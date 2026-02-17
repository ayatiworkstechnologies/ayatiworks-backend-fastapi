
import sys
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Try to load env from multiple possible locations
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(base_dir, '.env'))
load_dotenv(os.path.join(base_dir, 'backend', '.env'))

def get_employee_stats():
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
        engine = create_engine(db_url, pool_pre_ping=True)
    except Exception as e:
        print(f"Error creating engine: {e}")
        return
    
    try:
        with engine.connect() as connection:
            print("\nFetching Employee Data (Raw SQL)...")
            print("-" * 50)
            
            # Count
            try:
                result = connection.execute(text("SELECT COUNT(*) FROM employees WHERE is_deleted = false"))
                count = result.scalar()
                print(f"Total Active Employees: {count}")
                print("-" * 50)
            except Exception as e:
                 print(f"Error executing count query: {e}")
                 return

            # Details
            query = text("""
                SELECT e.id, e.employee_code, u.first_name, u.last_name, u.email, e.employment_status, u.role_id 
                FROM employees e
                JOIN users u ON e.user_id = u.id
                WHERE e.is_deleted = false
                ORDER BY e.created_at DESC
                LIMIT 50
            """)
            
            # Get roles map
            role_map = {}
            try:
                roles_res = connection.execute(text("SELECT id, code FROM roles")).fetchall()
                role_map = {r[0]: r[1] for r in roles_res}
            except:
                print("Could not fetch roles, skipping role mapping")
            
            rows = connection.execute(query).fetchall()
            
            if rows:
                print(f"{'ID':<5} {'Code':<10} {'Name':<25} {'Role':<15} {'Email':<30} {'Status':<10}")
                print("-" * 100)
                
                for row in rows:
                    fname = row[2] or ""
                    lname = row[3] or ""
                    full_name = f"{fname} {lname}".strip()
                    role_id = row[6]
                    role_name = role_map.get(role_id, str(role_id))
                    
                    if len(full_name) > 24: full_name = full_name[:21] + "..."
                    email = row[4] or ""
                    if len(email) > 29: email = email[:26] + "..."
                    
                    print(f"{row[0]:<5} {row[1]:<10} {full_name:<25} {role_name:<15} {email:<30} {row[5]:<10}")
            else:
                print("\nNo employees found.")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_employee_stats()
