"""Test script to check schedule API response"""
import sys
sys.path.insert(0, '.')

from src.models.database import get_db, Task
from src.services.manager import LBSManager
from datetime import date

session = next(get_db())
task = session.query(Task).filter(Task.task_name.like('%Part time%')).first()

if not task:
    print("No 'Part time' task found")
    exit(1)

manager = LBSManager(session, task.user_id)
schedule = manager.get_schedule(date(2026, 1, 16), date(2026, 1, 22))

print("Schedule results:")
for day in schedule:
    task_names = [t['task_name'] for t in day['tasks']]
    print(f"  {day['date']}: {len(day['tasks'])} tasks - {task_names}")
