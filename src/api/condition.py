from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
import logging

from ..models.database import get_db, DailyCondition
from ..services.manager import LBSManager
from ..auth import require_user_identity, Identity
from .schemas import ConditionUpdate, ConditionResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Condition"])

@router.post("/condition", response_model=ConditionResponse)
def update_condition(
    cond_in: ConditionUpdate,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    """
    Update user's daily condition (fatigue levels).
    VisionArk calls this to inject fatigue analysis results.
    """
    manager = LBSManager(db, identity.user_id)
    
    db_cond = DailyCondition(
        user_id=identity.user_id,
        target_date=cond_in.target_date,
        cognitive_fatigue=cond_in.cognitive_fatigue,
        physical_fatigue=cond_in.physical_fatigue or 0,
        note=cond_in.note
    )
    
    try:
        manager.repo.upsert_condition(db_cond)
        db.commit()
        db.refresh(db_cond)
        
        # Trigger cache refresh for the target date to apply adjustments
        manager.refresh_schedule(cond_in.target_date, cond_in.target_date, force=True)
        
        return db_cond
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating condition: {e}")
        raise HTTPException(status_code=500, detail="Failed to update condition")

@router.get("/condition/{target_date}", response_model=ConditionResponse)
def get_condition(
    target_date: date,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    manager = LBSManager(db, identity.user_id)
    cond = manager.repo.get_condition(identity.user_id, target_date)
    if not cond:
        # Return default condition if not set
        return ConditionResponse(
            user_id=identity.user_id,
            target_date=target_date,
            cognitive_fatigue=0,
            physical_fatigue=0,
            note=None,
            updated_at=date.today() # Placeholder
        )
    return cond
