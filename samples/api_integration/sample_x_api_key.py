import requests
import os
import json

# LBS API Configuration
BASE_URL = os.getenv("LBS_BASE_URL", "http://localhost:8100/api/lbs")

# Credentials for Login (Pattern 1)
USERNAME = os.getenv("LBS_USERNAME", "dev-user")
PASSWORD = os.getenv("LBS_PASSWORD", "password")

# Pre-provided JWT (Pattern 2 - if login is not desired)
MANUAL_JWT = os.getenv("LBS_ACCESS_TOKEN", None)

def get_jwt_via_login():
    """Pattern 1: Get system JWT by authorizing with login api."""
    print("--- Pattern 1: Getting JWT via Login ---")
    payload = {
        "username_or_email": USERNAME,
        "password": PASSWORD
    }
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=payload)
        response.raise_for_status()
        token = response.json().get("access_token")
        print("Successfully obtained JWT via login.")
        return token
    except Exception as e:
        print(f"Login failed: {e}")
        return None

def create_x_api_key(jwt_token):
    """Step 2: Generate a new X-API-KEY using the JWT."""
    print("\n--- Step 2: Generating X-API-KEY ---")
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "client_id": "sample-python-client",
        "scopes": ["read", "write"],
        "expires_in_days": 30
    }
    try:
        response = requests.post(f"{BASE_URL}/auth/api-keys", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        api_key = data.get("api_key")
        print(f"Key Created: {data.get('client_id')} (ID: {data.get('id')})")
        print(f"API KEY: {api_key} (Store this securely!)")
        return api_key
    except Exception as e:
        print(f"Failed to create API key: {e}")
        return None

def call_api_with_key(api_key):
    """Step 3: Call LBS APIs using the X-API-KEY."""
    print("\n--- Step 3: Calling API with X-API-KEY ---")
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(f"{BASE_URL}/health", headers=headers)
        response.raise_for_status()
        print("Health Check successful with API Key.")
        
        response = requests.get(f"{BASE_URL}/dashboard", headers=headers)
        response.raise_for_status()
        print(f"Dashboard Data: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"API call with X-API-KEY failed: {e}")

if __name__ == "__main__":
    print(f"X-API-KEY Generation & Usage Sample (Base URL: {BASE_URL})")
    
    # Choice of Pattern
    jwt = MANUAL_JWT
    if not jwt:
        jwt = get_jwt_via_login()
    else:
        print("--- Pattern 2: Using provided LBS_ACCESS_TOKEN ---")

    if jwt:
        new_key = create_x_api_key(jwt)
        if new_key:
            call_api_with_key(new_key)
    else:
        print("Error: No valid JWT obtained. Cannot proceed.")
