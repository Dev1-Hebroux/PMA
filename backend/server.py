from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, BackgroundTasks, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, validator, ValidationError
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
from enum import Enum
import jwt
from passlib.context import CryptContext
import json
import asyncio
from collections import defaultdict
import qrcode
from io import BytesIO
import base64

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(
    title="Prescription Management App (PMA)",
    description="A comprehensive prescription management system powered by Innovating Chaos",
    version="2.0.0"
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security setup
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, List[str]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, user_id: str, connection_id: str):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.user_connections[user_id].append(connection_id)

    def disconnect(self, connection_id: str, user_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if user_id in self.user_connections:
            self.user_connections[user_id] = [
                conn for conn in self.user_connections[user_id] if conn != connection_id
            ]

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.user_connections:
            for connection_id in self.user_connections[user_id]:
                if connection_id in self.active_connections:
                    try:
                        await self.active_connections[connection_id].send_text(message)
                    except:
                        pass

manager = ConnectionManager()

# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    error_messages = []
    for error in exc.errors():
        field = " -> ".join(str(x) for x in error["loc"][1:])  # Skip 'body'
        message = error["msg"]
        error_messages.append(f"{field}: {message}" if field else message)
    
    return JSONResponse(
        status_code=422,
        content={"detail": "; ".join(error_messages)}
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions"""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."}
    )

# Enhanced Enums
class UserRole(str, Enum):
    PATIENT = "patient"
    GP = "gp"
    PHARMACY = "pharmacy"
    DELEGATE = "delegate"
    ADMIN = "admin"

class PrescriptionStatus(str, Enum):
    REQUESTED = "requested"
    GP_APPROVED = "gp_approved"
    SENT_TO_PHARMACY = "sent_to_pharmacy"
    DISPENSED = "dispensed"
    READY_FOR_COLLECTION = "ready_for_collection"
    COLLECTED = "collected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class PrescriptionType(str, Enum):
    ACUTE = "acute"
    REPEAT = "repeat"
    REPEAT_DISPENSING = "repeat_dispensing"

class DelegationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class NotificationType(str, Enum):
    PRESCRIPTION_APPROVED = "prescription_approved"
    PRESCRIPTION_READY = "prescription_ready"
    PRESCRIPTION_DISPENSED = "prescription_dispensed"
    DELEGATION_REQUEST = "delegation_request"
    REMINDER = "reminder"

class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    APPROVE = "approve"
    DISPENSE = "dispense"
    COLLECT = "collect"

# Enhanced Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    password_hash: str
    full_name: str
    role: UserRole
    nhs_number: Optional[str] = None  # For patients
    phone: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gp_license_number: Optional[str] = None  # For GPs
    pharmacy_license_number: Optional[str] = None  # For Pharmacies
    ods_code: Optional[str] = None  # NHS Organisation Data Service code
    nominated_pharmacy: Optional[str] = None  # For patients
    accessibility_requirements: Optional[Dict[str, Any]] = None
    gdpr_consent: bool = False
    gdpr_consent_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    last_login: Optional[datetime] = None

class Prescription(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    patient_nhs_number: Optional[str] = None
    gp_id: Optional[str] = None
    pharmacy_id: Optional[str] = None
    prescription_type: PrescriptionType = PrescriptionType.ACUTE
    medication_name: str
    medication_code: Optional[str] = None  # SNOMED CT code
    dosage: str
    quantity: str
    instructions: str
    indication: Optional[str] = None
    status: PrescriptionStatus = PrescriptionStatus.REQUESTED
    eps_id: Optional[str] = None  # EPS unique identifier
    barcode: Optional[str] = None
    qr_code: Optional[str] = None
    collection_pin: Optional[str] = None
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    sent_to_pharmacy_at: Optional[datetime] = None
    dispensed_at: Optional[datetime] = None
    collected_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None
    gp_notes: Optional[str] = None
    pharmacy_notes: Optional[str] = None
    repeat_count: int = 0
    max_repeats: int = 0
    adverse_reactions: Optional[List[str]] = None
    contraindications: Optional[List[str]] = None
    priority: str = "normal"  # normal, urgent, emergency
    
    @validator('expires_at', pre=True, always=True)
    def set_expiry(cls, v, values):
        if not v and 'requested_at' in values:
            return values['requested_at'] + timedelta(days=28)  # Standard NHS prescription validity
        return v

class Delegation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    delegate_user_id: str
    delegate_name: str
    delegate_phone: str
    delegate_relationship: str
    delegate_id_verified: bool = False
    status: DelegationStatus = DelegationStatus.PENDING
    permissions: List[str] = ["collect_prescriptions"]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    gdpr_consent: bool = False
    gdpr_consent_date: Optional[datetime] = None
    pin_code: Optional[str] = None
    qr_code: Optional[str] = None
    is_active: bool = True

class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    notification_type: NotificationType
    title: str
    message: str
    prescription_id: Optional[str] = None
    delegation_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    is_read: bool = False
    priority: str = "normal"
    data: Optional[Dict[str, Any]] = None

class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    action: AuditAction
    resource_type: str
    resource_id: str
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    gdpr_category: Optional[str] = None

# Request/Response Models
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: UserRole
    nhs_number: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[str] = None  # Changed to string to handle empty values
    gp_license_number: Optional[str] = None
    pharmacy_license_number: Optional[str] = None
    ods_code: Optional[str] = None
    accessibility_requirements: Optional[Dict[str, Any]] = None
    gdpr_consent: bool = False

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    role: str
    expires_in: int

class PrescriptionCreate(BaseModel):
    medication_name: str
    medication_code: Optional[str] = None
    dosage: str
    quantity: str
    instructions: str
    indication: Optional[str] = None
    prescription_type: PrescriptionType = PrescriptionType.ACUTE
    notes: Optional[str] = None
    priority: str = "normal"
    max_repeats: int = 0

class PrescriptionUpdate(BaseModel):
    status: Optional[PrescriptionStatus] = None
    gp_notes: Optional[str] = None
    pharmacy_notes: Optional[str] = None
    pharmacy_id: Optional[str] = None
    collection_pin: Optional[str] = None
    adverse_reactions: Optional[List[str]] = None
    contraindications: Optional[List[str]] = None

class DelegationCreate(BaseModel):
    delegate_user_id: str
    delegate_name: str
    delegate_phone: str
    delegate_relationship: str
    permissions: List[str] = ["collect_prescriptions"]
    expires_at: Optional[datetime] = None
    gdpr_consent: bool = False

class PharmacyNomination(BaseModel):
    pharmacy_id: str
    pharmacy_name: str
    pharmacy_address: str
    ods_code: str

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
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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

# Automated reminder system
async def check_stalled_prescriptions():
    """Check for stalled prescriptions and send reminders"""
    try:
        # Find prescriptions that are stalled (pending GP approval for > 24 hours)
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        
        stalled_prescriptions = await db.prescriptions.find({
            "status": PrescriptionStatus.REQUESTED,
            "requested_at": {"$lt": twenty_four_hours_ago}
        }).to_list(100)
        
        for prescription in stalled_prescriptions:
            prescription_obj = Prescription(**prescription)
            
            # Send reminder to patient
            await send_notification(
                prescription_obj.patient_id,
                NotificationType.REMINDER,
                "Prescription Pending Review",
                f"Your prescription for {prescription_obj.medication_name} is still pending GP approval. We've sent a reminder to your GP.",
                prescription_id=prescription_obj.id
            )
            
            # Send reminder to GP (if assigned) or all GPs
            if prescription_obj.gp_id:
                # Find the specific GP
                gp = await db.users.find_one({"id": prescription_obj.gp_id})
                if gp:
                    await send_notification(
                        gp["id"],
                        NotificationType.REMINDER,
                        "Prescription Awaiting Your Review",
                        f"Prescription for {prescription_obj.medication_name} has been pending for over 24 hours. Please review.",
                        prescription_id=prescription_obj.id
                    )
            else:
                # Send to all active GPs
                gps = await db.users.find({"role": UserRole.GP, "is_active": True}).to_list(50)
                for gp in gps:
                    await send_notification(
                        gp["id"],
                        NotificationType.REMINDER,
                        "Prescription Awaiting Review",
                        f"Prescription for {prescription_obj.medication_name} has been pending for over 24 hours. Please review.",
                        prescription_id=prescription_obj.id
                    )
        
        # Find prescriptions stalled at pharmacy (GP approved for > 12 hours)
        twelve_hours_ago = datetime.utcnow() - timedelta(hours=12)
        
        pharmacy_stalled = await db.prescriptions.find({
            "status": PrescriptionStatus.GP_APPROVED,
            "approved_at": {"$lt": twelve_hours_ago}
        }).to_list(100)
        
        for prescription in pharmacy_stalled:
            prescription_obj = Prescription(**prescription)
            
            # Send reminder to patient
            await send_notification(
                prescription_obj.patient_id,
                NotificationType.REMINDER,
                "Prescription Ready for Pharmacy",
                f"Your approved prescription for {prescription_obj.medication_name} is ready for pharmacy processing.",
                prescription_id=prescription_obj.id
            )
            
            # Send reminder to all pharmacies
            pharmacies = await db.users.find({"role": UserRole.PHARMACY, "is_active": True}).to_list(50)
            for pharmacy in pharmacies:
                await send_notification(
                    pharmacy["id"],
                    NotificationType.REMINDER,
                    "Prescription Awaiting Fulfillment",
                    f"Prescription for {prescription_obj.medication_name} has been approved and is awaiting fulfillment.",
                    prescription_id=prescription_obj.id
                )
                
        logger.info(f"Processed {len(stalled_prescriptions)} stalled prescriptions and {len(pharmacy_stalled)} pharmacy-stalled prescriptions")
        
    except Exception as e:
        logger.error(f"Error checking stalled prescriptions: {e}")

@api_router.post("/prescriptions/check-reminders")
async def trigger_reminder_check(current_user: User = Depends(get_current_user)):
    """Manually trigger reminder check (for admin use)"""
    if current_user.role not in [UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    await check_stalled_prescriptions()
    return {"message": "Reminder check completed"}
def generate_qr_code(data: str) -> str:
    """Generate QR code and return as base64 string"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

def generate_collection_pin() -> str:
    """Generate 6-digit collection PIN"""
    import random
    return str(random.randint(100000, 999999))

async def create_audit_log(user_id: str, action: AuditAction, resource_type: str, 
                          resource_id: str, details: Dict[str, Any]):
    """Create audit log entry"""
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        gdpr_category="healthcare_data"
    )
    await db.audit_logs.insert_one(audit_log.dict())

async def simple_create_audit_log(user_id: str, action: str, resource_type: str, 
                                 resource_id: str, details: Dict[str, Any]):
    """Simple audit log creation with string action"""
    audit_data = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details,
        "timestamp": datetime.utcnow(),
        "gdpr_category": "healthcare_data"
    }
    await db.audit_logs.insert_one(audit_data)

