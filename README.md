# LBS (Load Balancing System)

LBS is a comprehensive Load Balancing System that manages and schedules tasks. It includes a FastAPI backend and a modern React-based UI for maintenance and monitoring.

## Features

-   **Load Balancing Engine**: Core logic for task distribution and scaling.
-   **Maintenance UI**: A user-friendly interface to monitor system status and manage configurations.
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
    -   **Frontend UI**: Open [http://localhost:3000](http://localhost:3000) in your browser.
    -   **Backend API Docs**: Open [http://localhost:8001/docs](http://localhost:8001/docs) for the interactive Swagger UI.

## Project Structure

-   `src/`: Backend source code (API, Services, Models).
-   `ui/`: Frontend source code (React App).
-   `data/`: Data storage/persistence.
-   `docker-compose.yml`: Service definitions.

## Development

To run the backend locally (without Docker):
1.  Create a virtual environment: `python -m venv venv`
2.  Activate it: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
3.  Install dependencies: `pip install -r requirements.txt`
4.  Run the server: `uvicorn src.main:app --reload`
