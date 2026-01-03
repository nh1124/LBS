from datetime import date, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from calendar import monthrange
import time
import logging

logger = logging.getLogger(__name__)

from ..models.database import Task, TaskException, LBSDailyCache, SystemConfig, TaskStatus
from ..config import settings

class LBSEngine:
    """User-scoped LBS calculation and expansion logic"""
    
    def __init__(self, db_session: Session, user_id: str):
        self.session = db_session
        self.user_id = user_id
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, float]:
        """Load user-specific or default configuration"""
        configs = self.session.query(SystemConfig).filter(SystemConfig.user_id == self.user_id).all()
        config_dict = {c.key: float(c.value) for c in configs}
        
        # Fill defaults
        return {
            "ALPHA": config_dict.get("ALPHA", settings.DEFAULT_ALPHA),
            "BETA": config_dict.get("BETA", settings.DEFAULT_BETA),
            "CAP": config_dict.get("CAP", settings.DEFAULT_CAP),
            "SWITCH_COST": config_dict.get("SWITCH_COST", settings.DEFAULT_SWITCH_COST),
        }
    
    def expand_tasks(self, start_date: date, end_date: date) -> None:
        """Expand task rules into daily cache for the user's date range"""
        start_time = time.time()
        
        # Clear existing cache for this user and range
        self.session.query(LBSDailyCache).filter(
            LBSDailyCache.user_id == self.user_id,
            LBSDailyCache.target_date >= start_date,
            LBSDailyCache.target_date <= end_date
        ).delete()
        
        # Get all active tasks for user
        tasks = self.session.query(Task).filter(
            Task.user_id == self.user_id,
            Task.active == True
        ).all()
        
        # Load exceptions
        exceptions_query = self.session.query(TaskException).filter(
            TaskException.user_id == self.user_id,
            TaskException.target_date >= start_date,
            TaskException.target_date <= end_date
        ).all()
        
        exceptions_dict = {(exc.task_id, exc.target_date): exc for exc in exceptions_query}
        
        cache_entries = []
        
        # Process recurrence
        for task in tasks:
            current_date = start_date
            # Optimization: for ONCE tasks, we only care about the due_date OR exceptions
            if task.rule_type == "ONCE":
                # Regular occurrence
                if task.due_date and start_date <= task.due_date <= end_date:
                    self._process_day(task, task.due_date, exceptions_dict, cache_entries, force_check=False)
                
                # Check for FORCE_DO exceptions on other dates
                for (t_id, d), exc in exceptions_dict.items():
                    if t_id == task.task_id and exc.exception_type == "FORCE_DO":
                        if d != task.due_date: # Don't double process
                            self._process_day(task, d, exceptions_dict, cache_entries, force_check=True)
                continue

            # Recurring tasks
            while current_date <= end_date:
                occurs = self._should_task_occur(task, current_date)
                exception = exceptions_dict.get((task.task_id, current_date))
                
                if occurs:
                    # Normal occurrence, check for SKIP
                    if not (exception and exception.exception_type == "SKIP"):
                        self._process_day(task, current_date, exceptions_dict, cache_entries, force_check=False)
                else:
                    # No normal occurrence, check for FORCE_DO
                    if exception and exception.exception_type == "FORCE_DO":
                        self._process_day(task, current_date, exceptions_dict, cache_entries, force_check=True)
                
                current_date += timedelta(days=1)
        
        if cache_entries:
            self.session.bulk_save_objects(cache_entries)
        
        self.session.commit()
        
        # Update overflow flags
        self._update_overflow_flags(start_date, end_date)
        
        logger.info(f"[LBS Engine] Expanded {len(cache_entries)} entries for user {self.user_id} in {time.time() - start_time:.3f}s")

    def _process_day(self, task, day_date, exceptions_dict, cache_entries, force_check=False):
        # Implementation moved logic out to allow FORCE_DO check
        exception = exceptions_dict.get((task.task_id, day_date))
        
        load = task.base_load_score
        if exception and exception.exception_type == "OVERRIDE_LOAD":
            load = exception.override_load_value
        elif exception and exception.exception_type == "FORCE_DO" and exception.override_load_value is not None:
             load = exception.override_load_value
            
        cache_entries.append(LBSDailyCache(
            user_id=self.user_id,
            target_date=day_date,
            task_id=task.task_id,
            calculated_load=load,
            status="completed" if task.status == TaskStatus.DONE else "planned"
        ))

    def _should_task_occur(self, task: Task, target_date: date) -> bool:
        if task.start_date and target_date < task.start_date: return False
        if task.end_date and target_date > task.end_date: return False
        
        rule = task.rule_type
        if rule == "WEEKLY":
            weekday = target_date.weekday()
            flags = [task.mon, task.tue, task.wed, task.thu, task.fri, task.sat, task.sun]
            return flags[weekday]
        
        if rule == "EVERY_N_DAYS":
            if not task.anchor_date or not task.interval_days: return False
            diff = (target_date - task.anchor_date).days
            return diff >= 0 and diff % task.interval_days == 0
            
        if rule == "MONTHLY_DAY":
            if not task.month_day: return False
            _, last = monthrange(target_date.year, target_date.month)
            return target_date.day == min(task.month_day, last)
            
        if rule == "MONTHLY_NTH_WEEKDAY":
            if not task.nth_in_month or not task.weekday_mon1: return False
            target_weekday = (task.weekday_mon1 - 1) % 7
            if target_date.weekday() != target_weekday: return False
            occ = (target_date.day - 1) // 7 + 1
            if task.nth_in_month == -1:
                return (target_date + timedelta(days=7)).month != target_date.month
            return occ == task.nth_in_month
        
        return False

    def calculate_daily_load(self, target_date: date, include_completed: bool = True) -> Dict:
        alpha = self.config["ALPHA"]
        beta = self.config["BETA"]
        switch_cost = self.config["SWITCH_COST"]
        cap = self.config["CAP"]
        
        query = self.session.query(LBSDailyCache).filter(
            LBSDailyCache.user_id == self.user_id,
            LBSDailyCache.target_date == target_date,
            LBSDailyCache.status != "skipped"
        )
        
        if not include_completed:
            query = query.filter(LBSDailyCache.status != "completed")
            
        cache_entries = query.all()
        
        if not cache_entries:
            return {
                "date": target_date, 
                "base_load": 0.0,
                "task_count": 0, 
                "unique_contexts": 0,
                "adjusted_load": 0.0, 
                "count_penalty": 0.0,
                "context_penalty": 0.0,
                "level": "SAFE", 
                "cap": cap, 
                "tasks": []
            }
            
        base_load = sum(e.calculated_load for e in cache_entries)
        task_count = len(cache_entries)
        
        # Get tasks for these entries to find contexts
        task_ids = [e.task_id for e in cache_entries]
        tasks = self.session.query(Task).filter(Task.task_id.in_(task_ids)).all()
        unique_contexts = len(set(t.context for t in tasks))
        
        count_penalty = alpha * (task_count ** beta)
        context_penalty = switch_cost * max(unique_contexts - 1, 0)
        adjusted_load = base_load + count_penalty + context_penalty
        
        level = "SAFE"
        if adjusted_load > cap: level = "CRITICAL"
        elif adjusted_load >= 8.0: level = "DANGER"
        elif adjusted_load >= 6.0: level = "WARNING"
        
        return {
            "date": target_date,
            "base_load": round(base_load, 2),
            "task_count": task_count,
            "unique_contexts": unique_contexts,
            "adjusted_load": round(adjusted_load, 2),
            "count_penalty": round(count_penalty, 2),
            "context_penalty": round(context_penalty, 2),
            "level": level,
            "cap": cap,
            "tasks": [
                {"task_id": t.task_id, "task_name": t.task_name, "context": t.context, "load": next(e for e in cache_entries if e.task_id == t.task_id).calculated_load}
                for t in tasks
            ]
        }

    def _update_overflow_flags(self, start_date: date, end_date: date) -> None:
        cap = self.config["CAP"]
        current = start_date
        while current <= end_date:
            load_data = self.calculate_daily_load(current)
            is_overflow = load_data["adjusted_load"] > cap
            self.session.query(LBSDailyCache).filter(
                LBSDailyCache.user_id == self.user_id,
                LBSDailyCache.target_date == current
            ).update({"is_overflow": is_overflow})
            current += timedelta(days=1)
        self.session.commit()

    def get_weekly_stats(self, start_date: date, include_completed: bool = True) -> Dict:
        daily_loads = []
        for i in range(7):
            day = start_date + timedelta(days=i)
            daily_loads.append(self.calculate_daily_load(day, include_completed=include_completed)["adjusted_load"])
        
        avg = sum(daily_loads) / 7
        recovery_days = sum(1 for l in daily_loads if l < 4.0)
        return {
            "average_load": round(avg, 2),
            "recovery_rate": round((recovery_days / 7) * 100, 1)
        }

    def get_trend_data(self, weeks: int = 12, start_date: Optional[date] = None, include_completed: bool = True) -> List[Dict]:
        """Get average and max load per week for trend analysis"""
        if not start_date:
            end_date = date.today()
            start_date = end_date - timedelta(weeks=weeks)
        else:
            end_date = start_date + timedelta(weeks=weeks)
        
        trends = []
        current_week_start = start_date
        
        while current_week_start <= end_date:
            week_end = current_week_start + timedelta(days=6)
            week_loads = []
            
            curr = current_week_start
            while curr <= week_end and curr <= end_date:
                daily = self.calculate_daily_load(curr, include_completed=include_completed)
                week_loads.append(daily["adjusted_load"])
                curr += timedelta(days=1)
                
            if week_loads:
                trends.append({
                    "date": str(current_week_start),
                    "average_load": round(sum(week_loads) / len(week_loads), 2),
                    "max_load": round(max(week_loads), 2),
                    "min_load": round(min(week_loads), 2)
                })
            current_week_start += timedelta(days=7)
            
        return trends

    def get_context_distribution(self, start: date, end: date, include_completed: bool = True) -> List[Dict]:
        """Get load grouped by context (spoke) for each day"""
        distribution = {}
        
        curr = start
        while curr <= end:
            query = self.session.query(LBSDailyCache).filter(
                LBSDailyCache.user_id == self.user_id,
                LBSDailyCache.target_date == curr,
                LBSDailyCache.status != "skipped"
            )
            
            if not include_completed:
                query = query.filter(LBSDailyCache.status != "completed")
                
            cache_entries = query.all()
            
            if cache_entries:
                date_str = str(curr)
                distribution[date_str] = {"date": date_str, "total_load": 0, "contexts": []}
                
                context_map = {}
                for entry in cache_entries:
                    task = self.session.query(Task).filter(Task.task_id == entry.task_id).first()
                    context = task.context or "unassigned"
                    context_map[context] = context_map.get(context, 0) + entry.calculated_load
                
                for ctx, load in context_map.items():
                    distribution[date_str]["contexts"].append({"context": ctx, "load": round(load, 2)})
                    distribution[date_str]["total_load"] += load
                
                distribution[date_str]["total_load"] = round(distribution[date_str]["total_load"], 2)
            
            curr += timedelta(days=1)
            
        return list(distribution.values())
