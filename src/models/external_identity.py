from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from .user import Base

class ExternalIdentity(Base):
    __tablename__ = "external_identities"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    issuer = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint('issuer', 'subject', name='_issuer_subject_uc'),
        Index('idx_issuer_subject', 'issuer', 'subject'),
    )
