import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.orm import Session
from pydantic import BaseModel
import hashlib
import hmac
import secrets

from .models.database import get_db, User
from .config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
logger = logging.getLogger("lbs.auth")

class Identity(BaseModel):
    user_id: str
    client_id: Optional[str] = None
    scopes: List[str] = []
    auth_method: str # api_key, jwt, dev_fallback
    warnings: List[str] = []

def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256."""
    return hashlib.sha256(api_key.encode()).hexdigest()

def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify a plain API key against a hashed key using constant-time comparison."""
    return hmac.compare_digest(hash_api_key(plain_key), hashed_key)

async def resolve_identity(
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None, alias="X-API-KEY"),
    token: Optional[str] = Depends(oauth2_scheme)
) -> Identity:
    warnings = []
    
    # 1. Primary Auth: API Key
    if x_api_key:
        from .models.user import APIKey
        key_hash = hash_api_key(x_api_key)
        api_key_record = db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        ).first()
        
        if api_key_record:
            logger.debug(f"Authenticated with API Key for user {api_key_record.user_id}")
            return Identity(
                user_id=api_key_record.user_id,
                client_id=api_key_record.client_id,
                scopes=api_key_record.scopes or [],
                auth_method="api_key",
                warnings=warnings
            )
        else:
            logger.warning(f"Invalid API Key attempt: {x_api_key[:8]}...")

    # 2. Secondary Auth: JWT
    if token:
        try:
            payload = jwt.decode(token, settings.LBS_SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id:
                logger.debug(f"Authenticated with JWT for user {user_id}")
                return Identity(
                    user_id=user_id,
                    auth_method="jwt",
                    warnings=warnings
                )
        except JWTError:
            pass # Fall through to error or dev fallback

        except JWTError:
            pass # Fall through to error or dev fallback

    # 3. Dev Fallback
    if not settings.LBS_REQUIRE_API_KEY:
        logger.warning(f"DEV FALLBACK USED: Using default user_id {settings.LBS_DEFAULT_USER_ID}")
        warnings.append("api_key_missing_dev_fallback_used")
        return Identity(
            user_id=settings.LBS_DEFAULT_USER_ID,
            auth_method="dev_fallback",
            warnings=warnings
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: valid X-API-KEY or Bearer token needed",
        headers={"WWW-Authenticate": "Bearer"},
    )

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.LBS_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(
    db: Session = Depends(get_db),
    identity: Identity = Depends(resolve_identity)
):
    """Backward compatibility layer for existing get_current_user usage."""
    user = db.query(User).filter(User.user_id == identity.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user
