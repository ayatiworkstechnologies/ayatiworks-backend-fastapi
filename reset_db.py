
import sys
import os
from sqlalchemy import create_engine, text
from app.config import settings
from app.database import init_db
from seed import seed_db

def reset_database():
    print("=" * 60)
    print("DATABASE RESET SCRIPT")
    print("=" * 60)
    
    # 1. Parse DATABASE_URL to get the server URL (without DB name)
    # mysql+pymysql://user:pass@host:port/dbname
    db_url = settings.DATABASE_URL
    base_url = db_url.rsplit('/', 1)[0] + '/'
    db_name = db_url.rsplit('/', 1)[1]
    
    print(f"Connecting to MySQL server at: {base_url}")
    print(f"Target Database: {db_name}")
    
    # 2. Create engine to the server (not the specific DB)
    try:
        engine = create_engine(base_url)
        with engine.connect() as conn:
            # MySQL requires autocommit for DROP/CREATE
            conn.execute(text("COMMIT")) 
            
            print(f"\nDropping database '{db_name}' if it exists...")
            conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
            
            print(f"Creating database '{db_name}'...")
            conn.execute(text(f"CREATE DATABASE {db_name}"))
            print("Successfully recreated database structure.")
            
    except Exception as e:
        print(f"\nError durante database recreation: {e}")
        return

    # 3. Initialize Tables
    print("\nStep 2: Initializing Tables...")
    try:
        init_db()
        print("  All tables created successfully.")
    except Exception as e:
        print(f"  Error initializing tables: {e}")
        return

    # 4. Seed Data
    print("\nStep 3: Seeding Data...")
    try:
        seed_db()
        print("\nDatabase reset and seeding completed successfully!")
    except Exception as e:
        print(f"  Error seeding database: {e}")

if __name__ == "__main__":
    reset_database()