async def send_notification(user_id: str, notification_type: NotificationType, 
                           title: str, message: str, prescription_id: Optional[str] = None):
    """Send notification to user"""
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        prescription_id=prescription_id
    )
    await db.notifications.insert_one(notification.dict())
    
    # Send real-time notification via WebSocket
    await manager.send_personal_message(
        json.dumps({
            "type": "notification",
            "data": notification.dict()
        }),
        user_id
    )

async def simple_send_notification(user_id: str, notification_type: str, 
                                  title: str, message: str, prescription_id: Optional[str] = None):
    """Simple notification creation with string notification type"""
    notification_data = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "notification_type": notification_type,
        "title": title,
        "message": message,
        "prescription_id": prescription_id,
        "created_at": datetime.utcnow(),
        "is_read": False,
        "priority": "normal"
    }
    await db.notifications.insert_one(notification_data)
    
    # Send real-time notification via WebSocket
    try:
        await manager.send_personal_message(
            json.dumps({
                "type": "notification",
                "data": notification_data
            }),
            user_id
        )
    except Exception as ws_error:
        logger.warning(f"WebSocket notification failed: {ws_error}")

# WebSocket endpoint
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    connection_id = str(uuid.uuid4())
    await manager.connect(websocket, user_id, connection_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(connection_id, user_id)

# Enhanced Authentication routes
@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    try:
        # Check if user already exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Validate patient ID format (basic validation)
        if user_data.nhs_number and len(user_data.nhs_number.strip()) > 15:
            raise HTTPException(status_code=400, detail="Patient ID must be 15 characters or less")
        
        # Parse date_of_birth if provided
        parsed_date_of_birth = None
        if user_data.date_of_birth and user_data.date_of_birth.strip():
            try:
                parsed_date_of_birth = datetime.fromisoformat(user_data.date_of_birth.strip())
            except (ValueError, TypeError):
                # If date parsing fails, just ignore it for now
                parsed_date_of_birth = None
        
        # Create new user
        password_hash = get_password_hash(user_data.password)
        user_dict = {
            "id": str(uuid.uuid4()),
            "email": user_data.email,
            "password_hash": password_hash,
            "full_name": user_data.full_name,
            "role": user_data.role,
            "phone": user_data.phone,
            "address": user_data.address,
            "gp_license_number": user_data.gp_license_number,
            "pharmacy_license_number": user_data.pharmacy_license_number,
            "ods_code": user_data.ods_code,
            "accessibility_requirements": user_data.accessibility_requirements,
            "gdpr_consent": user_data.gdpr_consent,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True
        }
        
        # Add optional fields only if they have values
        if user_data.nhs_number and user_data.nhs_number.strip():
            user_dict["nhs_number"] = user_data.nhs_number.strip()
        
        if parsed_date_of_birth:
            user_dict["date_of_birth"] = parsed_date_of_birth
            
        if user_data.gdpr_consent:
            user_dict["gdpr_consent_date"] = datetime.utcnow()
        
        await db.users.insert_one(user_dict)
        
        # Create audit log (safely)
        try:
            await simple_create_audit_log(user_dict["id"], "CREATE", "user", user_dict["id"], 
                                        {"action": "user_registration", "role": user_data.role})
        except Exception as audit_error:
            logger.warning(f"Audit log creation failed: {audit_error}")
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_dict["id"], "role": user_data.role}, 
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token, 
            token_type="bearer", 
            user_id=user_dict["id"], 
            role=user_data.role,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log unexpected errors and return generic message
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail="Registration failed. Please try again.")

