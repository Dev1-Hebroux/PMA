#!/usr/bin/env python3
"""
Debug prescription creation issue
"""

import requests
import json

BASE_URL = "https://f6b00ae1-f513-4038-91eb-ddf68c5cea24.preview.emergentagent.com/api"

def debug_prescription_creation():
    # First register a patient
    patient_data = {
        "role": "patient",
        "email": "debug.patient@email.com",
        "password": "SecurePass123!",
        "full_name": "Debug Patient",
        "nhs_number": "1234567890",
        "gdpr_consent": True
    }
    
    print("Registering patient...")
    response = requests.post(f"{BASE_URL}/auth/register", json=patient_data)
    print(f"Registration status: {response.status_code}")
    
    if response.status_code == 200:
        token_data = response.json()
        token = token_data["access_token"]
        print(f"Got token: {token[:20]}...")
        
        # Try to create prescription
        prescription_data = {
            "medication_name": "Test Medicine",
            "dosage": "100mg",
            "quantity": "10 tablets",
            "instructions": "Take once daily"
        }
        
        print("Creating prescription...")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        response = requests.post(f"{BASE_URL}/prescriptions", json=prescription_data, headers=headers)
        print(f"Prescription creation status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code != 200:
            print("Error details:")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2))
            except:
                print(response.text)
    else:
        print(f"Registration failed: {response.text}")

if __name__ == "__main__":
    debug_prescription_creation()