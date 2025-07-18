from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
from enum import Enum
import jwt
from passlib.context import CryptContext
import hashlib

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security setup
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"

# Enums
class UserRole(str, Enum):
    PATIENT = "patient"
    GP = "gp"
    PHARMACY = "pharmacy"
    DELEGATE = "delegate"

class PrescriptionStatus(str, Enum):
    REQUESTED = "requested"
    GP_APPROVED = "gp_approved"
    PHARMACY_FULFILLED = "pharmacy_fulfilled"
    COLLECTED = "collected"
    CANCELLED = "cancelled"

class DelegationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    password_hash: str
    full_name: str
    role: UserRole
    phone: Optional[str] = None
    address: Optional[str] = None
    gp_license_number: Optional[str] = None  # For GPs
    pharmacy_license_number: Optional[str] = None  # For Pharmacies
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: UserRole
    phone: Optional[str] = None
    address: Optional[str] = None
    gp_license_number: Optional[str] = None
    pharmacy_license_number: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    role: str

class Prescription(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    gp_id: Optional[str] = None
    pharmacy_id: Optional[str] = None
    medication_name: str
    dosage: str
    quantity: str
    instructions: str
    status: PrescriptionStatus = PrescriptionStatus.REQUESTED
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    fulfilled_at: Optional[datetime] = None
    collected_at: Optional[datetime] = None
    notes: Optional[str] = None
    gp_notes: Optional[str] = None
    pharmacy_notes: Optional[str] = None

class PrescriptionCreate(BaseModel):
    medication_name: str
    dosage: str
    quantity: str
    instructions: str
    notes: Optional[str] = None

class PrescriptionUpdate(BaseModel):
    status: Optional[PrescriptionStatus] = None
    gp_notes: Optional[str] = None
    pharmacy_notes: Optional[str] = None
    pharmacy_id: Optional[str] = None

class Delegation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    delegate_user_id: str
    delegate_name: str
    delegate_phone: str
    delegate_relationship: str
    status: DelegationStatus = DelegationStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True

class DelegationCreate(BaseModel):
    delegate_user_id: str
    delegate_name: str
    delegate_phone: str
    delegate_relationship: str

# Authentication helpers
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"id": user_id})
    if user is None:
        raise credentials_exception
    return User(**user)

# Authentication routes
@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    password_hash = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        password_hash=password_hash,
        full_name=user_data.full_name,
        role=user_data.role,
        phone=user_data.phone,
        address=user_data.address,
        gp_license_number=user_data.gp_license_number,
        pharmacy_license_number=user_data.pharmacy_license_number
    )
    
    await db.users.insert_one(user.dict())
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    
    return Token(access_token=access_token, token_type="bearer", user_id=user.id, role=user.role)

