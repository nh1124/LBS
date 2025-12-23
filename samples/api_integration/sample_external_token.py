import requests
import os
import json

# LBS API Configuration
BASE_URL = os.getenv("LBS_BASE_URL", "http://localhost:8100/api/lbs")
# This should be a JWT token issued by the HOST system that LBS trusts.
EXTERNAL_JWT = os.getenv("EXTERNAL_SYSTEM_TOKEN", "your_external_jwt_here")

headers = {
    "Authorization": f"Bearer {EXTERNAL_JWT}",
    "Content-Type": "application/json"
}

def verify_identity():
    """Verify the current identity mapped from the external token."""
    print("--- Verify Identity ---")
    try:
        # Note: /auth/me might be under /api/auth or /api/lbs depending on final routing
        # Adjusting to /api/lbs/auth/me based on docs/API_USAGE_GUIDE.md table
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        response.raise_for_status()
        print(f"Status: {response.status_code}")
        print(f"User Info: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def list_tasks():
    """List tasks assigned to the user associated with this token."""
    print("\n--- Listing Tasks ---")
    try:
        response = requests.get(f"{BASE_URL}/tasks", headers=headers)
        response.raise_for_status()
        tasks = response.json()
        print(f"Found {len(tasks)} tasks.")
        for task in tasks[:5]: # Show first 5
            print(f"- [{task.get('id')}] {task.get('title')} (Due: {task.get('due_date')})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print(f"Using Base URL: {BASE_URL}")
    verify_identity()
    list_tasks()
