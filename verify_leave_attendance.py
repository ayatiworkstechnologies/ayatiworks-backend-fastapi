import sys
import os
from datetime import date, timedelta

# Add current directory to path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
# Force utf-8 for windows console
sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

from app.database import SessionLocal
from app.services.leave_service import LeaveService
from app.services.attendance_service import AttendanceService
from app.services.employee_service import EmployeeService
from app.models.leave import LeaveType, Leave

def verify_integration():
    db = SessionLocal()
    try:
        print("🚀 Starting Leave-Attendance Integration Verification...")
        
        # 1. Setup Data
        # Get an employee
        # Note: using page_size=1
        employees_result = EmployeeService(db).get_all(page_size=1)
        if not employees_result or not employees_result[0]:
            print("❌ No employees found. Please seed data first.")
            return

        employee = employees_result[0][0]
        print(f"👤 Testing with Employee: {employee.user.full_name} ({employee.employee_code})")
        
        # Get a leave type
        leave_type = db.query(LeaveType).first()
        if not leave_type:
            print("❌ No leave types found.")
            return

        # 2. Create a Leave Request for next Monday
        today = date.today()
        # Find next monday
        next_monday = today + timedelta(days=(7 - today.weekday()))
        
        print(f"📅 Applying for leave on: {next_monday} ({leave_type.name})")
        
        from app.schemas.leave import LeaveCreate, LeaveApprovalRequest
        leave_data = LeaveCreate(
            leave_type_id=leave_type.id,
            from_date=next_monday,
            to_date=next_monday,
            reason="Integration Test Verification",
            is_half_day=False
        )
        
        ls = LeaveService(db)
        
        # Check if leave already exists for this date to avoid duplicate error
        existing_leave = db.query(Leave).filter(
            Leave.employee_id == employee.id,
            Leave.from_date == next_monday,
            Leave.is_deleted == False
        ).first()
        
        if existing_leave:
            print(f"⚠️ Leave already exists. Deleting ID: {existing_leave.id} to re-test...")
            db.delete(existing_leave)
            db.commit()
            
            leave = ls.apply_leave(employee.id, leave_data, created_by=employee.user.id)
            print(f"✅ New Leave Applied. ID: {leave.id}, Status: {leave.status}")
        else:
            leave = ls.apply_leave(employee.id, leave_data, created_by=employee.user.id)
            print(f"✅ Leave Applied. ID: {leave.id}, Status: {leave.status}")
        
        # 3. Approve Leave
        if leave.status == "pending":
            print("✍️  Approving leave...")
            approval_data = LeaveApprovalRequest(
                status="approved",
                remarks="Approved by Verification Script"
            )
            # Use employee's own manager or just self (admin) for test
            approver_id = employee.manager_id if employee.manager_id else employee.user.id
            
            ls.approve_leave(leave.id, approver_id, approval_data)
            print("✅ Leave Approved.")
        
        # 4. Check Attendance
        print("🔍 Checking Attendance records...")
        from app.models.attendance import Attendance
        attendance = db.query(Attendance).filter(
            Attendance.employee_id == employee.id,
            Attendance.date == next_monday
        ).first()
        
        if attendance:
             print(f"📄 Attendance Record Found for {next_monday}:")
             print(f"   - Status: {attendance.status}")
             print(f"   - Work Mode: {attendance.work_mode}")
             print(f"   - Notes: {attendance.notes}")
             
             if attendance.status == "on_leave" and attendance.work_mode == "leave":
                 print("\nSUCCESS: Attendance automatically updated to 'on_leave'! 🎉")
             else:
                 print(f"\nFAILURE: Attendance status is {attendance.status}, expected 'on_leave'. ❌")
        else:
             print("\nFAILURE: No attendance record found for the leave date. ❌")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_integration()