@api_router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    # Find user
    user = await db.users.find_one({"email": user_data.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create access token
    access_token = create_access_token(data={"sub": user["id"]})
    
    return Token(access_token=access_token, token_type="bearer", user_id=user["id"], role=user["role"])

# User routes
@api_router.get("/users/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

@api_router.get("/users/gps", response_model=List[User])
async def get_gps():
    gps = await db.users.find({"role": UserRole.GP, "is_active": True}).to_list(100)
    return [User(**gp) for gp in gps]

@api_router.get("/users/pharmacies", response_model=List[User])
async def get_pharmacies():
    pharmacies = await db.users.find({"role": UserRole.PHARMACY, "is_active": True}).to_list(100)
    return [User(**pharmacy) for pharmacy in pharmacies]

# Prescription routes
@api_router.post("/prescriptions", response_model=Prescription)
async def create_prescription(prescription_data: PrescriptionCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(status_code=403, detail="Only patients can create prescriptions")
    
    prescription = Prescription(
        patient_id=current_user.id,
        medication_name=prescription_data.medication_name,
        dosage=prescription_data.dosage,
        quantity=prescription_data.quantity,
        instructions=prescription_data.instructions,
        notes=prescription_data.notes
    )
    
    await db.prescriptions.insert_one(prescription.dict())
    return prescription

@api_router.get("/prescriptions", response_model=List[Prescription])
async def get_prescriptions(current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.PATIENT:
        prescriptions = await db.prescriptions.find({"patient_id": current_user.id}).to_list(100)
    elif current_user.role == UserRole.GP:
        prescriptions = await db.prescriptions.find({"status": PrescriptionStatus.REQUESTED}).to_list(100)
    elif current_user.role == UserRole.PHARMACY:
        prescriptions = await db.prescriptions.find({"status": PrescriptionStatus.GP_APPROVED}).to_list(100)
    else:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return [Prescription(**prescription) for prescription in prescriptions]

@api_router.get("/prescriptions/{prescription_id}", response_model=Prescription)
async def get_prescription(prescription_id: str, current_user: User = Depends(get_current_user)):
    prescription = await db.prescriptions.find_one({"id": prescription_id})
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    prescription_obj = Prescription(**prescription)
    
    # Check access permissions
    if current_user.role == UserRole.PATIENT and prescription_obj.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return prescription_obj

@api_router.put("/prescriptions/{prescription_id}", response_model=Prescription)
async def update_prescription(prescription_id: str, prescription_data: PrescriptionUpdate, current_user: User = Depends(get_current_user)):
    prescription = await db.prescriptions.find_one({"id": prescription_id})
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    prescription_obj = Prescription(**prescription)
    
    # Handle status updates based on user role
    if current_user.role == UserRole.GP and prescription_data.status == PrescriptionStatus.GP_APPROVED:
        update_data = {
            "status": PrescriptionStatus.GP_APPROVED,
            "gp_id": current_user.id,
            "approved_at": datetime.utcnow(),
            "gp_notes": prescription_data.gp_notes
        }
    elif current_user.role == UserRole.PHARMACY and prescription_data.status == PrescriptionStatus.PHARMACY_FULFILLED:
        update_data = {
            "status": PrescriptionStatus.PHARMACY_FULFILLED,
            "pharmacy_id": current_user.id,
            "fulfilled_at": datetime.utcnow(),
            "pharmacy_notes": prescription_data.pharmacy_notes
        }
    else:
        raise HTTPException(status_code=403, detail="Invalid status update for your role")
    
    await db.prescriptions.update_one({"id": prescription_id}, {"$set": update_data})
    
    # Get updated prescription
    updated_prescription = await db.prescriptions.find_one({"id": prescription_id})
    return Prescription(**updated_prescription)

# Delegation routes
@api_router.post("/delegations", response_model=Delegation)
async def create_delegation(delegation_data: DelegationCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(status_code=403, detail="Only patients can create delegations")
    
    delegation = Delegation(
        patient_id=current_user.id,
        delegate_user_id=delegation_data.delegate_user_id,
        delegate_name=delegation_data.delegate_name,
        delegate_phone=delegation_data.delegate_phone,
        delegate_relationship=delegation_data.delegate_relationship
    )
    
    await db.delegations.insert_one(delegation.dict())
    return delegation

@api_router.get("/delegations", response_model=List[Delegation])
async def get_delegations(current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.PATIENT:
        delegations = await db.delegations.find({"patient_id": current_user.id}).to_list(100)
    elif current_user.role == UserRole.DELEGATE:
        delegations = await db.delegations.find({"delegate_user_id": current_user.id}).to_list(100)
    else:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return [Delegation(**delegation) for delegation in delegations]

@api_router.put("/delegations/{delegation_id}/approve")
async def approve_delegation(delegation_id: str, current_user: User = Depends(get_current_user)):
    delegation = await db.delegations.find_one({"id": delegation_id})
    if not delegation:
        raise HTTPException(status_code=404, detail="Delegation not found")
    
    if delegation["patient_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_data = {
        "status": DelegationStatus.APPROVED,
        "approved_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=30)  # 30 day expiry
    }
    
    await db.delegations.update_one({"id": delegation_id}, {"$set": update_data})
    
    return {"message": "Delegation approved successfully"}

# Basic routes
@api_router.get("/")
async def root():
    return {"message": "Prescription Management API"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()