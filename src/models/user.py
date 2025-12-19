from sqlalchemy import Column, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True) # For future use
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    api_key = Column(String, unique=True, index=True, nullable=True)
    
    keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key_hash = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    client_id = Column(String, nullable=True)
    scopes = Column(JSON, default=list) # List of strings
    is_active = Column(Boolean, default=True)
    name = Column(String, nullable=True) # Human label
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="keys")
