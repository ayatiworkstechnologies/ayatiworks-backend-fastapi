
import sys
import os

# Ensure we are running from backend directory
# or verify app module is importable
try:
    from app.database import SessionLocal
except ImportError:
    # Fallback if run from parent
    sys.path.append(os.path.join(os.getcwd(), 'backend'))
    from app.database import SessionLocal
    
from app.models.auth import User, Role

def check_users():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"Found {len(users)} users:")
        for u in users:
            role_code = u.role.code if u.role else "NO_ROLE"
            emp_info = ""
            if u.employee:
                dept = u.employee.department.name if u.employee.department else "No Dept"
                desig = u.employee.designation.name if u.employee.designation else "No Desig"
                emp_info = f" [Linked Employee: {u.employee.employee_code} | {dept} | {desig}]"
            print(f" - {u.email} (Role: {role_code}, ID: {u.id}){emp_info}")
            
        client_role = db.query(Role).filter_by(code="CLIENT").first()
        if client_role:
             print(f"Client Role ID: {client_role.id}")
        else:
             print("Client Role NOT FOUND")
        
        # Check Client Profile
        from app.models.client import Client, Lead
        client = db.query(Client).filter_by(email="client@demo.com").first()
        if client:
            print(f"Client Profile Found: {client.name} (ID: {client.id})")
            leads = db.query(Lead).filter_by(client_id=client.id).all()
            print(f"Leads found for client: {len(leads)}")
            if leads:
                print(f"Sample Lead: {leads[0].name} (Campaign: {leads[0].campaign})")
        else:
            print("Client Profile NOT FOUND for client@demo.com")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_users()
