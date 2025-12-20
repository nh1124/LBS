from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from ..models.database import get_db, User
from ..models.user import APIKey
from .schemas import UserCreate, UserResponse
from ..auth import resolve_identity, Identity, hash_api_key

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", response_model=UserResponse)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    plain_key = f"LBS-{uuid.uuid4().hex[:12].upper()}"
    new_user = User(
        email=user_in.email,
        name=user_in.name,
        api_key=plain_key # Legacy column for simple lookups if needed
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create the secure APIKey record
    api_key_record = APIKey(
        key_hash=hash_api_key(plain_key),
        user_id=new_user.user_id,
        is_active=True,
        name="Default Key"
    )
    db.add(api_key_record)
    db.commit()
    
    # Return user with plain_key so user can see it once
    return new_user

@router.get("/me")
def get_user_me(
    db: Session = Depends(get_db),
    identity: Identity = Depends(resolve_identity)
):
    user = db.query(User).filter(User.user_id == identity.user_id).first()
    if not user:
        # If identity resolved but user not in DB (e.g. dev fallback with non-existent UUID)
        return {
            "user_id": identity.user_id,
            "client_id": identity.client_id,
            "auth_method": identity.auth_method,
            "warnings": identity.warnings,
            "error": "User record not found"
        }
    
    return {
        "user_id": user.user_id,
        "email": user.email,
        "name": user.name,
        "client_id": identity.client_id,
        "auth_method": identity.auth_method,
        "warnings": identity.warnings
    }
