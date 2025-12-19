from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from ..models.database import get_db, User
from .schemas import UserCreate, UserResponse
from ..auth import resolve_identity, Identity

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", response_model=UserResponse)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email=user_in.email,
        name=user_in.name,
        api_key=f"LBS-{uuid.uuid4().hex[:12].upper()}"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
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
