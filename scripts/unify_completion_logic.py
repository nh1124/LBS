import os
import sys
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add src to path so we can import models
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.models.database import Task, TaskCompletion, TaskStatus
from src.config import settings

def migrate():
    print("Starting unified completion logic migration...")
    
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 1. Find all tasks with status 'done'
        done_tasks = session.query(Task).filter(Task.status == TaskStatus.DONE).all()
        print(f"Found {len(done_tasks)} tasks with 'done' status.")
        
        completions_created = 0
        for task in done_tasks:
            # Determine target date for completion record
            # For ONCE tasks, use due_date. If missing, use today.
            # For recurring tasks, we use today as a fallback since history wasn't tracked.
            target_date = task.due_date or date.today()
            
            # Check if completion already exists
            exists = session.query(TaskCompletion).filter(
                TaskCompletion.task_id == task.task_id,
                TaskCompletion.completed_date == target_date
            ).first()
            
            if not exists:
                new_comp = TaskCompletion(
                    user_id=task.user_id,
                    task_id=task.task_id,
                    completed_date=target_date
                )
                session.add(new_comp)
                completions_created += 1
        
        print(f"Created {completions_created} history records.")
        
        # 2. Reset all tasks to 'todo' status
        updated_count = session.query(Task).filter(Task.status == TaskStatus.DONE).update({Task.status: TaskStatus.TODO})
        print(f"Reset {updated_count} master tasks to 'todo'.")
        
        session.commit()
        print("Migration successfully completed.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    migrate()
