#!/usr/bin/env python3
"""
Enhanced Features Testing for PMA Backend
Tests notification system, analytics dashboard, and audit features
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any

# Configuration
BASE_URL = "https://ab6009e8-2e3e-4cd0-b3b8-a452a86b19f9.preview.emergentagent.com/api"
TIMEOUT = 30

class EnhancedFeaturesTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.timeout = TIMEOUT
        self.tokens = {}
        self.users = {}
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def make_request(self, method: str, endpoint: str, data: Dict = None, 
                    headers: Dict = None, token: str = None) -> requests.Response:
        """Make HTTP request with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        
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
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            return response
        except requests.exceptions.RequestException as e:
            self.log(f"Request failed: {e}", "ERROR")
            raise
            
    def setup_test_users(self) -> bool:
        """Set up test users for enhanced features testing"""
        self.log("Setting up test users...")
        
        timestamp = str(int(time.time()))
        
        test_users = [
            {
                "role": "patient",
                "email": f"enhanced.patient.{timestamp}@email.com",
                "password": "EnhancedPass123!",
                "full_name": "Enhanced Test Patient",
                "phone": "+44 7700 900111",
                "nhs_number": "1234567890",
                "gdpr_consent": True
            },
            {
                "role": "gp", 
                "email": f"enhanced.gp.{timestamp}@medicalpractice.com",
                "password": "EnhancedGP456!",
                "full_name": "Dr. Enhanced GP",
                "phone": "+44 7700 900222",
                "gp_license_number": "GMC111111",
                "gdpr_consent": True
            },
            {
                "role": "pharmacy",
                "email": f"enhanced.pharmacy.{timestamp}@pharmacy.com", 
                "password": "EnhancedPharm789!",
                "full_name": "Enhanced Test Pharmacy",
                "phone": "+44 7700 900333",
                "pharmacy_license_number": "GPhC222222",
                "gdpr_consent": True
            }
        ]
        
        success_count = 0
        
        for user_data in test_users:
            try:
                response = self.make_request("POST", "/auth/register", user_data)
                
                if response.status_code == 200:
                    token_data = response.json()
                    self.tokens[user_data["role"]] = token_data["access_token"]
                    self.users[user_data["role"]] = {
                        "user_id": token_data["user_id"],
                        "email": user_data["email"],
                        "role": user_data["role"],
                        "full_name": user_data["full_name"]
                    }
                    self.log(f"✅ {user_data['role'].title()} user setup successful")
                    success_count += 1
                else:
                    self.log(f"❌ {user_data['role'].title()} user setup failed: {response.status_code}", "ERROR")
                    
            except Exception as e:
                self.log(f"❌ {user_data['role'].title()} user setup error: {e}", "ERROR")
                
        return success_count == len(test_users)
        
    def test_notification_system(self) -> bool:
        """Test notification system functionality"""
        self.log("Testing notification system...")
        
        success_count = 0
        
        # Test 1: Get notifications for patient
        if "patient" in self.tokens:
            try:
                response = self.make_request("GET", "/notifications", token=self.tokens["patient"])
                if response.status_code == 200:
                    notifications = response.json()
                    if isinstance(notifications, list):
                        self.log("✅ Notification retrieval working")
                        success_count += 1
                    else:
                        self.log("❌ Notification retrieval returned invalid data", "ERROR")
                else:
                    self.log(f"❌ Notification retrieval failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Notification retrieval error: {e}", "ERROR")
        
        # Test 2: Create a prescription to generate notifications
        if "patient" in self.tokens:
            prescription_data = {
                "medication_name": "Enhanced Test Medicine",
                "dosage": "200mg",
                "quantity": "14 tablets",
                "instructions": "Take twice daily with meals",
                "notes": "Enhanced testing prescription"
            }
            
            try:
                response = self.make_request("POST", "/prescriptions", prescription_data, token=self.tokens["patient"])
                if response.status_code == 200:
                    self.log("✅ Prescription created for notification testing")
                    success_count += 1
                    
                    # Wait a moment for notification to be created
                    time.sleep(1)
                    
                    # Check if notification was created
                    response = self.make_request("GET", "/notifications", token=self.tokens["patient"])
                    if response.status_code == 200:
                        notifications = response.json()
                        if len(notifications) > 0:
                            self.log("✅ Notification created after prescription submission")
                            success_count += 1
                            
                            # Test marking notification as read
                            notification_id = notifications[0]["id"]
                            response = self.make_request("PUT", f"/notifications/{notification_id}/read", token=self.tokens["patient"])
                            if response.status_code == 200:
                                self.log("✅ Notification mark-as-read working")
                                success_count += 1
                            else:
                                self.log(f"❌ Notification mark-as-read failed: {response.status_code}", "ERROR")
                        else:
                            self.log("❌ No notifications found after prescription creation", "ERROR")
                    else:
                        self.log(f"❌ Failed to retrieve notifications after prescription: {response.status_code}", "ERROR")
                else:
                    self.log(f"❌ Prescription creation for notification test failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Prescription creation for notification test error: {e}", "ERROR")
        
        return success_count >= 3
        
    def test_analytics_dashboard(self) -> bool:
        """Test analytics dashboard functionality"""
        self.log("Testing analytics dashboard...")
        
        success_count = 0
        
        # Test 1: GP access to analytics
        if "gp" in self.tokens:
            try:
                response = self.make_request("GET", "/analytics/dashboard", token=self.tokens["gp"])
                if response.status_code == 200:
                    analytics = response.json()
                    required_fields = ["total_prescriptions", "pending_prescriptions", "approved_prescriptions", "dispensed_prescriptions", "completion_rate"]
                    if all(field in analytics for field in required_fields):
                        self.log("✅ GP analytics dashboard working with all required fields")
                        success_count += 1
                    else:
                        self.log(f"❌ GP analytics missing required fields: {analytics}", "ERROR")
                else:
                    self.log(f"❌ GP analytics dashboard failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ GP analytics dashboard error: {e}", "ERROR")
        
        # Test 2: Pharmacy access to analytics
        if "pharmacy" in self.tokens:
            try:
                response = self.make_request("GET", "/analytics/dashboard", token=self.tokens["pharmacy"])
                if response.status_code == 200:
                    analytics = response.json()
                    required_fields = ["total_prescriptions", "pending_prescriptions", "approved_prescriptions", "dispensed_prescriptions", "completion_rate"]
                    if all(field in analytics for field in required_fields):
                        self.log("✅ Pharmacy analytics dashboard working with all required fields")
                        success_count += 1
                    else:
                        self.log(f"❌ Pharmacy analytics missing required fields: {analytics}", "ERROR")
                else:
                    self.log(f"❌ Pharmacy analytics dashboard failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Pharmacy analytics dashboard error: {e}", "ERROR")
        
        # Test 3: Patient access should be denied
        if "patient" in self.tokens:
            try:
                response = self.make_request("GET", "/analytics/dashboard", token=self.tokens["patient"])
                if response.status_code == 403:
                    self.log("✅ Patient access to analytics properly denied")
                    success_count += 1
                else:
                    self.log(f"❌ Patient should be denied analytics access: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Patient analytics access test error: {e}", "ERROR")
        
        return success_count == 3
        
    def test_user_profile_updates(self) -> bool:
        """Test user profile update functionality"""
        self.log("Testing user profile updates...")
        
        success_count = 0
        
        if "patient" in self.tokens:
            # Test updating allowed fields
            update_data = {
                "phone": "+44 7700 999888",
                "address": "Updated Address, London, SW1A 1AA"
            }
            
            try:
                response = self.make_request("PUT", "/users/me", update_data, token=self.tokens["patient"])
                if response.status_code == 200:
                    result = response.json()
                    if "message" in result:
                        self.log("✅ User profile update working")
                        success_count += 1
                    else:
                        self.log(f"❌ User profile update returned unexpected response: {result}", "ERROR")
                else:
                    self.log(f"❌ User profile update failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ User profile update error: {e}", "ERROR")
        
        return success_count == 1
        
    def test_pharmacy_nomination(self) -> bool:
        """Test pharmacy nomination functionality"""
        self.log("Testing pharmacy nomination...")
        
        success_count = 0
        
        if "patient" in self.tokens and "pharmacy" in self.users:
            nomination_data = {
                "pharmacy_id": self.users["pharmacy"]["user_id"],
                "pharmacy_name": "Enhanced Test Pharmacy",
                "pharmacy_address": "123 Pharmacy Street, London",
                "ods_code": "ABC123"
            }
            
            try:
                response = self.make_request("POST", "/users/nominate-pharmacy", nomination_data, token=self.tokens["patient"])
                if response.status_code == 200:
                    result = response.json()
                    if "message" in result:
                        self.log("✅ Pharmacy nomination working")
                        success_count += 1
                    else:
                        self.log(f"❌ Pharmacy nomination returned unexpected response: {result}", "ERROR")
                else:
                    self.log(f"❌ Pharmacy nomination failed: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Pharmacy nomination error: {e}", "ERROR")
        
        # Test that non-patients cannot nominate pharmacies
        if "gp" in self.tokens:
            nomination_data = {
                "pharmacy_id": "test_id",
                "pharmacy_name": "Test Pharmacy",
                "pharmacy_address": "Test Address",
                "ods_code": "TEST123"
            }
            
            try:
                response = self.make_request("POST", "/users/nominate-pharmacy", nomination_data, token=self.tokens["gp"])
                if response.status_code == 403:
                    self.log("✅ Non-patients properly blocked from pharmacy nomination")
                    success_count += 1
                else:
                    self.log(f"❌ Non-patients should be blocked from pharmacy nomination: {response.status_code}", "ERROR")
            except Exception as e:
                self.log(f"❌ Non-patient pharmacy nomination test error: {e}", "ERROR")
        
        return success_count == 2
        
    def run_enhanced_tests(self) -> Dict[str, bool]:
        """Run all enhanced feature tests"""
        self.log("=" * 60)
        self.log("STARTING ENHANCED FEATURES TESTING")
        self.log("=" * 60)
        
        test_results = {}
        
        # Setup test users
        if not self.setup_test_users():
            self.log("❌ Failed to setup test users. Cannot continue with enhanced tests.", "ERROR")
            return {"setup_failed": False}
        
        # Test enhanced features
        test_results["notification_system"] = self.test_notification_system()
        test_results["analytics_dashboard"] = self.test_analytics_dashboard()
        test_results["user_profile_updates"] = self.test_user_profile_updates()
        test_results["pharmacy_nomination"] = self.test_pharmacy_nomination()
        
        # Summary
        self.log("=" * 60)
        self.log("ENHANCED FEATURES TEST RESULTS")
        self.log("=" * 60)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{test_name.replace('_', ' ').title()}: {status}")
            if result:
                passed += 1
                
        self.log("=" * 60)
        self.log(f"ENHANCED FEATURES RESULT: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("🎉 ALL ENHANCED FEATURES TESTS PASSED!")
        else:
            self.log(f"⚠️  {total - passed} enhanced feature tests failed.")
            
        return test_results

if __name__ == "__main__":
    tester = EnhancedFeaturesTester()
    results = tester.run_enhanced_tests()