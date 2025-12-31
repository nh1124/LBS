import requests
import os
from datetime import date, datetime
from typing import List, Optional, Dict, Any, Union

class LBSClient:
    """
    Life Balance System (LBS) API Client.
    
    Supports:
    - X-API-KEY (Recommended for AI/Automation)
    - Bearer Token (JWT)
    - Username/Password (Login Flow)
    """

    def __init__(
        self, 
        base_url: str = "http://localhost:8100/api/lbs", 
        api_key: Optional[str] = None, 
        token: Optional[str] = None
    ):
        """
        Initialize the LBS Client.
        
        :param base_url: The base URL of the LBS service (default: http://localhost:8100/api/lbs)
        :param api_key: X-API-KEY for authentication.
        :param token: JWT Bearer token for authentication.
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("LBS_API_KEY")
        self.token = token
        self._session = requests.Session()

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            headers["X-API-KEY"] = self.api_key
        elif self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = self._get_headers()
        
        # Merge headers if provided in kwargs
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))
            
        response = self._session.request(method, url, headers=headers, **kwargs)
        
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            # Try to extract error detail from JSON response
            try:
                error_data = response.json()
                detail = error_data.get("detail", str(e))
                raise requests.HTTPError(f"{response.status_code} Client Error: {detail} for url: {url}") from e
            except Exception:
                raise e

        if response.status_code == 204:
            return None
        return response.json()

    # --- Authentication Methods ---

    def login(self, username_or_email: str, password: str) -> str:
        """
        Login with username/email and password to obtain a JWT.
        Sets self.token automatically.
        """
        payload = {
            "username_or_email": username_or_email,
            "password": password
        }
        # Login is usually under /auth/login
        # Our base_url is /api/lbs, but the route is /auth/login
        data = self._request("POST", "auth/login", json=payload)
        self.token = data.get("access_token")
        return self.token

    def verify_identity(self) -> Dict:
        """Verify current identity status (/auth/me)"""
        return self._request("GET", "auth/me")

    # --- Task Operations ---

    def list_tasks(self, context: Optional[str] = None) -> List[Dict]:
        """List tasks, optionally filtered by context."""
        params = {}
        if context:
            params["context"] = context
        return self._request("GET", "tasks", params=params)

    def get_task(self, task_id: str) -> Dict:
        """Get detailed task information."""
        return self._request("GET", f"tasks/{task_id}")

    def create_task(self, task_data: Dict) -> Dict:
        """Create a new LBS task."""
        return self._request("POST", "tasks", json=task_data)

    def update_task(self, task_id: str, task_data: Dict) -> Dict:
        """Update an existing task."""
        return self._request("PUT", f"tasks/{task_id}", json=task_data)

    def delete_task(self, task_id: str) -> Dict:
        """Delete a task."""
        return self._request("DELETE", f"tasks/{task_id}")

    def bulk_delete_tasks(self, task_ids: List[str]) -> Dict:
        """Delete multiple tasks by ID list."""
        return self._request("POST", "tasks/bulk-delete", json={"task_ids": task_ids})

    def bulk_update_status(self, task_ids: List[str], active: bool) -> Dict:
        """Update active status for multiple tasks."""
        return self._request("POST", "tasks/bulk-update-status", json={"task_ids": task_ids, "active": active})

    def upload_csv(self, file_path: str) -> Dict:
        """Bulk import tasks via CSV file."""
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'text/csv')}
            # Note: We need to override headers for multipart/form-data
            headers = self._get_headers()
            del headers["Content-Type"] # requests will set this with boundary
            url = f"{self.base_url}/tasks/upload-csv"
            response = self._session.post(url, headers=headers, files=files)
            response.raise_for_status()
            return response.json()

    # --- Load Analysis & Insights ---

    def get_dashboard(self, start_date: Optional[Union[date, str]] = None) -> Dict:
        """Get summary of current load and predictions."""
        params = {}
        if start_date:
            params["start_date"] = start_date.isoformat() if isinstance(start_date, date) else start_date
        return self._request("GET", "dashboard", params=params)

    def get_heatmap(self, start: Union[date, str], end: Union[date, str]) -> List[Dict]:
        """Get daily load distribution."""
        params = {
            "start": start.isoformat() if isinstance(start, date) else start,
            "end": end.isoformat() if isinstance(end, date) else end
        }
        return self._request("GET", "heatmap", params=params)

    def get_trends(self, weeks: int = 12, start_date: Optional[Union[date, str]] = None) -> Dict:
        """Get multi-week load trend predictions."""
        params = {"weeks": weeks}
        if start_date:
            params["start_date"] = start_date.isoformat() if isinstance(start_date, date) else start_date
        return self._request("GET", "trends", params=params)

    def get_context_distribution(self, start: Union[date, str], end: Union[date, str]) -> Dict:
        """Get load distribution grouped by task context."""
        params = {
            "start": start.isoformat() if isinstance(start, date) else start,
            "end": end.isoformat() if isinstance(end, date) else end
        }
        return self._request("GET", "context-distribution", params=params)

    def calculate_load(self, target_date: Union[date, str]) -> Dict:
        """Get raw load calculation for a specific date."""
        target = target_date.isoformat() if isinstance(target_date, date) else target_date
        return self._request("GET", f"calculate/{target}")

    def force_expand(self, start_date: Union[date, str], end_date: Union[date, str]) -> Dict:
        """Force trigger task expansion for a range."""
        params = {
            "start_date": start_date.isoformat() if isinstance(start_date, date) else start_date,
            "end_date": end_date.isoformat() if isinstance(end_date, date) else end_date
        }
        return self._request("POST", "expand", params=params)

    def create_exception(self, exception_data: Dict) -> Dict:
        """Register a task exception (e.g. absence, priority shift)."""
        return self._request("POST", "exceptions", json=exception_data)

    # --- System ---

    def health_check(self) -> Dict:
        """Check system status (No auth required)."""
        return self._request("GET", "health")
