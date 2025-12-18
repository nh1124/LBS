import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "LBS Microservice"
    API_V1_STR: str = "/api/lbs"
    SECRET_KEY: str = os.getenv("LBS_SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Database
    # Use environment variable DATABASE_URL for PostgreSQL in Docker
    DATABASE_URL: str = "sqlite:///./lbs.db"
    
    # LBS Defaults
    DEFAULT_ALPHA: float = 0.1
    DEFAULT_BETA: float = 1.2
    DEFAULT_CAP: float = 8.0
    DEFAULT_SWITCH_COST: float = 0.5

    class Config:
        case_sensitive = True

settings = Settings()
