# LBS (Load Balancing System)

LBS is a comprehensive Load Balancing System that manages and schedules tasks. It includes a FastAPI backend and a modern React-based UI for maintenance and monitoring.

## Features

-   **Load Balancing Engine**: Core logic for task distribution and scaling.
-   **CSV Task Import**: Support for bulk task registration from CSV files.
-   **Integrated Registration UI**: Easy user onboarding directly through the browser.
-   **Maintenance UI**: User-friendly glassmorphism interface for monitoring and management.
-   **API**: RESTful API built with FastAPI for system interaction.
-   **Database**: PostgreSQL for robust data persistence.

## Tech Stack

### Backend
-   **Language**: Python 3.x
-   **Framework**: FastAPI
-   **ORM**: SQLAlchemy
-   **Database**: PostgreSQL

### Frontend
-   **Framework**: React (Vite)
-   **Styling**: Vanilla CSS / Design Tokens

### Infrastructure
-   **Docker**: Containerization for consistent environments.
-   **Docker Compose**: Orchestration for multi-container setup.

## Getting Started

### Prerequisites

-   [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) installed on your machine.

### Installation & Running

1.  Clone the repository:
    ```bash
    git clone https://github.com/nh1124/LBS.git
    cd LBS
    ```

2.  Start the application using Docker Compose:
    ```bash
    docker-compose up --build
    ```

    This command will build the backend and frontend images and start the services, including the PostgreSQL database.

3.  Access the services:
    -   **LBS UI & API**: Open [http://localhost:8100](http://localhost:8100) in your browser.
    -   **API Documentation**: Open [http://localhost:8100/docs](http://localhost:8100/docs) for the interactive Swagger UI.

## Project Structure

-   `src/`: Backend source code (API, Services, Models).
-   `ui/`: Frontend source code (React App).
-   `tasks_template.csv`: Template for bulk task import.
-   `docker-compose.yml`: Service definitions.

## Authentication & Security

LBS uses an API Key-centric authentication system.

### Auth Methods (Priority Order)
1. **X-API-KEY Header**: Primary method. Resolves user identity, client ID, and scopes.
2. **JWT Bearer Token**: Secondary method for browser/UI sessions.
3. **Dev Fallback**: Used only if `LBS_REQUIRE_API_KEY=false`. Uses `LBS_DEFAULT_USER_ID`.

### User Setup
The easiest way to get started is via the **Integrated Registration UI**:
1. Open the UI at [http://localhost:8100](http://localhost:8100).
2. Click **"Create Account"** in the authentication modal.
3. Fill in your details to instantly generate your personal API Key.

### Usage Examples (Curl)
```bash
# Using API Key
curl -H "X-API-KEY: your-secret-key" http://localhost:8100/api/lbs/tasks

# Using JWT
curl -H "Authorization: Bearer <token>" http://localhost:8100/api/lbs/tasks
```

### Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `LBS_ENV` | `dev` | `dev` or `prod`. `prod` enforces strict security. |
| `LBS_REQUIRE_API_KEY` | `false` | If `true`, requires API key or JWT. If `false`, falls back to default user. |
| `LBS_DEFAULT_USER_ID` | `0000...` | UUID used for dev fallback. |
| `LBS_BIND_HOST` | `127.0.0.1` | Host to bind uvicorn. |
| `BACKEND_PORT` | `8100` | Port for the backend service. |

## Development

To run the backend locally (without Docker):
1.  Create a virtual environment: `python -m venv venv`
2.  Activate it: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
3.  Install dependencies: `pip install -r requirements.txt`
4.  Run the server: `uvicorn src.main:app --reload`
