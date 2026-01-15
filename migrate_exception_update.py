"""
Database Migration Script for Exception CRUD & Flexibility Features

This script adds:
- tasks.is_locked (Boolean)
- task_exceptions.start_time (Time)
- task_exceptions.end_time (Time)

Run inside the backend container or on local dev environment.
"""
import os
import sys

# Add parent to path to import settings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from src.config import settings

def run_migration():
    engine = create_engine(settings.DATABASE_URL)
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        # Check if tasks.is_locked exists
        task_columns = [col['name'] for col in inspector.get_columns('tasks')]
        
        if 'is_locked' not in task_columns:
            print("Adding 'is_locked' column to tasks table...")
            try:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN is_locked BOOLEAN DEFAULT FALSE"))
                conn.commit()
                print("✓ Added 'is_locked' column to tasks")
            except Exception as e:
                print(f"✗ Error adding 'is_locked': {e}")
                conn.rollback()
        else:
            print("✓ 'is_locked' column already exists in tasks")
        
        # Check if task_exceptions.start_time exists
        exc_columns = [col['name'] for col in inspector.get_columns('task_exceptions')]
        
        if 'start_time' not in exc_columns:
            print("Adding 'start_time' column to task_exceptions table...")
            try:
                conn.execute(text("ALTER TABLE task_exceptions ADD COLUMN start_time TIME"))
                conn.commit()
                print("✓ Added 'start_time' column to task_exceptions")
            except Exception as e:
                print(f"✗ Error adding 'start_time': {e}")
                conn.rollback()
        else:
            print("✓ 'start_time' column already exists in task_exceptions")
        
        if 'end_time' not in exc_columns:
            print("Adding 'end_time' column to task_exceptions table...")
            try:
                conn.execute(text("ALTER TABLE task_exceptions ADD COLUMN end_time TIME"))
                conn.commit()
                print("✓ Added 'end_time' column to task_exceptions")
            except Exception as e:
                print(f"✗ Error adding 'end_time': {e}")
                conn.rollback()
        else:
            print("✓ 'end_time' column already exists in task_exceptions")
    
    print("\nMigration complete!")

if __name__ == "__main__":
    run_migration()
