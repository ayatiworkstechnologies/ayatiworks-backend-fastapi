
import sys
import os

# Add the current directory to sys.path to make app module importable
sys.path.append(os.getcwd())

from app.database import SessionLocal

# Import ALL models including base to clear up registry issues
from app.models.base import Base

# Import models in an order that respects dependencies if possible, 
# or just import all of them to ensure registry is populated
from app.models.auth import User
from app.models.employee import Employee
from app.models.project import Project
from app.models.client import Client
from app.models.organization import Department
from app.models.team import Team
# Add any other models that Employee might relate to

def get_employee_data():
    db = SessionLocal()
    try:
        employees = db.query(Employee).all()
        print(f"Total Employees: {len(employees)}")
        print("-" * 30)
        for emp in employees:
            # Access relationship directly if loaded, or query efficiently
            # Here we query manually to be safe against lazy load issues in script
            user = db.query(User).filter(User.id == emp.user_id).first()
            user_name = user.full_name if user else "Unknown User"
            user_email = user.email if user else "Unknown Email"
            
            # Check for department relationship or field
            dept_info = emp.department_id if hasattr(emp, 'department_id') else "N/A"
            if hasattr(emp, 'department'):
                 dept_info = emp.department
            
            print(f"ID: {emp.id}, User: {user_name} ({user_email}), Role: {emp.job_title}, Dept: {dept_info}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    get_employee_data()
