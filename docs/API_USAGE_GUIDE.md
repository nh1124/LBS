# LBS API Usage Guide

This guide explains how to access the LBS (Load Balancing System) API from external tools and AI agents.

## Base URL

By default, the API is accessible at:
`http://localhost:8100/api/lbs`

---

## Authentication Methods

The LBS system supports three primary ways to authenticate.

### 1. User ID + Password (Login Flow)

This method is primarily used by human users or tools acting on behalf of a user to obtain a temporary session token (JWT).

- **Endpoint**: `POST /auth/login`
- **Request Body**:
  ```json
  {
    "username_or_email": "your_username_or_email",
    "password": "your_password"
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "eyJhbG..."
  }
  ```

### 2. External System Token (JWT Integration)

This method is used when LBS is integrated with a host client system. The host system issues its own JWT, which LBS validates and maps to a specific User ID.

- **Flow**:
  1. The host client system generates its own JWT.
  2. The host system provides this JWT in the `Authorization: Bearer <token>` header.
  3. LBS decodes the token, verifies the issuer (`iss`), and maps the subject (`sub`) to an internal LBS `user_id` based on registered **External Identities**.
- **Header**: `Authorization: Bearer <host_system_jwt>`
- **Requirement**: The external identity must be linked to an LBS user (see Linking Flow) for the mapping to work.

- **Example `curl`**:
  ```bash
  curl -X GET "http://localhost:8100/api/lbs/dashboard" \
       -H "Authorization: Bearer <external_jwt>"
  ```

### 3. X-API-KEY (Machine-to-Machine)

This is the **recommended method for AI agents** and external automation. It uses a long-lived API key that does not expire frequently.

- **Header**: `X-API-KEY: <your_api_key>`
- **Example `curl`**:
  ```bash
  curl -X GET "http://localhost:8100/api/lbs/health" \
       -H "X-API-KEY: your_secret_api_key_here"
  ```

#### How to generate an API Key:
1. Log in to the LBS UI or use the Login Flow above.
2. Call `POST /auth/api-keys` with a Bearer Token:
   ```json
   {
     "client_id": "my-ai-agent",
     "scopes": ["read", "write"],
     "expires_in_days": 30
   }
   ```
3. The response will contain the plaintext `api_key`. **Store it securely**, as it cannot be retrieved again.

---

## Integration Guide for AI Agents

AI agents should prefer the `X-API-KEY` method for its simplicity and persistence.

### Configuration for Agents

When configuring an AI agent (like AutoGPT, BabyAGI, or a custom LangChain agent), provide the following:

- **Environment Variable**: `LBS_API_KEY`
- **Base URL**: `http://localhost:8100/api/lbs`
- **Common Header**: `{"X-API-KEY": os.environ["LBS_API_KEY"]}`

### Example Python Integration

```python
import requests
import os

BASE_URL = "http://localhost:8100/api/lbs"
API_KEY = os.getenv("LBS_API_KEY")

headers = {
    "X-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

def get_dashboard_summary():
    response = requests.get(f"{BASE_URL}/dashboard", headers=headers)
    response.raise_for_status()
    return response.json()

def create_lbs_task(title, load, due_date):
    payload = {
        "title": title,
        "load": load,
        "due_date": due_date,
        "context": "automation"
    }
    response = requests.post(f"{BASE_URL}/tasks", headers=headers, json=payload)
    return response.json()
```

---

## Important Endpoints

All endpoints are prefixed with `/api/lbs`.

### Authentication & API Keys (`/auth`)
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/auth/login` | POST | Login with username/password to get JWT |
| `/auth/me` | GET | Verify current identity status |
| `/auth/api-keys` | GET | List your active API keys |
| `/auth/api-keys` | POST | Create a new API key |
| `/auth/api-keys/{id}` | DELETE | Revoke an API key |
| `/auth/link/confirm` | POST | Link an external identity (e.g. from host system) |
| `/auth/identity` | GET | [Dev Only] Detailed identity debug info |

### User Management (`/users`)
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/users/` | POST | Create a new local user account |
| `/users/me` | GET | Get full profile details for current user |

### Task Operations (`/tasks`)
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/tasks` | GET | List your tasks (supports `context` filter) |
| `/tasks` | POST | Create a single LBS task |
| `/tasks/{id}` | GET | Get detailed task information |
| `/tasks/{id}` | PUT | Update an existing task |
| `/tasks/{id}` | DELETE | Delete a task |
| `/tasks/bulk-delete` | POST | Delete multiple tasks by ID list |
| `/tasks/upload` | POST | Bulk import tasks via CSV file |

### Load Analysis & Insights
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/dashboard` | GET | Summary of current load and next-day predictions |
| `/heatmap` | GET | Daily load distribution for a specific date range |
| `/trends` | GET | Multi-week load trend predictions (up to 12 weeks) |
| `/distribution/context` | GET | Load distribution grouped by task context |
| `/load` | GET | Get raw load calculation for a specific date |
| `/expand` | GET | Force trigger task expansion for a range |
| `/exceptions` | POST | Register a task exception (e.g. absence, priority shift) |

### System
| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/health` | GET | Check system status (No auth required) |
| `/` | GET | Root info and link to `/docs` |
| `/docs` | GET | Interactive Swagger API documentation |

---

## Troubleshooting

- **401 Unauthorized**: Ensure your `X-API-KEY` or `Authorization` header is correct and not expired.
- **403 Forbidden**: Your API key might not have the required `scopes` for the operation.
- **Connection Refused**: Ensure the LBS backend is running on the expected port (default 8100).
