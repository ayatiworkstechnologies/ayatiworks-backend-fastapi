
from app.database import SessionLocal
from app.models.auth import User, Role
from app.models.employee import Employee

def verify():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print("\n" + "="*80)
        print(f"{'EMAIL':<30} | {'ROLE':<15} | {'EMPLOYEE CODE':<15} | {'DEPT'}")
        print("-"*80)
        for u in users:
            role = u.role.code if u.role else "N/A"
            emp_code = u.employee.employee_code if u.employee else "N/A"
            dept = u.employee.department.name if u.employee and u.employee.department else "N/A"
            print(f"{u.email:<30} | {role:<15} | {emp_code:<15} | {dept}")
        print("="*80 + "\n")
    finally:
        db.close()

if __name__ == "__main__":
    verify()
