from sqlalchemy import text
from src.models.database import engine

def migrate():
    print("Running clean auth rebuild migration...")
    with engine.connect() as conn:
        # 1. Drop legacy column from users table
        try:
            conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS api_key;"))
            print("Dropped legacy api_key column from users table")
        except Exception as e:
            print(f"Note: Could not drop api_key: {e}")
            
        # 2. Recreate api_keys table to match new schema
        # We drop and recreate because the schema changes are significant (Clean Slate Rebuild)
        try:
            conn.execute(text("DROP TABLE IF EXISTS api_keys CASCADE;"))
            print("Dropped legacy api_keys table")
            
            # Re-creating via SQLAlchemy Base in main.py usually handles this, 
            # but we can also execute the DDL here for immediate effect if needed.
            # However, Base.metadata.create_all(bind=engine) in main.py is safer.
        except Exception as e:
            print(f"Note: Could not drop api_keys table: {e}")

        conn.commit()

    print("Migration (clean up) complete. SQLAlchemy will recreate tables on startup.")

if __name__ == "__main__":
    migrate()
