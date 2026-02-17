
import sys
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load env manually
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(base_dir, '.env'))
load_dotenv(os.path.join(base_dir, 'backend', '.env'))

def list_modules():
    # Helper to get DATABASE_URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Warning: DATABASE_URL not found in environment, trying default SQLite...")
        # Fallback to local sqlite
        db_path = os.path.join(base_dir, 'sql_app.db')
        db_url = f"sqlite:///{db_path}"
        print(f"Using fallback DB URL: {db_url}")

    # Create engine directly
    try:
        engine = create_engine(db_url)
    except Exception as e:
        print(f"Error creating engine: {e}")
        return
    
    try:
        with engine.connect() as connection:
            print("\nFetching Client Modules...")
            print("-" * 50)
            
            query = text("SELECT id, name, slug, client_id, created_at FROM client_modules WHERE is_deleted = false")
            rows = connection.execute(query).fetchall()
            
            if rows:
                print(f"{'ID':<5} {'Name':<20} {'Slug':<20} {'Client ID':<10}")
                print("-" * 60)
                for row in rows:
                    print(f"{row[0]:<5} {row[1]:<20} {row[2]:<20} {row[3]:<10}")
            else:
                print("\nNo modules found.")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_modules()
