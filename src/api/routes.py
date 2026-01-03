from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from datetime import date, timedelta, datetime
from typing import List, Optional
import uuid
import csv
import io
import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

from ..models.database import get_db, User, Task, TaskException, LBSDailyCache, TaskStatus
from ..models.user import User as DBUser
from ..services.lbs_engine import LBSEngine
from ..auth import require_local_user, require_user_identity, Identity
from .schemas import (
    TaskCreate, 
    TaskUpdate, 
    TaskResponse, 
    TaskDetail, 
    ExceptionCreate, 
    DashboardResponse,
    TaskBulkDelete,
    TaskBulkStatusUpdate
)

router = APIRouter(tags=["LBS"])

@router.get("/health")
def health_check():
    return {"status": "healthy", "service": "lbs-api"}

@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    start_date: Optional[date] = None,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    if not start_date:
        start_date = date.today() - timedelta(days=date.today().weekday())
    
    engine = LBSEngine(db, identity.user_id)
    
    today = engine.calculate_daily_load(date.today(), include_completed=True) # Always include for today's snapshot
    weekly = engine.get_weekly_stats(start_date, include_completed=True)
    
    daily_breakdown = []
    for i in range(7):
        daily_breakdown.append(engine.calculate_daily_load(start_date + timedelta(days=i), include_completed=True))
        
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
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    logger.info(f"[LBS] Creating task for user {identity.user_id}")
    task_id = f"T-{uuid.uuid4().hex[:8].upper()}"
    try:
        db_task = Task(
            **task_in.dict(),
            task_id=task_id,
            user_id=identity.user_id
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        logger.info(f"[LBS] Task {task_id} created in DB")
        
        # Trigger expansion for range
        engine = LBSEngine(db, identity.user_id)
        expand_start = db_task.start_date or date.today()
        expand_end = db_task.end_date or (date.today() + timedelta(days=90))
        logger.info(f"[LBS] Expanding tasks from {expand_start} to {expand_end}")
        engine.expand_tasks(expand_start, expand_end)
        logger.info(f"[LBS] Expansion complete")
        
        return db_task
    except Exception as e:
        logger.error(f"[LBS] Error creating task: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks", response_model=List[TaskResponse])
def list_tasks(
    context: Optional[str] = None,
    status: Optional[TaskStatus] = None,
    active: bool = Query(True),
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    query = db.query(Task).filter(Task.user_id == identity.user_id)
    if active is not None:
        query = query.filter(Task.active == active)
    if status:
        query = query.filter(Task.status == status)
    if context:
        query = query.filter(Task.context == context)
    return query.all()

@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task_detail(
    task_id: str,
    identity: Identity = Depends(require_user_identity),
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
    identity: Identity = Depends(require_user_identity),
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

@router.post("/tasks/upload-csv")
def upload_tasks_csv(
    file: UploadFile = File(...),
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    contents = file.file.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(contents))
    
    tasks_to_create = []
    engine = LBSEngine(db, identity.user_id)
    
    # We'll use a wide range for expansion if any task is created
    min_start = date.today()
    max_end = date.today() + timedelta(days=90)

    for row in reader:
        try:
            # Basic validation/conversion
            task_id = f"T-{uuid.uuid4().hex[:8].upper()}"
            
            # Helper to parse boolean from CSV
            def to_bool(val):
                if not val: return False
                return str(val).lower() in ('true', '1', 'yes', 'y', 't')

            # Validate rule_type
            rule_type = row.get('rule_type', 'WEEKLY').upper()
            valid_rules = ['WEEKLY', 'ONCE', 'EVERY_N_DAYS', 'MONTHLY_DAY']
            if rule_type not in valid_rules:
                raise HTTPException(status_code=400, detail=f"Invalid rule_type: {rule_type}")

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
                status=TaskStatus(row.get('status', 'todo').lower())
            )
            
            if db_task.start_date and db_task.start_date < min_start: min_start = db_task.start_date
            if db_task.end_date and db_task.end_date > max_end: max_end = db_task.end_date

            tasks_to_create.append(db_task)
        except HTTPException:
            raise
        except Exception as e:
            # Log other parsing errors (like float conversion) and continue
            logger.warning(f"Error parsing row: {e}")
            continue

    if not tasks_to_create and reader.line_num > 1:
        # If we didn't created any tasks but there were rows (line_num > 1 because line 1 is header)
        raise HTTPException(status_code=400, detail="No valid tasks found in CSV")

    if tasks_to_create:
        db.add_all(tasks_to_create)
        db.commit()
        
        # Trigger expansion for all new tasks in the relevant range
        engine.expand_tasks(min_start, max_end)
        
    return {"message": f"Successfully imported {len(tasks_to_create)} tasks"}

@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: str,
    identity: Identity = Depends(require_user_identity),
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

@router.post("/tasks/bulk-delete")
def bulk_delete_tasks(
    bulk_in: TaskBulkDelete,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    # Use optimized single-query delete instead of loop
    count = db.query(Task).filter(
        Task.task_id.in_(bulk_in.task_ids),
        Task.user_id == identity.user_id
    ).delete(synchronize_session='fetch')
    
    if count == 0:
        return {"message": "No tasks found to delete"}
    
    db.commit()
    
    # Trigger expansion for user
    engine = LBSEngine(db, identity.user_id)
    engine.expand_tasks(date.today(), date.today() + timedelta(days=90))
    
    return {"message": f"Successfully deleted {count} tasks"}

@router.post("/tasks/bulk-update-status")
def bulk_update_status(
    bulk_in: TaskBulkStatusUpdate,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    tasks = db.query(Task).filter(
        Task.task_id.in_(bulk_in.task_ids),
        Task.user_id == identity.user_id
    ).all()
    
    if not tasks:
        return {"message": "No tasks found to update"}
    
    count = len(tasks)
    for t in tasks:
        t.active = bulk_in.active
        t.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Trigger expansion for user
    engine = LBSEngine(db, identity.user_id)
    engine.expand_tasks(date.today(), date.today() + timedelta(days=90))
    
    return {"message": f"Successfully updated status for {count} tasks"}

@router.post("/exceptions")
def create_exception(
    exc: ExceptionCreate,
    identity: Identity = Depends(require_user_identity),
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
    include_completed: bool = Query(True),
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    engine = LBSEngine(db, identity.user_id)
    return engine.calculate_daily_load(target_date, include_completed=include_completed)

@router.post("/expand")
def expand_tasks(
    start_date: date,
    end_date: date,
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    engine = LBSEngine(db, identity.user_id)
    engine.expand_tasks(start_date, end_date)
    return {"message": "Expansion complete"}

@router.get("/heatmap")
def get_heatmap(
    start: date,
    end: date,
    include_completed: bool = Query(True),
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    engine = LBSEngine(db, identity.user_id)
    # Ensure range is expanded
    engine.expand_tasks(start, end)
    
    if hasattr(engine, 'get_heatmap_data'):
        return engine.get_heatmap_data(start, end, include_completed=include_completed)
    return get_heatmap_legacy(engine, start, end, include_completed=include_completed)

def get_heatmap_legacy(engine, start, end, include_completed=True):
    data = []
    curr = start
    while curr <= end:
        load = engine.calculate_daily_load(curr, include_completed=include_completed)
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
    engine = LBSEngine(db, identity.user_id)
    return {"trends": engine.get_trend_data(weeks, start_date, include_completed=include_completed)}

@router.get("/context-distribution")
def get_context_distribution(
    start: date,
    end: date,
    include_completed: bool = Query(True),
    identity: Identity = Depends(require_user_identity),
    db: Session = Depends(get_db)
):
    engine = LBSEngine(db, identity.user_id)
    return {"distribution": engine.get_context_distribution(start, end, include_completed=include_completed)}