@api_router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    # Find user
    user = await db.users.find_one({"email": user_data.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Update last login
    await db.users.update_one(
        {"id": user["id"]}, 
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Create audit log (safely)
    try:
        await simple_create_audit_log(user["id"], "LOGIN", "user", user["id"], 
                                    {"action": "user_login"})
    except Exception as audit_error:
        logger.warning(f"Audit log creation failed: {audit_error}")
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"], "role": user["role"]}, 
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token, 
        token_type="bearer", 
        user_id=user["id"], 
        role=user["role"],
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

# Enhanced User routes
@api_router.get("/users/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

@api_router.put("/users/me")
async def update_user_profile(user_updates: dict, current_user: User = Depends(get_current_user)):
    # Remove sensitive fields
    protected_fields = {"id", "password_hash", "created_at", "role"}
    user_updates = {k: v for k, v in user_updates.items() if k not in protected_fields}
    user_updates["updated_at"] = datetime.utcnow()
    
    await db.users.update_one({"id": current_user.id}, {"$set": user_updates})
    
    # Create audit log (safely)
    try:
        await simple_create_audit_log(current_user.id, "UPDATE", "user", current_user.id, 
                                    {"action": "profile_update", "fields": list(user_updates.keys())})
    except Exception as audit_error:
        logger.warning(f"Audit log creation failed: {audit_error}")
    
    return {"message": "Profile updated successfully"}

@api_router.get("/users/gps", response_model=List[User])
async def get_gps():
    gps = await db.users.find({"role": UserRole.GP, "is_active": True}).to_list(100)
    return [User(**gp) for gp in gps]

@api_router.get("/users/pharmacies", response_model=List[User])
async def get_pharmacies():
    pharmacies = await db.users.find({"role": UserRole.PHARMACY, "is_active": True}).to_list(100)
    return [User(**pharmacy) for pharmacy in pharmacies]

@api_router.post("/users/nominate-pharmacy")
async def nominate_pharmacy(nomination: PharmacyNomination, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(status_code=403, detail="Only patients can nominate pharmacies")
    
    await db.users.update_one(
        {"id": current_user.id}, 
        {"$set": {"nominated_pharmacy": nomination.pharmacy_id}}
    )
    
    # Create audit log (safely)
    try:
        await simple_create_audit_log(current_user.id, "UPDATE", "user", current_user.id, 
                                    {"action": "pharmacy_nomination", "pharmacy_id": nomination.pharmacy_id})
    except Exception as audit_error:
        logger.warning(f"Audit log creation failed: {audit_error}")
    
    return {"message": "Pharmacy nominated successfully"}

# Enhanced Prescription routes
@api_router.post("/prescriptions", response_model=Prescription)
async def create_prescription(prescription_data: PrescriptionCreate, 
                             current_user: User = Depends(get_current_user)):
    try:
        if current_user.role != UserRole.PATIENT:
            raise HTTPException(status_code=403, detail="Only patients can create prescriptions")
        
        # Generate collection PIN and QR code
        collection_pin = generate_collection_pin()
        qr_data = f"prescription:{prescription_data.medication_name}:{collection_pin}"
        qr_code = generate_qr_code(qr_data)
        
        # Create prescription dictionary for database
        prescription_dict = {
            "id": str(uuid.uuid4()),
            "patient_id": current_user.id,
            "patient_nhs_number": current_user.nhs_number,
            "medication_name": prescription_data.medication_name,
            "medication_code": prescription_data.medication_code,
            "dosage": prescription_data.dosage,
            "quantity": prescription_data.quantity,
            "instructions": prescription_data.instructions,
            "indication": prescription_data.indication,
            "prescription_type": prescription_data.prescription_type,
            "notes": prescription_data.notes,
            "priority": prescription_data.priority,
            "max_repeats": prescription_data.max_repeats,
            "collection_pin": collection_pin,
            "qr_code": qr_code,
            "status": PrescriptionStatus.REQUESTED,
            "requested_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=28),
            "repeat_count": 0
        }
        
        # Insert into database
        await db.prescriptions.insert_one(prescription_dict)
        
        # Create audit log (safely)
        try:
            audit_data = {
                "user_id": current_user.id,
                "action": AuditAction.CREATE,
                "resource_type": "prescription",
                "resource_id": prescription_dict["id"],
                "details": {"action": "prescription_created", "medication": prescription_dict["medication_name"]},
                "timestamp": datetime.utcnow()
            }
            await db.audit_logs.insert_one(audit_data)
        except Exception as audit_error:
            logger.warning(f"Audit log creation failed: {audit_error}")
        
        # Send notification (safely)
        try:
            notification_data = {
                "id": str(uuid.uuid4()),
                "user_id": current_user.id,
                "notification_type": NotificationType.PRESCRIPTION_APPROVED,
                "title": "Prescription Request Submitted",
                "message": f"Your prescription for {prescription_dict['medication_name']} has been submitted for GP approval.",
                "prescription_id": prescription_dict["id"],
                "created_at": datetime.utcnow(),
                "is_read": False
            }
            await db.notifications.insert_one(notification_data)
        except Exception as notif_error:
            logger.warning(f"Notification creation failed: {notif_error}")
        
        # Return the prescription object
        return Prescription(**prescription_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating prescription: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create prescription. Please try again.")

@api_router.get("/prescriptions", response_model=List[Prescription])
async def get_prescriptions(current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.PATIENT:
        prescriptions = await db.prescriptions.find({"patient_id": current_user.id}).to_list(100)
    elif current_user.role == UserRole.GP:
        prescriptions = await db.prescriptions.find({
            "status": {"$in": [PrescriptionStatus.REQUESTED]}
        }).to_list(100)
    elif current_user.role == UserRole.PHARMACY:
        prescriptions = await db.prescriptions.find({
            "status": {"$in": [PrescriptionStatus.GP_APPROVED, PrescriptionStatus.SENT_TO_PHARMACY]}
        }).to_list(100)
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
    
    # Create audit log (safely)
    try:
        await simple_create_audit_log(current_user.id, "VIEW", "prescription", prescription_id, 
                                    {"action": "prescription_viewed"})
    except Exception as audit_error:
        logger.warning(f"Audit log creation failed: {audit_error}")
    
    return prescription_obj

@api_router.put("/prescriptions/{prescription_id}", response_model=Prescription)
async def update_prescription(prescription_id: str, prescription_data: PrescriptionUpdate, 
                             current_user: User = Depends(get_current_user)):
    prescription = await db.prescriptions.find_one({"id": prescription_id})
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    prescription_obj = Prescription(**prescription)
    update_data = {}
    
    # Handle status updates based on user role
    if current_user.role == UserRole.GP and prescription_data.status == PrescriptionStatus.GP_APPROVED:
        update_data = {
            "status": PrescriptionStatus.GP_APPROVED,
            "gp_id": current_user.id,
            "approved_at": datetime.utcnow(),
            "gp_notes": prescription_data.gp_notes
        }
        
        # Send notification to patient (safely)
        try:
            await simple_send_notification(
                prescription_obj.patient_id,
                "PRESCRIPTION_APPROVED",
                "Prescription Approved",
                f"Your prescription for {prescription_obj.medication_name} has been approved by your GP."
            )
        except Exception as notif_error:
            logger.warning(f"Notification creation failed: {notif_error}")
        
    elif current_user.role == UserRole.PHARMACY and prescription_data.status == PrescriptionStatus.DISPENSED:
        update_data = {
            "status": PrescriptionStatus.READY_FOR_COLLECTION,
            "pharmacy_id": current_user.id,
            "dispensed_at": datetime.utcnow(),
            "pharmacy_notes": prescription_data.pharmacy_notes
        }
        
        # Send notification to patient (safely)
        try:
            await simple_send_notification(
                prescription_obj.patient_id,
                "PRESCRIPTION_READY",
                "Prescription Ready for Collection",
                f"Your prescription for {prescription_obj.medication_name} is ready for collection."
            )
        except Exception as notif_error:
            logger.warning(f"Notification creation failed: {notif_error}")
        
    else:
        raise HTTPException(status_code=403, detail="Invalid status update for your role")
    
    await db.prescriptions.update_one({"id": prescription_id}, {"$set": update_data})
    
    # Create audit log (safely)
    try:
        await simple_create_audit_log(current_user.id, "UPDATE", "prescription", prescription_id, 
                                    {"action": "status_update", "new_status": str(prescription_data.status)})
    except Exception as audit_error:
        logger.warning(f"Audit log creation failed: {audit_error}")
    
    # Get updated prescription
    updated_prescription = await db.prescriptions.find_one({"id": prescription_id})
    return Prescription(**updated_prescription)

# Enhanced Delegation routes
@api_router.post("/delegations", response_model=Delegation)
async def create_delegation(delegation_data: DelegationCreate, 
                           current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(status_code=403, detail="Only patients can create delegations")
    
    # Generate PIN and QR code for delegation
    pin_code = generate_collection_pin()
    qr_data = f"delegation:{current_user.id}:{delegation_data.delegate_user_id}:{pin_code}"
    qr_code = generate_qr_code(qr_data)
    
    delegation = Delegation(
        patient_id=current_user.id,
        delegate_user_id=delegation_data.delegate_user_id,
        delegate_name=delegation_data.delegate_name,
        delegate_phone=delegation_data.delegate_phone,
        delegate_relationship=delegation_data.delegate_relationship,
        permissions=delegation_data.permissions,
        expires_at=delegation_data.expires_at or (datetime.utcnow() + timedelta(days=30)),
        gdpr_consent=delegation_data.gdpr_consent,
        gdpr_consent_date=datetime.utcnow() if delegation_data.gdpr_consent else None,
        pin_code=pin_code,
        qr_code=qr_code
    )
    
    await db.delegations.insert_one(delegation.dict())
    
    # Create audit log (safely)
    try:
        await simple_create_audit_log(current_user.id, "CREATE", "delegation", delegation.id, 
                                    {"action": "delegation_created", "delegate": delegation.delegate_name})
    except Exception as audit_error:
        logger.warning(f"Audit log creation failed: {audit_error}")
    
    # Send notification to delegate (safely)
    try:
        await simple_send_notification(
            delegation.delegate_user_id,
            "DELEGATION_REQUEST",
            "Delegation Request",
            f"You have been authorized to collect prescriptions for {current_user.full_name}.",
            delegation_id=delegation.id
        )
    except Exception as notif_error:
        logger.warning(f"Notification creation failed: {notif_error}")
    
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
        "approved_at": datetime.utcnow()
    }
    
    await db.delegations.update_one({"id": delegation_id}, {"$set": update_data})
    
    # Create audit log
    await create_audit_log(current_user.id, AuditAction.APPROVE, "delegation", delegation_id, 
                          {"action": "delegation_approved"})
    
    return {"message": "Delegation approved successfully"}

# Notification routes
@api_router.get("/notifications", response_model=List[Notification])
async def get_notifications(current_user: User = Depends(get_current_user)):
    notifications = await db.notifications.find({"user_id": current_user.id}).sort("created_at", -1).to_list(50)
    return [Notification(**notification) for notification in notifications]

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: User = Depends(get_current_user)):
    await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {"$set": {"is_read": True, "read_at": datetime.utcnow()}}
    )
    return {"message": "Notification marked as read"}

# Analytics and Reporting routes
@api_router.get("/analytics/dashboard")
async def get_analytics_dashboard(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.GP, UserRole.PHARMACY, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get prescription statistics
    total_prescriptions = await db.prescriptions.count_documents({})
    pending_prescriptions = await db.prescriptions.count_documents({"status": PrescriptionStatus.REQUESTED})
    approved_prescriptions = await db.prescriptions.count_documents({"status": PrescriptionStatus.GP_APPROVED})
    dispensed_prescriptions = await db.prescriptions.count_documents({"status": PrescriptionStatus.DISPENSED})
    
    return {
        "total_prescriptions": total_prescriptions,
        "pending_prescriptions": pending_prescriptions,
        "approved_prescriptions": approved_prescriptions,
        "dispensed_prescriptions": dispensed_prescriptions,
        "completion_rate": (dispensed_prescriptions / total_prescriptions * 100) if total_prescriptions > 0 else 0
    }

# Basic routes
@api_router.get("/")
async def root():
    return {"message": "Prescription Management App (PMA) API", "version": "2.0.0", "powered_by": "Innovating Chaos"}

@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow(),
        "version": "2.0.0",
        "app": "Prescription Management App (PMA)",
        "powered_by": "Innovating Chaos",
        "features": ["Healthcare Innovation", "WCAG 2.2 Compliance", "Real-time Notifications"]
    }

# Include the router in the main app
app.include_router(api_router)

# Enhanced CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],  # Configure with specific origins in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    # Create database indexes for better performance
    await db.users.create_index("email", unique=True)
    await db.users.create_index("nhs_number")
    await db.prescriptions.create_index("patient_id")
    await db.prescriptions.create_index("status")
    await db.prescriptions.create_index("expires_at")
    await db.prescriptions.create_index("requested_at")
    await db.prescriptions.create_index("approved_at")
    await db.delegations.create_index("patient_id")
    await db.delegations.create_index("delegate_user_id")
    await db.notifications.create_index("user_id")
    await db.audit_logs.create_index("user_id")
    await db.audit_logs.create_index("timestamp")
    
    # Start background task for reminder checking
    asyncio.create_task(reminder_background_task())
    
    logger.info("Prescription Management App (PMA) powered by Innovating Chaos started successfully")

async def reminder_background_task():
    """Background task to check for stalled prescriptions every hour"""
    while True:
        try:
            await asyncio.sleep(3600)  # Wait 1 hour
            await check_stalled_prescriptions()
        except Exception as e:
            logger.error(f"Error in reminder background task: {e}")
            await asyncio.sleep(3600)  # Continue after error

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    logger.info("Database connection closed")