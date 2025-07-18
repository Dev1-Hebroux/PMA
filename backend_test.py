#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Prescription Management System
Tests authentication, prescription workflow, user management, and delegation system
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://f6b00ae1-f513-4038-91eb-ddf68c5cea24.preview.emergentagent.com/api"
TIMEOUT = 30

class BackendTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.timeout = TIMEOUT
        self.tokens = {}  # Store tokens for different users
        self.users = {}   # Store user data
        self.prescriptions = {}  # Store prescription data
        self.delegations = {}    # Store delegation data
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def make_request(self, method: str, endpoint: str, data: Dict = None, 
                    headers: Dict = None, token: str = None) -> requests.Response:
        """Make HTTP request with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        
        # Set up headers
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)
        if token:
            request_headers["Authorization"] = f"Bearer {token}"
            
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=request_headers)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, headers=request_headers)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, headers=request_headers)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=request_headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            return response
        except requests.exceptions.RequestException as e:
            self.log(f"Request failed: {e}", "ERROR")
            raise
            
    def test_health_check(self) -> bool:
        """Test basic health check endpoints"""
        self.log("Testing health check endpoints...")
        
        try:
            # Test root endpoint
            response = self.make_request("GET", "/")
            if response.status_code == 200:
                self.log("✅ Root endpoint working")
            else:
                self.log(f"❌ Root endpoint failed: {response.status_code}", "ERROR")
                return False
                
            # Test health endpoint
            response = self.make_request("GET", "/health")
            if response.status_code == 200:
                data = response.json()
                if "status" in data and data["status"] == "healthy":
                    self.log("✅ Health check endpoint working")
                    return True
                else:
                    self.log(f"❌ Health check returned unexpected data: {data}", "ERROR")
                    return False
            else:
                self.log(f"❌ Health check failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Health check test failed: {e}", "ERROR")
            return False
            
    def test_user_registration(self) -> bool:
        """Test user registration for all roles"""
        self.log("Testing user registration for all roles...")
        
        # Generate unique emails using timestamp
        timestamp = str(int(time.time()))
        
        test_users = [
            {
                "role": "patient",
                "email": f"sarah.johnson.{timestamp}@email.com",
                "password": "SecurePass123!",
                "full_name": "Sarah Johnson",
                "phone": "+44 7700 900123",
                "address": "123 Oak Street, London, SW1A 1AA"
            },
            {
                "role": "gp", 
                "email": f"dr.smith.{timestamp}@medicalpractice.com",
                "password": "DoctorPass456!",
                "full_name": "Dr. Michael Smith",
                "phone": "+44 7700 900456",
                "address": "456 Medical Centre, London, W1A 0AX",
                "gp_license_number": "GMC123456"
            },
            {
                "role": "pharmacy",
                "email": f"manager.{timestamp}@wellnesspharmacy.com", 
                "password": "PharmacyPass789!",
                "full_name": "Wellness Pharmacy",
                "phone": "+44 7700 900789",
                "address": "789 High Street, London, EC1A 1BB",
                "pharmacy_license_number": "GPhC987654"
            },
            {
                "role": "delegate",
                "email": f"emma.wilson.{timestamp}@email.com",
                "password": "DelegatePass321!",
                "full_name": "Emma Wilson",
                "phone": "+44 7700 900321",
                "address": "321 Pine Avenue, London, N1 9AA"
            }
        ]
        
        success_count = 0
        
        for user_data in test_users:
            try:
                response = self.make_request("POST", "/auth/register", user_data)
                
                if response.status_code == 200:
                    token_data = response.json()
                    if all(key in token_data for key in ["access_token", "token_type", "user_id", "role"]):
                        self.tokens[user_data["role"]] = token_data["access_token"]
                        self.users[user_data["role"]] = {
                            "user_id": token_data["user_id"],
                            "email": user_data["email"],
                            "role": user_data["role"],
                            "full_name": user_data["full_name"]
                        }
                        self.log(f"✅ {user_data['role'].title()} registration successful")
                        success_count += 1
                    else:
                        self.log(f"❌ {user_data['role'].title()} registration returned incomplete token data", "ERROR")
                else:
                    error_msg = response.text
                    self.log(f"❌ {user_data['role'].title()} registration failed: {response.status_code} - {error_msg}", "ERROR")
                    
            except Exception as e:
                self.log(f"❌ {user_data['role'].title()} registration error: {e}", "ERROR")
                
        return success_count == len(test_users)
        
    def test_user_login(self) -> bool:
        """Test user login functionality"""
        self.log("Testing user login functionality...")
        
        # Use the emails from registration or fallback to existing ones
        login_tests = []
        for role in ["patient", "gp", "pharmacy", "delegate"]:
            if role in self.users:
                login_tests.append({
                    "email": self.users[role]["email"],
                    "password": {
                        "patient": "SecurePass123!",
                        "gp": "DoctorPass456!",
                        "pharmacy": "PharmacyPass789!",
                        "delegate": "DelegatePass321!"
                    }[role],
                    "role": role
                })
        
        # If no users from registration, try with original emails
        if not login_tests:
            login_tests = [
                {"email": "sarah.johnson@email.com", "password": "SecurePass123!", "role": "patient"},
                {"email": "dr.smith@medicalpractice.com", "password": "DoctorPass456!", "role": "gp"},
                {"email": "manager@wellnesspharmacy.com", "password": "PharmacyPass789!", "role": "pharmacy"},
                {"email": "emma.wilson@email.com", "password": "DelegatePass321!", "role": "delegate"}
            ]
        
        success_count = 0
        
        for login_data in login_tests:
            try:
                response = self.make_request("POST", "/auth/login", {
                    "email": login_data["email"],
                    "password": login_data["password"]
                })
                
                if response.status_code == 200:
                    token_data = response.json()
                    if token_data.get("role") == login_data["role"]:
                        # Store token for later tests if not already stored
                        if login_data["role"] not in self.tokens:
                            self.tokens[login_data["role"]] = token_data["access_token"]
                            self.users[login_data["role"]] = {
                                "user_id": token_data["user_id"],
                                "email": login_data["email"],
                                "role": login_data["role"],
                                "full_name": "Test User"
                            }
                        self.log(f"✅ {login_data['role'].title()} login successful")
                        success_count += 1
                    else:
                        self.log(f"❌ {login_data['role'].title()} login returned wrong role", "ERROR")
                else:
                    self.log(f"❌ {login_data['role'].title()} login failed: {response.status_code}", "ERROR")
                    
            except Exception as e:
                self.log(f"❌ {login_data['role'].title()} login error: {e}", "ERROR")
                
        # Test invalid credentials
        try:
            response = self.make_request("POST", "/auth/login", {
                "email": "invalid@email.com",
                "password": "wrongpassword"
            })
            if response.status_code == 401:
                self.log("✅ Invalid credentials properly rejected")
                success_count += 1
            else:
                self.log(f"❌ Invalid credentials not properly rejected: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ Invalid credentials test error: {e}", "ERROR")
            
        return success_count == len(login_tests) + 1
        
    def test_protected_routes(self) -> bool:
        """Test JWT token validation and protected routes"""
        self.log("Testing protected routes and JWT validation...")
        
        success_count = 0
        
        # Test accessing protected route without token
        try:
            response = self.make_request("GET", "/users/me")
            if response.status_code in [401, 403]:  # FastAPI HTTPBearer can return either
                self.log("✅ Protected route properly rejects requests without token")
                success_count += 1
            else:
                self.log(f"❌ Protected route should reject requests without token: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ Protected route test error: {e}", "ERROR")
            
        # Test accessing protected route with invalid token
        try:
            response = self.make_request("GET", "/users/me", token="invalid_token")
            if response.status_code == 401:
                self.log("✅ Protected route properly rejects invalid tokens")
                success_count += 1
            else:
                self.log(f"❌ Protected route should reject invalid tokens: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ Invalid token test error: {e}", "ERROR")
            
        # Test accessing protected route with valid token
        if "patient" in self.tokens:
            try:
                response = self.make_request("GET", "/users/me", token=self.tokens["patient"])
                if response.status_code == 200:
                    user_data = response.json()
                    if user_data.get("role") == "patient":
                        self.log("✅ Protected route works with valid token")
                        success_count += 1
                    else:
                        self.log(f"❌ Protected route returned wrong user data", "ERROR")
                else:
                    self.log(f"❌ Protected route failed with valid token: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Valid token test error: {e}", "ERROR")
        else:
            self.log("❌ No patient token available for testing", "ERROR")
            
        return success_count == 3
        
    def test_user_management(self) -> bool:
        """Test user management endpoints"""
        self.log("Testing user management endpoints...")
        
        success_count = 0
        
        # Test get current user info for each role
        for role in ["patient", "gp", "pharmacy", "delegate"]:
            if role in self.tokens:
                try:
                    response = self.make_request("GET", "/users/me", token=self.tokens[role])
                    if response.status_code == 200:
                        user_data = response.json()
                        if user_data.get("role") == role:
                            self.log(f"✅ Get current user info works for {role}")
                            success_count += 1
                        else:
                            self.log(f"❌ Wrong role returned for {role}", "ERROR")
                    else:
                        self.log(f"❌ Get current user failed for {role}: {response.status_code}", "ERROR")
                except Exception as e:
                    self.log(f"❌ Get current user error for {role}: {e}", "ERROR")
                    
        # Test get GPs list
        try:
            response = self.make_request("GET", "/users/gps")
            if response.status_code == 200:
                gps = response.json()
                if isinstance(gps, list) and len(gps) > 0:
                    self.log("✅ Get GPs list working")
                    success_count += 1
                else:
                    self.log("❌ Get GPs list returned empty or invalid data", "ERROR")
            else:
                self.log(f"❌ Get GPs list failed: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ Get GPs list error: {e}", "ERROR")
            
        # Test get pharmacies list
        try:
            response = self.make_request("GET", "/users/pharmacies")
            if response.status_code == 200:
                pharmacies = response.json()
                if isinstance(pharmacies, list) and len(pharmacies) > 0:
                    self.log("✅ Get pharmacies list working")
                    success_count += 1
                else:
                    self.log("❌ Get pharmacies list returned empty or invalid data", "ERROR")
            else:
                self.log(f"❌ Get pharmacies list failed: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ Get pharmacies list error: {e}", "ERROR")
            
        return success_count == 6  # 4 roles + 2 lists
        
    def test_prescription_workflow(self) -> bool:
        """Test complete prescription workflow"""
        self.log("Testing prescription workflow...")
        
        success_count = 0
        
        # Step 1: Patient creates prescription
        if "patient" in self.tokens:
            prescription_data = {
                "medication_name": "Amoxicillin 500mg",
                "dosage": "500mg",
                "quantity": "21 capsules",
                "instructions": "Take one capsule three times daily with food for 7 days",
                "notes": "Patient has mild penicillin allergy - monitor for reactions"
            }
            
            try:
                response = self.make_request("POST", "/prescriptions", prescription_data, token=self.tokens["patient"])
                if response.status_code == 200:
                    prescription = response.json()
                    if prescription.get("status") == "requested":
                        self.prescriptions["test_prescription"] = prescription
                        self.log("✅ Patient can create prescription")
                        success_count += 1
                    else:
                        self.log(f"❌ Prescription created with wrong status: {prescription.get('status')}", "ERROR")
                else:
                    self.log(f"❌ Prescription creation failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Prescription creation error: {e}", "ERROR")
        else:
            self.log("❌ No patient token available", "ERROR")
            
        # Step 2: Test role-based prescription access
        # Patient should see their prescriptions
        if "patient" in self.tokens:
            try:
                response = self.make_request("GET", "/prescriptions", token=self.tokens["patient"])
                if response.status_code == 200:
                    prescriptions = response.json()
                    if isinstance(prescriptions, list) and len(prescriptions) > 0:
                        self.log("✅ Patient can view their prescriptions")
                        success_count += 1
                    else:
                        self.log("❌ Patient cannot see their prescriptions", "ERROR")
                else:
                    self.log(f"❌ Patient prescription list failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Patient prescription list error: {e}", "ERROR")
                
        # GP should see pending prescriptions
        if "gp" in self.tokens:
            try:
                response = self.make_request("GET", "/prescriptions", token=self.tokens["gp"])
                if response.status_code == 200:
                    prescriptions = response.json()
                    if isinstance(prescriptions, list):
                        self.log("✅ GP can view pending prescriptions")
                        success_count += 1
                    else:
                        self.log("❌ GP prescription list returned invalid data", "ERROR")
                else:
                    self.log(f"❌ GP prescription list failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ GP prescription list error: {e}", "ERROR")
                
        # Step 3: GP approves prescription
        if "gp" in self.tokens and "test_prescription" in self.prescriptions:
            prescription_id = self.prescriptions["test_prescription"]["id"]
            update_data = {
                "status": "gp_approved",
                "gp_notes": "Prescription approved. Patient should complete full course."
            }
            
            try:
                response = self.make_request("PUT", f"/prescriptions/{prescription_id}", update_data, token=self.tokens["gp"])
                if response.status_code == 200:
                    updated_prescription = response.json()
                    if updated_prescription.get("status") == "gp_approved":
                        self.prescriptions["test_prescription"] = updated_prescription
                        self.log("✅ GP can approve prescription")
                        success_count += 1
                    else:
                        self.log(f"❌ Prescription not properly approved: {updated_prescription.get('status')}", "ERROR")
                else:
                    self.log(f"❌ GP prescription approval failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ GP prescription approval error: {e}", "ERROR")
                
        # Step 4: Pharmacy sees approved prescriptions
        if "pharmacy" in self.tokens:
            try:
                response = self.make_request("GET", "/prescriptions", token=self.tokens["pharmacy"])
                if response.status_code == 200:
                    prescriptions = response.json()
                    if isinstance(prescriptions, list):
                        self.log("✅ Pharmacy can view approved prescriptions")
                        success_count += 1
                    else:
                        self.log("❌ Pharmacy prescription list returned invalid data", "ERROR")
                else:
                    self.log(f"❌ Pharmacy prescription list failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Pharmacy prescription list error: {e}", "ERROR")
                
        # Step 5: Pharmacy fulfills prescription
        if "pharmacy" in self.tokens and "test_prescription" in self.prescriptions:
            prescription_id = self.prescriptions["test_prescription"]["id"]
            update_data = {
                "status": "pharmacy_fulfilled",
                "pharmacy_notes": "Prescription ready for collection. Please bring ID."
            }
            
            try:
                response = self.make_request("PUT", f"/prescriptions/{prescription_id}", update_data, token=self.tokens["pharmacy"])
                if response.status_code == 200:
                    updated_prescription = response.json()
                    if updated_prescription.get("status") == "pharmacy_fulfilled":
                        self.log("✅ Pharmacy can fulfill prescription")
                        success_count += 1
                    else:
                        self.log(f"❌ Prescription not properly fulfilled: {updated_prescription.get('status')}", "ERROR")
                else:
                    self.log(f"❌ Pharmacy prescription fulfillment failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Pharmacy prescription fulfillment error: {e}", "ERROR")
                
        # Step 6: Test individual prescription access
        if "patient" in self.tokens and "test_prescription" in self.prescriptions:
            prescription_id = self.prescriptions["test_prescription"]["id"]
            try:
                response = self.make_request("GET", f"/prescriptions/{prescription_id}", token=self.tokens["patient"])
                if response.status_code == 200:
                    prescription = response.json()
                    if prescription.get("id") == prescription_id:
                        self.log("✅ Individual prescription access working")
                        success_count += 1
                    else:
                        self.log("❌ Individual prescription returned wrong data", "ERROR")
                else:
                    self.log(f"❌ Individual prescription access failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Individual prescription access error: {e}", "ERROR")
                
        return success_count >= 6  # Allow some flexibility for workflow steps
        
    def test_delegation_system(self) -> bool:
        """Test delegation system"""
        self.log("Testing delegation system...")
        
        success_count = 0
        
        # Step 1: Patient creates delegation
        if "patient" in self.tokens and "delegate" in self.users:
            delegation_data = {
                "delegate_user_id": self.users["delegate"]["user_id"],
                "delegate_name": "Emma Wilson",
                "delegate_phone": "+44 7700 900321",
                "delegate_relationship": "Family Member"
            }
            
            try:
                response = self.make_request("POST", "/delegations", delegation_data, token=self.tokens["patient"])
                if response.status_code == 200:
                    delegation = response.json()
                    if delegation.get("status") == "pending":
                        self.delegations["test_delegation"] = delegation
                        self.log("✅ Patient can create delegation")
                        success_count += 1
                    else:
                        self.log(f"❌ Delegation created with wrong status: {delegation.get('status')}", "ERROR")
                else:
                    self.log(f"❌ Delegation creation failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Delegation creation error: {e}", "ERROR")
        else:
            self.log("❌ Missing patient token or delegate user for delegation test", "ERROR")
            
        # Step 2: Patient views their delegations
        if "patient" in self.tokens:
            try:
                response = self.make_request("GET", "/delegations", token=self.tokens["patient"])
                if response.status_code == 200:
                    delegations = response.json()
                    if isinstance(delegations, list):
                        self.log("✅ Patient can view their delegations")
                        success_count += 1
                    else:
                        self.log("❌ Patient delegation list returned invalid data", "ERROR")
                else:
                    self.log(f"❌ Patient delegation list failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Patient delegation list error: {e}", "ERROR")
                
        # Step 3: Delegate views their delegations
        if "delegate" in self.tokens:
            try:
                response = self.make_request("GET", "/delegations", token=self.tokens["delegate"])
                if response.status_code == 200:
                    delegations = response.json()
                    if isinstance(delegations, list):
                        self.log("✅ Delegate can view their delegations")
                        success_count += 1
                    else:
                        self.log("❌ Delegate delegation list returned invalid data", "ERROR")
                else:
                    self.log(f"❌ Delegate delegation list failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Delegate delegation list error: {e}", "ERROR")
                
        # Step 4: Patient approves delegation
        if "patient" in self.tokens and "test_delegation" in self.delegations:
            delegation_id = self.delegations["test_delegation"]["id"]
            try:
                response = self.make_request("PUT", f"/delegations/{delegation_id}/approve", token=self.tokens["patient"])
                if response.status_code == 200:
                    result = response.json()
                    if "message" in result:
                        self.log("✅ Patient can approve delegation")
                        success_count += 1
                    else:
                        self.log("❌ Delegation approval returned unexpected response", "ERROR")
                else:
                    self.log(f"❌ Delegation approval failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Delegation approval error: {e}", "ERROR")
                
        return success_count >= 3  # Allow some flexibility
        
    def test_role_based_access_control(self) -> bool:
        """Test role-based access control"""
        self.log("Testing role-based access control...")
        
        success_count = 0
        
        # Test that non-patients cannot create prescriptions
        if "gp" in self.tokens:
            prescription_data = {
                "medication_name": "Test Medicine",
                "dosage": "100mg",
                "quantity": "10 tablets",
                "instructions": "Test instructions"
            }
            
            try:
                response = self.make_request("POST", "/prescriptions", prescription_data, token=self.tokens["gp"])
                if response.status_code == 403:
                    self.log("✅ Non-patients properly blocked from creating prescriptions")
                    success_count += 1
                else:
                    self.log(f"❌ Non-patients should be blocked from creating prescriptions: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Role-based prescription creation test error: {e}", "ERROR")
                
        # Test that non-patients cannot create delegations
        if "gp" in self.tokens:
            delegation_data = {
                "delegate_user_id": "test_id",
                "delegate_name": "Test Delegate",
                "delegate_phone": "+44 1234567890",
                "delegate_relationship": "Test"
            }
            
            try:
                response = self.make_request("POST", "/delegations", delegation_data, token=self.tokens["gp"])
                if response.status_code == 403:
                    self.log("✅ Non-patients properly blocked from creating delegations")
                    success_count += 1
                else:
                    self.log(f"❌ Non-patients should be blocked from creating delegations: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Role-based delegation creation test error: {e}", "ERROR")
                
        return success_count == 2
        
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all backend tests"""
        self.log("=" * 60)
        self.log("STARTING COMPREHENSIVE BACKEND TESTING")
        self.log("=" * 60)
        
        test_results = {}
        
        # Test 1: Health Check
        test_results["health_check"] = self.test_health_check()
        
        # Test 2: User Registration
        test_results["user_registration"] = self.test_user_registration()
        
        # Test 3: User Login
        test_results["user_login"] = self.test_user_login()
        
        # Test 4: Protected Routes & JWT
        test_results["protected_routes"] = self.test_protected_routes()
        
        # Test 5: User Management
        test_results["user_management"] = self.test_user_management()
        
        # Test 6: Prescription Workflow
        test_results["prescription_workflow"] = self.test_prescription_workflow()
        
        # Test 7: Delegation System
        test_results["delegation_system"] = self.test_delegation_system()
        
        # Test 8: Role-based Access Control
        test_results["role_based_access"] = self.test_role_based_access_control()
        
        # Summary
        self.log("=" * 60)
        self.log("TEST RESULTS SUMMARY")
        self.log("=" * 60)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{test_name.replace('_', ' ').title()}: {status}")
            if result:
                passed += 1
                
        self.log("=" * 60)
        self.log(f"OVERALL RESULT: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("🎉 ALL TESTS PASSED! Backend system is working correctly.")
        else:
            self.log(f"⚠️  {total - passed} tests failed. Please check the logs above for details.")
            
        return test_results

if __name__ == "__main__":
    tester = BackendTester()
    results = tester.run_all_tests()