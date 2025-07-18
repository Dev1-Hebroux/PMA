#!/usr/bin/env python3
import requests
import time

BASE_URL = "https://f6b00ae1-f513-4038-91eb-ddf68c5cea24.preview.emergentagent.com/api"

def simple_health_check():
    try:
        print("Testing health endpoint...")
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

if __name__ == "__main__":
    result = simple_health_check()
    print(f"Health check result: {result}")