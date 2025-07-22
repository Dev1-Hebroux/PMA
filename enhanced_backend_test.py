#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Enhanced NHS-Integrated Prescription Management System
Tests enhanced authentication, advanced prescription workflow, notifications, analytics, and compliance features
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

# Configuration
BASE_URL = "https://ab6009e8-2e3e-4cd0-b3b8-a452a86b19f9.preview.emergentagent.com/api"
TIMEOUT = 30

class EnhancedBackendTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.timeout = TIMEOUT
        self.tokens = {}  # Store tokens for different users
        self.users = {}   # Store user data
        self.prescriptions = {}  # Store prescription data
        self.delegations = {}    # Store delegation data
        self.notifications = {}  # Store notification data
        
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
            
    def test_enhanced_authentication(self) -> bool:
        """Test enhanced authentication system with NHS numbers and GDPR consent"""
        self.log("Testing enhanced authentication system...")
        
        success_count = 0
        timestamp = str(int(time.time()))
        
        # Test enhanced user registration with NHS numbers and GDPR consent
        enhanced_users = [
            {
                "role": "patient",
                "email": f"nhs.patient.{timestamp}@email.com",
                "password": "SecurePass123!",
                "full_name": "NHS Patient Test",
                "nhs_number": "1234567890",  # 10-digit NHS number
                "phone": "+44 7700 900123",
                "address": "123 NHS Street, London, SW1A 1AA",
                "date_of_birth": "1990-01-01T00:00:00",
                "gdpr_consent": True
            },
            {
                "role": "gp", 
                "email": f"nhs.gp.{timestamp}@medicalpractice.com",
                "password": "DoctorPass456!",
                "full_name": "Dr. NHS GP Test",
                "gp_license_number": "GMC123456",
                "ods_code": "NHS001",
                "phone": "+44 7700 900456",
                "gdpr_consent": True
            },
            {
                "role": "pharmacy",
                "email": f"nhs.pharmacy.{timestamp}@pharmacy.com", 
                "password": "PharmacyPass789!",
                "full_name": "NHS Pharmacy Test",
                "pharmacy_license_number": "GPhC987654",
                "ods_code": "NHS002",
                "phone": "+44 7700 900789",
                "gdpr_consent": True
            }
        ]
        
        for user_data in enhanced_users:
            try:
                response = self.make_request("POST", "/auth/register", user_data)
                
                if response.status_code == 200:
                    token_data = response.json()
                    # Check for enhanced token data
                    required_fields = ["access_token", "token_type", "user_id", "role", "expires_in"]
                    if all(key in token_data for key in required_fields):
                        self.tokens[user_data["role"]] = token_data["access_token"]
                        self.users[user_data["role"]] = {
                            "user_id": token_data["user_id"],
                            "email": user_data["email"],
                            "role": user_data["role"],
                            "full_name": user_data["full_name"]
                        }
                        self.log(f"✅ Enhanced {user_data['role'].title()} registration with NHS data successful")
                        success_count += 1
                    else:
                        self.log(f"❌ {user_data['role'].title()} registration missing enhanced token fields", "ERROR")
                else:
                    error_msg = response.text
                    self.log(f"❌ Enhanced {user_data['role'].title()} registration failed: {response.status_code} - {error_msg}", "ERROR")
                    
            except Exception as e:
                self.log(f"❌ Enhanced {user_data['role'].title()} registration error: {e}", "ERROR")
        
        # Test NHS number validation
        try:
            invalid_nhs_user = {
                "role": "patient",
                "email": f"invalid.nhs.{timestamp}@email.com",
                "password": "SecurePass123!",
                "full_name": "Invalid NHS Test",
                "nhs_number": "123",  # Invalid NHS number (too short)
                "gdpr_consent": True
            }
            response = self.make_request("POST", "/auth/register", invalid_nhs_user)
            if response.status_code == 400:
                self.log("✅ NHS number validation working correctly")
                success_count += 1
            else:
                self.log(f"❌ NHS number validation should reject invalid numbers: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ NHS number validation test error: {e}", "ERROR")
            
        return success_count >= 3
        
    def test_advanced_prescription_workflow(self) -> bool:
        """Test advanced prescription workflow with QR codes, PINs, and priority levels"""
        self.log("Testing advanced prescription workflow...")
        
        success_count = 0
        
        if "patient" not in self.tokens:
            self.log("❌ No patient token available for prescription testing", "ERROR")
            return False
            
        # Test prescription creation with enhanced fields
        enhanced_prescription_data = {
            "medication_name": "Amoxicillin 500mg",
            "medication_code": "SNOMED123456",  # SNOMED CT code
            "dosage": "500mg",
            "quantity": "21 capsules",
            "instructions": "Take one capsule three times daily with food for 7 days",
            "indication": "Bacterial infection treatment",
            "prescription_type": "acute",
            "notes": "Patient has mild penicillin allergy - monitor for reactions",
            "priority": "urgent",
            "max_repeats": 0
        }
        
        try:
            response = self.make_request("POST", "/prescriptions", enhanced_prescription_data, token=self.tokens["patient"])
            if response.status_code == 200:
                prescription = response.json()
                # Check for enhanced prescription fields
                enhanced_fields = ["qr_code", "collection_pin", "priority", "prescription_type", "medication_code"]
                if all(field in prescription for field in enhanced_fields):
                    self.prescriptions["enhanced_prescription"] = prescription
                    self.log("✅ Enhanced prescription creation with QR code and PIN successful")
                    success_count += 1
                else:
                    missing_fields = [field for field in enhanced_fields if field not in prescription]
                    self.log(f"❌ Prescription missing enhanced fields: {missing_fields}", "ERROR")
            else:
                self.log(f"❌ Enhanced prescription creation failed: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ Enhanced prescription creation error: {e}", "ERROR")
            
        # Test prescription status transitions (enhanced workflow)
        if "enhanced_prescription" in self.prescriptions and "gp" in self.tokens:
            prescription_id = self.prescriptions["enhanced_prescription"]["id"]
            
            # GP approves prescription
            try:
                update_data = {
                    "status": "gp_approved",
                    "gp_notes": "Prescription approved with enhanced tracking"
                }
                response = self.make_request("PUT", f"/prescriptions/{prescription_id}", update_data, token=self.tokens["gp"])
                if response.status_code == 200:
                    updated_prescription = response.json()
                    if updated_prescription.get("status") == "gp_approved":
                        self.log("✅ Enhanced GP approval workflow working")
                        success_count += 1
                    else:
                        self.log(f"❌ GP approval status incorrect: {updated_prescription.get('status')}", "ERROR")
                else:
                    self.log(f"❌ Enhanced GP approval failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Enhanced GP approval error: {e}", "ERROR")
                
            # Pharmacy dispenses prescription (enhanced status)
            if "pharmacy" in self.tokens:
                try:
                    update_data = {
                        "status": "dispensed",  # Enhanced status
                        "pharmacy_notes": "Prescription dispensed with enhanced tracking"
                    }
                    response = self.make_request("PUT", f"/prescriptions/{prescription_id}", update_data, token=self.tokens["pharmacy"])
                    if response.status_code == 200:
                        updated_prescription = response.json()
                        # Should transition to ready_for_collection
                        if updated_prescription.get("status") == "ready_for_collection":
                            self.log("✅ Enhanced pharmacy dispensing workflow working")
                            success_count += 1
                        else:
                            self.log(f"❌ Pharmacy dispensing status incorrect: {updated_prescription.get('status')}", "ERROR")
                    else:
                        self.log(f"❌ Enhanced pharmacy dispensing failed: {response.status_code}", "ERROR")
                except Exception as e:
                    self.log(f"❌ Enhanced pharmacy dispensing error: {e}", "ERROR")
                    
        return success_count >= 2
        
    def test_notification_system(self) -> bool:
        """Test real-time notification system"""
        self.log("Testing notification system...")
        
        success_count = 0
        
        if "patient" not in self.tokens:
            self.log("❌ No patient token available for notification testing", "ERROR")
            return False
            
        # Test notification retrieval
        try:
            response = self.make_request("GET", "/notifications", token=self.tokens["patient"])
            if response.status_code == 200:
                notifications = response.json()
                if isinstance(notifications, list):
                    self.log("✅ Notification retrieval working")
                    success_count += 1
                    
                    # Store notifications for further testing
                    if notifications:
                        self.notifications["patient_notifications"] = notifications
                else:
                    self.log("❌ Notification retrieval returned invalid data", "ERROR")
            else:
                self.log(f"❌ Notification retrieval failed: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ Notification retrieval error: {e}", "ERROR")
            
        # Test notification marking as read
        if "patient_notifications" in self.notifications and self.notifications["patient_notifications"]:
            notification_id = self.notifications["patient_notifications"][0]["id"]
            try:
                response = self.make_request("PUT", f"/notifications/{notification_id}/read", token=self.tokens["patient"])
                if response.status_code == 200:
                    result = response.json()
                    if "message" in result:
                        self.log("✅ Notification mark as read working")
                        success_count += 1
                    else:
                        self.log("❌ Notification mark as read returned unexpected response", "ERROR")
                else:
                    self.log(f"❌ Notification mark as read failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Notification mark as read error: {e}", "ERROR")
                
        return success_count >= 1
        
    def test_enhanced_delegation_system(self) -> bool:
        """Test enhanced delegation system with PIN/QR codes and GDPR consent"""
        self.log("Testing enhanced delegation system...")
        
        success_count = 0
        
        if "patient" not in self.tokens or "delegate" not in self.users:
            self.log("❌ Missing patient token or delegate user for enhanced delegation test", "ERROR")
            return False
            
        # Test enhanced delegation creation
        enhanced_delegation_data = {
            "delegate_user_id": self.users["delegate"]["user_id"],
            "delegate_name": "Enhanced Delegate Test",
            "delegate_phone": "+44 7700 900321",
            "delegate_relationship": "Family Member",
            "permissions": ["collect_prescriptions"],
            "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "gdpr_consent": True
        }
        
        try:
            response = self.make_request("POST", "/delegations", enhanced_delegation_data, token=self.tokens["patient"])
            if response.status_code == 200:
                delegation = response.json()
                # Check for enhanced delegation fields
                enhanced_fields = ["pin_code", "qr_code", "gdpr_consent", "expires_at"]
                if all(field in delegation for field in enhanced_fields):
                    self.delegations["enhanced_delegation"] = delegation
                    self.log("✅ Enhanced delegation creation with PIN/QR code successful")
                    success_count += 1
                else:
                    missing_fields = [field for field in enhanced_fields if field not in delegation]
                    self.log(f"❌ Delegation missing enhanced fields: {missing_fields}", "ERROR")
            else:
                self.log(f"❌ Enhanced delegation creation failed: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ Enhanced delegation creation error: {e}", "ERROR")
            
        return success_count >= 1
        
    def test_analytics_and_reporting(self) -> bool:
        """Test analytics dashboard endpoint"""
        self.log("Testing analytics and reporting...")
        
        success_count = 0
        
        # Test analytics dashboard access for GP
        if "gp" in self.tokens:
            try:
                response = self.make_request("GET", "/analytics/dashboard", token=self.tokens["gp"])
                if response.status_code == 200:
                    analytics = response.json()
                    required_fields = ["total_prescriptions", "pending_prescriptions", "approved_prescriptions", "dispensed_prescriptions", "completion_rate"]
                    if all(field in analytics for field in required_fields):
                        self.log("✅ Analytics dashboard working for GP")
                        success_count += 1
                    else:
                        missing_fields = [field for field in required_fields if field not in analytics]
                        self.log(f"❌ Analytics dashboard missing fields: {missing_fields}", "ERROR")
                else:
                    self.log(f"❌ Analytics dashboard failed for GP: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Analytics dashboard error for GP: {e}", "ERROR")
                
        # Test analytics dashboard access for Pharmacy
        if "pharmacy" in self.tokens:
            try:
                response = self.make_request("GET", "/analytics/dashboard", token=self.tokens["pharmacy"])
                if response.status_code == 200:
                    analytics = response.json()
                    if isinstance(analytics, dict) and "total_prescriptions" in analytics:
                        self.log("✅ Analytics dashboard working for Pharmacy")
                        success_count += 1
                    else:
                        self.log("❌ Analytics dashboard returned invalid data for Pharmacy", "ERROR")
                else:
                    self.log(f"❌ Analytics dashboard failed for Pharmacy: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Analytics dashboard error for Pharmacy: {e}", "ERROR")
                
        # Test analytics access control (patient should be denied)
        if "patient" in self.tokens:
            try:
                response = self.make_request("GET", "/analytics/dashboard", token=self.tokens["patient"])
                if response.status_code == 403:
                    self.log("✅ Analytics dashboard properly restricts patient access")
                    success_count += 1
                else:
                    self.log(f"❌ Analytics dashboard should deny patient access: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Analytics access control test error: {e}", "ERROR")
                
        return success_count >= 2
        
    def test_user_profile_updates(self) -> bool:
        """Test user profile updates with protected fields"""
        self.log("Testing user profile updates...")
        
        success_count = 0
        
        if "patient" not in self.tokens:
            self.log("❌ No patient token available for profile update testing", "ERROR")
            return False
            
        # Test valid profile update
        try:
            update_data = {
                "phone": "+44 7700 999999",
                "address": "Updated Address, London, SW1A 1AA"
            }
            response = self.make_request("PUT", "/users/me", update_data, token=self.tokens["patient"])
            if response.status_code == 200:
                result = response.json()
                if "message" in result:
                    self.log("✅ User profile update working")
                    success_count += 1
                else:
                    self.log("❌ Profile update returned unexpected response", "ERROR")
            else:
                self.log(f"❌ User profile update failed: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ User profile update error: {e}", "ERROR")
            
        return success_count >= 1
        
    def test_pharmacy_nomination(self) -> bool:
        """Test pharmacy nomination endpoint"""
        self.log("Testing pharmacy nomination...")
        
        success_count = 0
        
        if "patient" not in self.tokens or "pharmacy" not in self.users:
            self.log("❌ Missing patient token or pharmacy user for nomination test", "ERROR")
            return False
            
        # Test pharmacy nomination
        try:
            nomination_data = {
                "pharmacy_id": self.users["pharmacy"]["user_id"],
                "pharmacy_name": "Test Pharmacy",
                "pharmacy_address": "123 Pharmacy Street, London",
                "ods_code": "NHS002"
            }
            response = self.make_request("POST", "/users/nominate-pharmacy", nomination_data, token=self.tokens["patient"])
            if response.status_code == 200:
                result = response.json()
                if "message" in result:
                    self.log("✅ Pharmacy nomination working")
                    success_count += 1
                else:
                    self.log("❌ Pharmacy nomination returned unexpected response", "ERROR")
            else:
                self.log(f"❌ Pharmacy nomination failed: {response.status_code}", "ERROR")
        except Exception as e:
            self.log(f"❌ Pharmacy nomination error: {e}", "ERROR")
            
        # Test that non-patients cannot nominate pharmacies
        if "gp" in self.tokens:
            try:
                nomination_data = {
                    "pharmacy_id": "test_id",
                    "pharmacy_name": "Test Pharmacy",
                    "pharmacy_address": "123 Test Street",
                    "ods_code": "TEST001"
                }
                response = self.make_request("POST", "/users/nominate-pharmacy", nomination_data, token=self.tokens["gp"])
                if response.status_code == 403:
                    self.log("✅ Non-patients properly blocked from nominating pharmacies")
                    success_count += 1
                else:
                    self.log(f"❌ Non-patients should be blocked from nominating pharmacies: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Pharmacy nomination access control test error: {e}", "ERROR")
                
        return success_count >= 1
        
    def run_enhanced_tests(self) -> Dict[str, bool]:
        """Run all enhanced backend tests"""
        self.log("=" * 70)
        self.log("STARTING ENHANCED NHS-INTEGRATED BACKEND TESTING")
        self.log("=" * 70)
        
        test_results = {}
        
        # Enhanced Test 1: Enhanced Authentication System
        test_results["enhanced_authentication"] = self.test_enhanced_authentication()
        
        # Enhanced Test 2: Advanced Prescription Workflow
        test_results["advanced_prescription_workflow"] = self.test_advanced_prescription_workflow()
        
        # Enhanced Test 3: Notification System
        test_results["notification_system"] = self.test_notification_system()
        
        # Enhanced Test 4: Enhanced Delegation System
        test_results["enhanced_delegation_system"] = self.test_enhanced_delegation_system()
        
        # Enhanced Test 5: Analytics and Reporting
        test_results["analytics_and_reporting"] = self.test_analytics_and_reporting()
        
        # Enhanced Test 6: User Profile Updates
        test_results["user_profile_updates"] = self.test_user_profile_updates()
        
        # Enhanced Test 7: Pharmacy Nomination
        test_results["pharmacy_nomination"] = self.test_pharmacy_nomination()
        
        # Summary
        self.log("=" * 70)
        self.log("ENHANCED TEST RESULTS SUMMARY")
        self.log("=" * 70)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{test_name.replace('_', ' ').title()}: {status}")
            if result:
                passed += 1
                
        self.log("=" * 70)
        self.log(f"ENHANCED OVERALL RESULT: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("🎉 ALL ENHANCED TESTS PASSED! NHS-Integrated Backend system is working correctly.")
        else:
            self.log(f"⚠️  {total - passed} enhanced tests failed. Please check the logs above for details.")
            
        return test_results

if __name__ == "__main__":
    tester = EnhancedBackendTester()
    results = tester.run_enhanced_tests()