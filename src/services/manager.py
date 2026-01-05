from datetime import date, timedelta, datetime
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from .repository import TaskRepository
from .lbs_engine import LBSEngine
from ..models.database import Task, TaskExecution, TaskStatus

class LBSManager:
    def __init__(self, session: Session, user_id: str):
        self.session = session
        self.user_id = user_id
        self.repo = TaskRepository(session)
        config = self.repo.get_system_config(user_id)
        self.engine = LBSEngine(config)

    def refresh_schedule(self, start_date: date, end_date: date, force: bool = False):
        """Refresh the daily cache for the given range, with debouncing"""
        if not force:
            # Check if we have recent cache entries to avoid redundant refreshes in high-concurrency reloads
            recent_entries = self.repo.get_daily_cache_in_range(self.user_id, start_date, end_date)
            if recent_entries:
                latest_gen = max(e.generated_at for e in recent_entries)
                # If cache was generated in the last 30 seconds, skip the refresh
                if datetime.utcnow() - latest_gen < timedelta(seconds=30):
                    return
        tasks = self.repo.get_active_tasks(self.user_id)
        executions = self.repo.get_executions_in_range(self.user_id, start_date, end_date)
        exceptions = self.repo.get_exceptions_in_range(self.user_id, start_date, end_date)
        
        cache_entries = self.engine.calculate_schedule(
            self.user_id, start_date, end_date, tasks, executions, exceptions
        )
        
        from sqlalchemy.exc import IntegrityError
        try:
            self.repo.update_daily_cache(self.user_id, start_date, end_date, cache_entries)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            # If another thread already inserted the cache, we can just continue
            pass

    def get_schedule(self, start_date: date, end_date: date) -> List[Dict]:
        """Get the schedule from cache, refreshing if necessary (caller should ideally handle refresh logic or manager does it)"""
        # For simplicity in this logic, we always refresh to ensure it's up to date with task rules
        self.refresh_schedule(start_date, end_date)
        
        # Now query the refreshed cache with task info
        cache_entries = self.repo.get_daily_cache_in_range(self.user_id, start_date, end_date)
        
        # Join with tasks (we already have them from repo)
        tasks = self.repo.get_active_tasks(self.user_id)
        task_map = {t.task_id: t for t in tasks}
        
        schedule_map = {}
        for entry in cache_entries:
            d = entry.target_date
            if d not in schedule_map:
                schedule_map[d] = {"date": d, "total_load": 0.0, "tasks": []}
            
            task = task_map.get(entry.task_id)
            if not task: continue # Should not happen if cache is fresh
            
            schedule_map[d]["total_load"] += entry.calculated_load
            schedule_map[d]["tasks"].append({
                "task_id": task.task_id,
                "task_name": task.task_name,
                "context": task.context,
                "status": entry.status,
                "load": entry.calculated_load
            })
            
        return sorted(schedule_map.values(), key=lambda x: x["date"])

    def update_task_execution(self, task_id: str, target_date: date, status: TaskStatus) -> Dict:
        """Update task execution and refresh the specific day's cache"""
        existing = self.repo.get_execution(self.user_id, task_id, target_date)
        
        if status == TaskStatus.TODO:
            if existing:
                self.repo.delete_execution(existing)
        else:
            if not existing:
                existing = TaskExecution(
                    user_id=self.user_id,
                    task_id=task_id,
                    target_date=target_date,
                    status=status,
                    progress=100 if status == TaskStatus.DONE else 0
                )
                self.repo.create_execution(existing)
            else:
                existing.status = status
                if status == TaskStatus.DONE:
                    existing.progress = 100
        
        self.session.commit()
        
        # Re-calculate and refresh for the specific day
        self.refresh_schedule(target_date, target_date, force=True)
        
        return {"message": f"Task execution updated: {status}", "status": status}

    def get_dashboard(self, start_date: date) -> Dict:
        """Get dashboard stats using Repository and Engine"""
        # Ensure cache is fresh for the week
        self.refresh_schedule(start_date, start_date + timedelta(days=6))
        
        cache_entries = self.repo.get_daily_cache_in_range(self.user_id, start_date, start_date + timedelta(days=6))
        tasks = self.repo.get_active_tasks(self.user_id) # Manager prefers Repo for entities
        
        today = date.today()
        today_data = self.engine.calculate_daily_load(today, cache_entries, tasks, include_completed=True)
        weekly_stats = self.engine.get_weekly_stats(start_date, cache_entries, tasks, include_completed=True)
        
        daily_breakdown = []
        for i in range(7):
            day = start_date + timedelta(days=i)
            daily_breakdown.append(self.engine.calculate_daily_load(day, cache_entries, tasks, include_completed=True))
            
        return {
            "today": today_data,
            "weekly": weekly_stats,
            "daily_breakdown": daily_breakdown,
            "config": self.engine.config
        }

    def get_trends(self, weeks: int, start_date: Optional[date] = None, include_completed: bool = True) -> List[Dict]:
        if not start_date:
            end_date = date.today()
            start_date = end_date - timedelta(weeks=weeks)
        else:
            end_date = start_date + timedelta(weeks=weeks)
            
        # Ensure cache for trend range
        self.refresh_schedule(start_date, end_date)
        
        cache_entries = self.repo.get_daily_cache_in_range(self.user_id, start_date, end_date)
        tasks = self.repo.get_active_tasks(self.user_id)
        
        return self.engine.get_trend_data(weeks, start_date, end_date, cache_entries, tasks, include_completed)

    def list_tasks(self, context: Optional[str] = None, active: Optional[bool] = None) -> List[Task]:
        return self.repo.list_tasks(self.user_id, context, active)

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.repo.get_task(self.user_id, task_id)

    def create_task(self, task: Task) -> Task:
        self.repo.create_task(task)
        self.session.commit()
        self.session.refresh(task)
        
        # Trigger refresh
        expand_start = task.start_date or date.today()
        expand_end = task.end_date or (date.today() + timedelta(days=90))
        self.refresh_schedule(expand_start, expand_end, force=True)
        return task

    def bulk_create_tasks(self, tasks: List[Task], start: date, end: date):
        self.repo.bulk_create_tasks(tasks)
        self.session.commit()
        self.refresh_schedule(start, end, force=True)

    def update_task(self, task_id: str, update_data: Dict[str, Any]) -> Optional[Task]:
        task = self.repo.get_task(self.user_id, task_id)
        if not task:
            return None
        
        for field, value in update_data.items():
            setattr(task, field, value)
        
        from datetime import datetime
        task.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(task)
        
        expand_start = task.start_date or date.today()
        expand_end = task.end_date or (date.today() + timedelta(days=90))
        self.refresh_schedule(expand_start, expand_end, force=True)
        return task

    def delete_task(self, task_id: str) -> bool:
        task = self.repo.get_task(self.user_id, task_id)
        if not task:
            return False
        
        self.repo.delete_task(task)
        self.session.commit()
        self.refresh_schedule(date.today(), date.today() + timedelta(days=90), force=True)
        return True

    def bulk_delete_tasks(self, task_ids: List[str]) -> int:
        count = self.repo.bulk_delete_tasks(self.user_id, task_ids)
        if count > 0:
            self.session.commit()
            self.refresh_schedule(date.today(), date.today() + timedelta(days=90), force=True)
        return count

    def bulk_update_active(self, task_ids: List[str], active: bool) -> int:
        tasks = self.repo.bulk_update_active(self.user_id, task_ids, active)
        if tasks:
            from datetime import datetime
            for t in tasks:
                t.updated_at = datetime.utcnow()
            self.session.commit()
            self.refresh_schedule(date.today(), date.today() + timedelta(days=90), force=True)
        return len(tasks)

    def get_task_history(self, task_id: str, start_date: date, end_date: date) -> List[TaskExecution]:
        return self.repo.get_task_history(task_id, start_date, end_date)

    def create_exception(self, exception_data: Dict[str, Any]) -> None:
        from ..models.database import TaskException
        new_exc = TaskException(
            **exception_data,
            user_id=self.user_id
        )
        self.repo.create_exception(new_exc)
        self.session.commit()
        self.refresh_schedule(new_exc.target_date, new_exc.target_date, force=True)
