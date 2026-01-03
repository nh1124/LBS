import requests
import os
from datetime import date, datetime
import enum
from typing import List, Optional, Dict, Any, Union

class TaskStatus(str, enum.Enum):
    """Possible statuses for an LBS task."""
    TODO = "todo"
    DONE = "done"

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
        token: Optional[str] = None,
        external_jwt: Optional[str] = None
    ):
        """
        Initialize the LBS Client.
        
        :param base_url: The base URL of the LBS service (default: http://localhost:8100/api/lbs)
        :param api_key: X-API-KEY for authentication.
        :param token: JWT Bearer token for authentication.
        :param external_jwt: External system JWT for identity linking (X-EXTERNAL-JWT).
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("LBS_API_KEY")
        self.token = token
        self.external_jwt = external_jwt
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
            
        if self.external_jwt:
            headers["X-EXTERNAL-JWT"] = self.external_jwt
            
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

    # --- Authentication & API Keys ---

    def login(self, username_or_email: str, password: str) -> str:
        """
        Login with username/email and password to obtain a JWT.
        Sets self.token automatically.
        """
        payload = {
            "username_or_email": username_or_email,
            "password": password
        }
        data = self._request("POST", "auth/login", json=payload)
        self.token = data.get("access_token")
        return self.token

    def verify_identity(self) -> Dict:
        """Verify current identity status (/auth/me)"""
        return self._request("GET", "auth/me")

    def get_full_identity_debug(self) -> Dict:
        """Debug endpoint to show resolved identity (local, external, or api_key)."""
        return self._request("GET", "auth/identity")

    def confirm_link_external(self) -> Dict:
        """
        Link a verified External System JWT identity (from X-EXTERNAL-JWT header) 
        to the currently logged-in local LBS account.
        """
        return self._request("POST", "auth/link/confirm")

    def provision_api_key(self, rotate: bool = False, scopes: List[str] = ["read"]) -> Dict:
        """
        Provision an API key for a specific external integration client.
        """
        payload = {"rotate": rotate, "scopes": scopes}
        return self._request("POST", "auth/api-keys/provision", json=payload)

    def create_api_key(self, client_id: str, scopes: List[str] = ["read"], expires_in_days: Optional[int] = None) -> Dict:
        """Create a user-managed API key."""
        payload = {
            "client_id": client_id,
            "scopes": scopes,
            "expires_in_days": expires_in_days
        }
        return self._request("POST", "auth/api-keys", json=payload)

    def list_api_keys(self) -> List[Dict]:
        """List metadata for all API keys belonging to the current user."""
        return self._request("GET", "auth/api-keys")

    def revoke_api_key(self, key_id: str) -> Dict:
        """Revoke an API key."""
        return self._request("DELETE", f"auth/api-keys/{key_id}")

    # --- User Management ---

    def create_user(self, email: str, name: Optional[str] = None, password: Optional[str] = None) -> Dict:
        """Create a new local user account."""
        payload = {
            "email": email,
            "name": name,
            "password": password
        }
        return self._request("POST", "users/", json=payload)

    def get_user_me(self) -> Dict:
        """Get full profile details for current user."""
        return self._request("GET", "users/me")

    # --- Task Operations ---

    def list_tasks(self, context: Optional[str] = None, status: Optional[Union[str, TaskStatus]] = None, active: Optional[bool] = None) -> List[Dict]:
        """
        List tasks, optionally filtered by context, status, and active flag.
        
        :param context: Filter by task context string.
        :param status: Filter by task status (e.g., 'todo', 'done' or TaskStatus enum).
        :param active: Filter by active status (True/False).
        """
        params = {}
        if context:
            params["context"] = context
        if status:
            params["status"] = status.value if isinstance(status, TaskStatus) else status
        if active is not None:
            params["active"] = str(active).lower()
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

    def update_task_progress(self, task_id: str, status: Union[str, TaskStatus]) -> Dict:
        """Update the progress status of a task (e.g., 'todo', 'done')."""
        status_val = status.value if isinstance(status, TaskStatus) else status
        return self.update_task(task_id, {"status": status_val})

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

    def get_heatmap(self, start: Union[date, str], end: Union[date, str], include_completed: bool = True) -> List[Dict]:
        """Get daily load distribution."""
        params = {
            "start": start.isoformat() if isinstance(start, date) else start,
            "end": end.isoformat() if isinstance(end, date) else end,
            "include_completed": str(include_completed).lower()
        }
        return self._request("GET", "heatmap", params=params)

    def get_trends(self, weeks: int = 12, start_date: Optional[Union[date, str]] = None, include_completed: bool = True) -> Dict:
        """Get multi-week load trend predictions."""
        params = {"weeks": weeks, "include_completed": str(include_completed).lower()}
        if start_date:
            params["start_date"] = start_date.isoformat() if isinstance(start_date, date) else start_date
        return self._request("GET", "trends", params=params)

    def get_context_distribution(self, start: Union[date, str], end: Union[date, str], include_completed: bool = True) -> Dict:
        """Get load distribution grouped by task context."""
        params = {
            "start": start.isoformat() if isinstance(start, date) else start,
            "end": end.isoformat() if isinstance(end, date) else end,
            "include_completed": str(include_completed).lower()
        }
        return self._request("GET", "context-distribution", params=params)

    def calculate_load(self, target_date: Union[date, str], include_completed: bool = True) -> Dict:
        """Get raw load calculation for a specific date."""
        target = target_date.isoformat() if isinstance(target_date, date) else target_date
        params = {"include_completed": str(include_completed).lower()}
        return self._request("GET", f"calculate/{target}", params=params)

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
