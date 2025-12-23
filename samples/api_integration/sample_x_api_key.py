import requests
import os
import json

# LBS API Configuration
BASE_URL = os.getenv("LBS_BASE_URL", "http://localhost:8100/api/lbs")
API_KEY = os.getenv("LBS_API_KEY", "your_secret_api_key_here")

headers = {
    "X-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

def check_health():
    """Check LBS system status."""
    print("--- Health Check ---")
    try:
        response = requests.get(f"{BASE_URL}/health", headers=headers)
        response.raise_for_status()
        print(f"Status: {response.status_code}")
        print(f"Data: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def get_dashboard():
    """Get current load summary and predictions."""
    print("\n--- Dashboard Summary ---")
    try:
        response = requests.get(f"{BASE_URL}/dashboard", headers=headers)
        response.raise_for_status()
        data = response.json()
        print(f"Total Load: {data.get('total_load', 'N/A')}")
        print(f"Message: {data.get('message', 'N/A')}")
    except Exception as e:
        print(f"Error: {e}")

def create_task(title, load, due_date):
    """Create a new LBS task."""
    print(f"\n--- Creating Task: {title} ---")
    payload = {
        "title": title,
        "load": load,
        "due_date": due_date,
        "context": "external-integration-sample"
    }
    try:
        response = requests.post(f"{BASE_URL}/tasks", headers=headers, json=payload)
        response.raise_for_status()
        print(f"Task Created: {response.json().get('id')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print(f"Using Base URL: {BASE_URL}")
    check_health()
    get_dashboard()
    # Uncomment to test task creation
    # create_task("Sample Task via API Key", 20.0, "2023-12-31")
