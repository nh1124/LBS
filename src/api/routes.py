from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from datetime import date, timedelta, datetime
from typing import List, Optional
import uuid
import csv
import io
import logging

logger = logging.getLogger(__name__)

from ..models.database import get_db, Task, TaskException, TaskStatus, TaskExecution
from ..services.manager import LBSManager
from ..auth import require_user_identity, Identity
from .schemas import (
    TaskCreate, 
    TaskUpdate, 
    TaskResponse, 
    DashboardResponse,
    TaskBulkDelete,
    TaskBulkActiveUpdate,
    TaskExecutionRequest,
    TaskExecutionResponse,
    DailySchedule,
    ExceptionCreate
)

router = APIRouter(tags=["LBS"])

@router.get("/health")
def health_check():
    return {"status": "healthy", "service": "lbs-api"}

@router.get("/schedule", response_model=List[DailySchedule])
def get_schedule(
    start_date: date,
    end_date: date,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    """Unified schedule API via Manager"""
    manager = LBSManager(db, identity.user_id)
    return manager.get_schedule(start_date, end_date)

@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    start_date: Optional[date] = None,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    if not start_date:
        start_date = date.today() - timedelta(days=date.today().weekday())
    
    manager = LBSManager(db, identity.user_id)
    dash = manager.get_dashboard(start_date)
    return {
        **dash,
        "warnings": identity.warnings
    }

@router.post("/tasks", response_model=TaskResponse)
def create_task(
    task_in: TaskCreate,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    manager = LBSManager(db, identity.user_id)
    task_id = f"T-{uuid.uuid4().hex[:8].upper()}"
    try:
        db_task = Task(
            **task_in.dict(exclude={'status'}),
            task_id=task_id,
            user_id=identity.user_id
        )
        manager.repo.create_task(db_task)
        db.commit()
        db.refresh(db_task)
        
        # Trigger refresh
        expand_start = db_task.start_date or date.today()
        expand_end = db_task.end_date or (date.today() + timedelta(days=90))
        manager.refresh_schedule(expand_start, expand_end)
        
        return db_task
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks", response_model=List[TaskResponse])
def list_tasks(
    context: Optional[str] = None,
    active: Optional[bool] = Query(None),
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    manager = LBSManager(db, identity.user_id)
    # Using repo directly for simple list
    query = db.query(Task).filter(Task.user_id == identity.user_id)
    if active is not None:
        query = query.filter(Task.active == active)
    if context:
        query = query.filter(Task.context == context)
    return query.all()

@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task_detail(
    task_id: str,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    manager = LBSManager(db, identity.user_id)
    task = manager.repo.get_task(identity.user_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/tasks/{task_id}/history", response_model=List[TaskExecutionResponse])
def get_task_history(
    task_id: str,
    start_date: date,
    end_date: date,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    manager = LBSManager(db, identity.user_id)
    task = manager.repo.get_task(identity.user_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    executions = db.query(TaskExecution).filter(
        TaskExecution.task_id == task_id,
        TaskExecution.target_date >= start_date,
        TaskExecution.target_date <= end_date
    ).order_by(TaskExecution.target_date.asc()).all()
    
    return executions

@router.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    task_in: TaskUpdate,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    manager = LBSManager(db, identity.user_id)
    db_task = manager.repo.get_task(identity.user_id, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_task, field, value)
    
    db_task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_task)
    
    expand_start = db_task.start_date or date.today()
    expand_end = db_task.end_date or (date.today() + timedelta(days=90))
    manager.refresh_schedule(expand_start, expand_end)
    
    return db_task

@router.post("/tasks/upload-csv")
def upload_tasks_csv(
    file: UploadFile = File(...),
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    manager = LBSManager(db, identity.user_id)
    contents = file.file.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(contents))
    
    tasks_to_create = []
    min_start = date.today()
    max_end = date.today() + timedelta(days=90)

    for row in reader:
        try:
            task_id = f"T-{uuid.uuid4().hex[:8].upper()}"
            def to_bool(val):
                if not val: return False
                return str(val).lower() in ('true', '1', 'yes', 'y', 't')

            rule_type = row.get('rule_type', 'WEEKLY').upper()
            db_task = Task(
                task_id=task_id,
                user_id=identity.user_id,
                task_name=row.get('task_name', 'Untitled Task'),
                context=row.get('context', 'work').lower(),
                base_load_score=float(row.get('base_load_score', 2.0)),
                active=to_bool(row.get('active', 'true')),
                rule_type=rule_type,
                due_date=date.fromisoformat(row['due_date']) if row.get('due_date') and row['due_date'].strip() else None,
                mon=to_bool(row.get('mon', 'false')),
                tue=to_bool(row.get('tue', 'false')),
                wed=to_bool(row.get('wed', 'false')),
                thu=to_bool(row.get('thu', 'false')),
                fri=to_bool(row.get('fri', 'false')),
                sat=to_bool(row.get('sat', 'false')),
                sun=to_bool(row.get('sun', 'false')),
                interval_days=int(row['interval_days']) if row.get('interval_days') and row['interval_days'].strip() else None,
                anchor_date=date.fromisoformat(row['anchor_date']) if row.get('anchor_date') and row['anchor_date'].strip() else None,
                month_day=int(row['month_day']) if row.get('month_day') and row['month_day'].strip() else None,
                nth_in_month=int(row['nth_in_month']) if row.get('nth_in_month') and row['nth_in_month'].strip() else None,
                weekday_mon1=int(row['weekday_mon1']) if row.get('weekday_mon1') and row['weekday_mon1'].strip() else None,
                start_date=date.fromisoformat(row['start_date']) if row.get('start_date') and row['start_date'].strip() else None,
                end_date=date.fromisoformat(row['end_date']) if row.get('end_date') and row['end_date'].strip() else None,
                notes=row.get('notes'),
                external_sync_id=row.get('external_sync_id')
            )
            if db_task.start_date and db_task.start_date < min_start: min_start = db_task.start_date
            if db_task.end_date and db_task.end_date > max_end: max_end = db_task.end_date
            tasks_to_create.append(db_task)
        except Exception as e:
            logger.warning(f"Error parsing row: {e}")
            continue

    if tasks_to_create:
        db.add_all(tasks_to_create)
        db.commit()
        manager.refresh_schedule(min_start, max_end)
        
    return {"message": f"Successfully imported {len(tasks_to_create)} tasks"}

@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: str,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    manager = LBSManager(db, identity.user_id)
    db_task = manager.repo.get_task(identity.user_id, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    manager.repo.delete_task(db_task)
    db.commit()
    manager.refresh_schedule(date.today(), date.today() + timedelta(days=90))
    return {"message": "Task deleted successfully"}

@router.post("/tasks/bulk-delete")
def bulk_delete_tasks(
    bulk_in: TaskBulkDelete,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    manager = LBSManager(db, identity.user_id)
    count = db.query(Task).filter(
        Task.task_id.in_(bulk_in.task_ids),
        Task.user_id == identity.user_id
    ).delete(synchronize_session='fetch')
    
    if count == 0:
        return {"message": "No tasks found to delete"}
    
    db.commit()
    manager.refresh_schedule(date.today(), date.today() + timedelta(days=90))
    return {"message": f"Successfully deleted {count} tasks"}

@router.post("/tasks/bulk-update-active")
def bulk_update_active(
    bulk_in: TaskBulkActiveUpdate,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    manager = LBSManager(db, identity.user_id)
    tasks = db.query(Task).filter(
        Task.task_id.in_(bulk_in.task_ids),
        Task.user_id == identity.user_id
    ).all()
    
    if not tasks:
        return {"message": "No tasks found to update"}
    
    for t in tasks:
        t.active = bulk_in.active
        t.updated_at = datetime.utcnow()
    
    db.commit()
    manager.refresh_schedule(date.today(), date.today() + timedelta(days=90))
    return {"message": f"Successfully updated active status for {len(tasks)} tasks"}

@router.post("/tasks/{task_id}/complete")
def handle_task_completion(
    task_id: str,
    req: TaskExecutionRequest,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    manager = LBSManager(db, identity.user_id)
    task = manager.repo.get_task(identity.user_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return manager.update_task_execution(task_id, req.target_date, req.status)

@router.post("/exceptions")
def create_exception(
    exc: ExceptionCreate,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    manager = LBSManager(db, identity.user_id)
    task = manager.repo.get_task(identity.user_id, exc.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    new_exc = TaskException(
        **exc.dict(),
        user_id=identity.user_id
    )
    manager.repo.create_exception(new_exc)
    db.commit()
    manager.refresh_schedule(exc.target_date, exc.target_date)
    return {"message": "Exception created successfully"}

@router.get("/calculate/{target_date}")
def calculate_load(
    target_date: date,
    include_completed: bool = Query(True),
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    manager = LBSManager(db, identity.user_id)
    # Ensure cache is fresh for the day
    manager.refresh_schedule(target_date, target_date)
    cache_entries = manager.repo.get_daily_cache_in_range(identity.user_id, target_date, target_date)
    tasks = manager.repo.get_active_tasks(identity.user_id)
    return manager.engine.calculate_daily_load(target_date, cache_entries, tasks, include_completed=include_completed)

@router.post("/expand")
def expand_tasks(
    start_date: date,
    end_date: date,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    manager = LBSManager(db, identity.user_id)
    manager.refresh_schedule(start_date, end_date)
    return {"message": "Expansion complete"}

@router.get("/heatmap")
def get_heatmap(
    start: date,
    end: date,
    include_completed: bool = Query(True),
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    manager = LBSManager(db, identity.user_id)
    manager.refresh_schedule(start, end)
    
    cache_entries = manager.repo.get_daily_cache_in_range(identity.user_id, start, end)
    tasks = manager.repo.get_active_tasks(identity.user_id)
    
    data = []
    curr = start
    while curr <= end:
        load = manager.engine.calculate_daily_load(curr, cache_entries, tasks, include_completed=include_completed)
        data.append({
            "date": str(curr),
            "adjusted_load": load["adjusted_load"],
            "level": load["level"],
            "task_count": load["task_count"]
        })
        curr += timedelta(days=1)
    return data

@router.get("/trends")
def get_trends(
    weeks: int = 12,
    start_date: Optional[date] = None,
    include_completed: bool = Query(True),
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    manager = LBSManager(db, identity.user_id)
    return {"trends": manager.get_trends(weeks, start_date, include_completed=include_completed)}

@router.get("/context-distribution")
def get_context_distribution(
    start: date,
    end: date,
    include_completed: bool = Query(True),
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    manager = LBSManager(db, identity.user_id)
    return {"distribution": manager.get_context_distribution(start, end, include_completed=include_completed)}
