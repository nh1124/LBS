from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta, datetime
from typing import List, Optional
import uuid

from ..models.database import get_db, Task, TaskException, User
from ..models.user import User as DBUser
from ..services.lbs_engine import LBSEngine
from ..auth import resolve_identity, Identity
from .schemas import TaskCreate, TaskUpdate, TaskResponse, TaskDetail, ExceptionCreate, DashboardResponse

router = APIRouter(tags=["LBS"])

@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    start_date: Optional[date] = None,
    identity: Identity = Depends(resolve_identity),
    db: Session = Depends(get_db)
):
    if not start_date:
        start_date = date.today() - timedelta(days=date.today().weekday())
    
    engine = LBSEngine(db, identity.user_id)
    
    today = engine.calculate_daily_load(date.today())
    weekly = engine.get_weekly_stats(start_date)
    
    daily_breakdown = []
    for i in range(7):
        daily_breakdown.append(engine.calculate_daily_load(start_date + timedelta(days=i)))
        
    return {
        "today": today,
        "weekly": weekly,
        "daily_breakdown": daily_breakdown,
        "config": engine.config,
        "warnings": identity.warnings
    }

@router.post("/tasks", response_model=TaskResponse)
def create_task(
    task_in: TaskCreate,
    identity: Identity = Depends(resolve_identity),
    db: Session = Depends(get_db)
):
    task_id = f"T-{uuid.uuid4().hex[:8].upper()}"
    db_task = Task(
        **task_in.dict(),
        task_id=task_id,
        user_id=identity.user_id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Trigger expansion for range
    engine = LBSEngine(db, identity.user_id)
    expand_start = db_task.start_date or date.today()
    expand_end = db_task.end_date or (date.today() + timedelta(days=90))
    engine.expand_tasks(expand_start, expand_end)
    
    return db_task

@router.get("/tasks", response_model=List[TaskResponse])
def list_tasks(
    context: Optional[str] = None,
    identity: Identity = Depends(resolve_identity),
    db: Session = Depends(get_db)
):
    query = db.query(Task).filter(Task.user_id == identity.user_id)
    if context:
        query = query.filter(Task.context == context)
    return query.all()

@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task_detail(
    task_id: str,
    identity: Identity = Depends(resolve_identity),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.task_id == task_id, Task.user_id == identity.user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    task_in: TaskUpdate,
    identity: Identity = Depends(resolve_identity),
    db: Session = Depends(get_db)
):
    db_task = db.query(Task).filter(Task.task_id == task_id, Task.user_id == identity.user_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_task, field, value)
    
    db_task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_task)
    
    # Trigger re-expansion
    engine = LBSEngine(db, identity.user_id)
    expand_start = db_task.start_date or date.today()
    expand_end = db_task.end_date or (date.today() + timedelta(days=90))
    engine.expand_tasks(expand_start, expand_end)
    
    return db_task

@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: str,
    identity: Identity = Depends(resolve_identity),
    db: Session = Depends(get_db)
):
    db_task = db.query(Task).filter(Task.task_id == task_id, Task.user_id == identity.user_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(db_task)
    db.commit()
    
    # Expansion trigger might be needed but optional here if cache is cleared by end of day or range
    # Best to re-expand to clear cache
    engine = LBSEngine(db, identity.user_id)
    engine.expand_tasks(date.today(), date.today() + timedelta(days=90))
    
    return {"message": "Task deleted successfully"}

@router.post("/exceptions")
def create_exception(
    exc: ExceptionCreate,
    identity: Identity = Depends(resolve_identity),
    db: Session = Depends(get_db)
):
    # Verify task ownership
    task = db.query(Task).filter(Task.task_id == exc.task_id, Task.user_id == identity.user_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    new_exc = TaskException(
        **exc.dict(),
        user_id=identity.user_id
    )
    db.add(new_exc)
    db.commit()
    
    # Re-expand affected date
    engine = LBSEngine(db, identity.user_id)
    engine.expand_tasks(exc.target_date, exc.target_date)
    
    return {"message": "Exception created successfully"}

@router.get("/calculate/{target_date}")
def calculate_load(
    target_date: date,
    identity: Identity = Depends(resolve_identity),
    db: Session = Depends(get_db)
):
    engine = LBSEngine(db, identity.user_id)
    return engine.calculate_daily_load(target_date)

@router.post("/expand")
def expand_tasks(
    start_date: date,
    end_date: date,
    identity: Identity = Depends(resolve_identity),
    db: Session = Depends(get_db)
):
    engine = LBSEngine(db, identity.user_id)
    engine.expand_tasks(start_date, end_date)
    return {"message": "Expansion complete"}

@router.get("/heatmap")
def get_heatmap(
    start: date,
    end: date,
    identity: Identity = Depends(resolve_identity),
    db: Session = Depends(get_db)
):
    engine = LBSEngine(db, identity.user_id)
    return {"days": engine.get_heatmap_data(start, end) if hasattr(engine, 'get_heatmap_data') else get_heatmap_legacy(engine, start, end)}

def get_heatmap_legacy(engine, start, end):
    data = []
    curr = start
    while curr <= end:
        load = engine.calculate_daily_load(curr)
        data.append({
            "date": str(curr),
            "load": load["adjusted_load"],
            "level": load["level"]
        })
        curr += timedelta(days=1)
    return data

@router.get("/trends")
def get_trends(
    weeks: int = 12,
    identity: Identity = Depends(resolve_identity),
    db: Session = Depends(get_db)
):
    engine = LBSEngine(db, identity.user_id)
    return {"trends": engine.get_trend_data(weeks)}

@router.get("/context-distribution")
def get_context_distribution(
    start: date,
    end: date,
    identity: Identity = Depends(resolve_identity),
    db: Session = Depends(get_db)
):
    engine = LBSEngine(db, identity.user_id)
    return {"distribution": engine.get_context_distribution(start, end)}
