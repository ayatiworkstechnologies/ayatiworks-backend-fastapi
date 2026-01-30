import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db, engine
from app.models.blog import Blog

def debug_mysql():
    try:
        print("Connecting to DB...")
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print(f"Connection Test: {result.fetchone()[0]}")
            
            print("Querying Blog table for ID 1...")
            # Use raw SQL to bypass ORM mapping potential issues
            result = connection.execute(text("SELECT * FROM blogs WHERE id = 1"))
            row = result.fetchone()
            if row:
                print(f"Found Blog ID 1 (Raw): {row}")
            else:
                print("Blog ID 1 NOT FOUND (Raw)")

    except Exception as e:
        print(f"DB Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_mysql()
