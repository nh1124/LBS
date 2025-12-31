import os
from datetime import date, timedelta
from lbs_client import LBSClient

# --- Configuration ---
LBS_URL = "http://localhost:8100/api/lbs"
# For API Key pattern, you can set LBS_API_KEY environment variable
# os.environ["LBS_API_KEY"] = "your_key_here"

def run_api_key_example():
    print("\n--- Running API Key Example ---")
    # Initialize with API Key (can also be picked from LBS_API_KEY env var)
    client = LBSClient(base_url=LBS_URL, api_key="your_secret_api_key_here")
    
    try:
        health = client.health_check()
        print(f"Health: {health}")
        
        # Identity check
        # identity = client.verify_identity()
        # print(f"Identity: {identity}")
        
    except Exception as e:
        print(f"Error: {e}")

def run_login_example():
    print("\n--- Running Login Example ---")
    client = LBSClient(base_url=LBS_URL)
    
    try:
        # Perform Login
        token = client.login(username_or_email="admin", password="password")
        print(f"Login successful! Token acquired.")
        
        # CRUD Operations
        print("Creating a task...")
        new_task = client.create_task({
            "task_name": "Sample Task from Client",
            "context": "work",
            "base_load_score": 5.0,
            "rule_type": "WEEKLY",
            "mon": True,
            "wed": True,
            "fri": True,
            "start_date": date.today().isoformat()
        })
        print(f"Task created: {new_task['task_id']}")
        
        print("Listing tasks...")
        tasks = client.list_tasks(context="work")
        print(f"Found {len(tasks)} tasks in 'work' context.")
        
        # Analysis
        print("Fetching dashboard...")
        dashboard = client.get_dashboard()
        print(f"Today's total load: {dashboard['today']['adjusted_load']}")
        
    except Exception as e:
        print(f"Error: {e}")

def run_csv_example():
    print("\n--- Running CSV Upload Example ---")
    client = LBSClient(base_url=LBS_URL)
    # Assume we are already logged in or have a token/key
    # client.api_key = "..."
    
    # Create a dummy CSV for example
    csv_content = """task_name,context,base_load_score,rule_type,mon,tue,wed,thu,fri,sat,sun,start_date
Imported Task 1,work,3.0,WEEKLY,true,false,true,false,true,false,false,2026-01-01
Imported Task 2,personal,2.0,ONCE,false,false,false,false,false,false,false,2026-01-10
"""
    csv_file = "sample_tasks.csv"
    with open(csv_file, "w") as f:
        f.write(csv_content)
    
    try:
        print(f"Uploading {csv_file}...")
        # result = client.upload_csv(csv_file)
        # print(f"Upload result: {result}")
        print("(Upload call commented out - requires valid auth)")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if os.path.exists(csv_file):
            os.remove(csv_file)

if __name__ == "__main__":
    print("LBS Client Examples")
    run_api_key_example()
    # run_login_example()
    # run_csv_example()
