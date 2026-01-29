"""
Leave management service.
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.leave import Leave, LeaveType, LeaveBalance, Holiday
from app.models.employee import Employee
from app.schemas.leave import LeaveCreate, LeaveUpdate, LeaveApprovalRequest


class LeaveService:
    """Leave service class."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_leave_days(self, from_date: date, to_date: date, is_half_day: bool = False) -> float:
        """Calculate number of leave days excluding weekends."""
        if is_half_day:
            return 0.5
        
        days = 0
        current = from_date
        while current <= to_date:
            # Skip weekends
            if current.weekday() < 5:  # Monday to Friday
                days += 1
            current += timedelta(days=1)
        
        return float(days)
    
    def get_balance(self, employee_id: int, leave_type_id: int, year: int) -> Optional[LeaveBalance]:
        """Get leave balance for an employee."""
        return self.db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type_id == leave_type_id,
            LeaveBalance.year == year,
            LeaveBalance.is_deleted == False
        ).first()
    
    def get_all_balances(self, employee_id: int, year: int) -> List[dict]:
        """Get all leave balances for an employee."""
        leave_types = self.db.query(LeaveType).filter(
            LeaveType.is_deleted == False,
            LeaveType.is_active == True
        ).all()
        
        balances = []
        for lt in leave_types:
            balance = self.get_balance(employee_id, lt.id, year)
            if balance:
                balances.append({
                    "leave_type_id": lt.id,
                    "leave_type_name": lt.name,
                    "leave_type_code": lt.code,
                    "allocated": balance.allocated,
                    "used": balance.used,
                    "pending": balance.pending,
                    "carry_forward": balance.carry_forward,
                    "encashed": balance.encashed,
                    "available": balance.available
                })
            else:
                balances.append({
                    "leave_type_id": lt.id,
                    "leave_type_name": lt.name,
                    "leave_type_code": lt.code,
                    "allocated": lt.days_allowed,
                    "used": 0,
                    "pending": 0,
                    "carry_forward": 0,
                    "encashed": 0,
                    "available": lt.days_allowed
                })
        
        return balances
    
    def apply_leave(self, employee_id: int, data: LeaveCreate, created_by: int = None) -> Leave:
        """Apply for leave."""
        # Calculate days
        days = self.calculate_leave_days(data.from_date, data.to_date, data.is_half_day)
        
        # Check balance
        year = data.from_date.year
        balance = self.get_balance(employee_id, data.leave_type_id, year)
        
        if balance and balance.available < days:
            raise ValueError("Insufficient leave balance")
        
        # Create leave request
        leave = Leave(
            employee_id=employee_id,
            leave_type_id=data.leave_type_id,
            from_date=data.from_date,
            to_date=data.to_date,
            days=days,
            is_half_day=data.is_half_day,
            half_day_type=data.half_day_type,
            reason=data.reason,
            contact_during_leave=data.contact_during_leave,
            status="pending",
            created_by=created_by
        )
        
        self.db.add(leave)
        
        # Update pending balance
        if balance:
            balance.pending += days
        
        self.db.commit()
        self.db.refresh(leave)
        
        return leave
    
    def approve_leave(self, leave_id: int, approver_id: int, data: LeaveApprovalRequest) -> Optional[Leave]:
        """Approve or reject a leave request."""
        from app.services.attendance_service import AttendanceService

        leave = self.db.query(Leave).filter(
            Leave.id == leave_id,
            Leave.is_deleted == False
        ).first()
        
        if not leave:
            return None
        
        if leave.status != "pending":
            raise ValueError("Leave is not pending")
        
        leave.status = data.status
        leave.approver_id = approver_id
        leave.approved_at = date.today()
        leave.approver_remarks = data.remarks
        
        # Update balance
        year = leave.from_date.year
        balance = self.get_balance(leave.employee_id, leave.leave_type_id, year)
        
        if balance:
            balance.pending -= leave.days
            
            if data.status == "approved":
                balance.used += leave.days

                # Create/Update Attendance Records for the leave period
                att_service = AttendanceService(self.db)
                current = leave.from_date
                while current <= leave.to_date:
                    # Skip weekends (Mon=0, Sun=6)
                    if current.weekday() < 5: 
                         att_service.mark_employee_on_leave(
                             employee_id=leave.employee_id,
                             attendance_date=current,
                             leave_type_name=leave.leave_type.name if leave.leave_type else "Leave",
                             is_half_day=leave.is_half_day,
                             notes=data.remarks
                         )
                    current += timedelta(days=1)
        
        self.db.commit()
        self.db.refresh(leave)
        
        return leave
    
    def cancel_leave(self, leave_id: int, cancelled_by: int, reason: str) -> Optional[Leave]:
        """Cancel a leave request."""
        leave = self.db.query(Leave).filter(
            Leave.id == leave_id,
            Leave.is_deleted == False
        ).first()
        
        if not leave:
            return None
        
        if leave.status == "cancelled":
            raise ValueError("Leave already cancelled")
        
        old_status = leave.status
        leave.status = "cancelled"
        leave.cancelled_by = cancelled_by
        leave.cancelled_at = date.today()
        leave.cancellation_reason = reason
        
        # Restore balance
        year = leave.from_date.year
        balance = self.get_balance(leave.employee_id, leave.leave_type_id, year)
        
        if balance:
            if old_status == "pending":
                balance.pending -= leave.days
            elif old_status == "approved":
                balance.used -= leave.days
        
        self.db.commit()
        self.db.refresh(leave)
        
        return leave
    
    def get_employee_leaves(
        self,
        employee_id: int,
        year: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Leave], int]:
        """Get leaves for an employee."""
        query = self.db.query(Leave).filter(
            Leave.employee_id == employee_id,
            Leave.is_deleted == False
        )
        
        if year:
            query = query.filter(func.year(Leave.from_date) == year)
        
        if status:
            query = query.filter(Leave.status == status)
        
        total = query.count()
        
        offset = (page - 1) * page_size
        leaves = query.order_by(Leave.from_date.desc()).offset(offset).limit(page_size).all()
        
        return leaves, total
    
    def get_pending_approvals(self, approver_id: int) -> List[Leave]:
        """Get pending leaves for approval by a manager."""
        # Get employees under this manager
        employees = self.db.query(Employee).filter(
            Employee.manager_id == approver_id,
            Employee.is_deleted == False
        ).all()
        
        employee_ids = [e.id for e in employees]
        
        return self.db.query(Leave).filter(
            Leave.employee_id.in_(employee_ids),
            Leave.status == "pending",
            Leave.is_deleted == False
        ).order_by(Leave.created_at).all()


class HolidayService:
    """Holiday service class."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, holiday_id: int) -> Optional[Holiday]:
        """Get holiday by ID."""
        return self.db.query(Holiday).filter(
            Holiday.id == holiday_id,
            Holiday.is_deleted == False
        ).first()
    
    def get_all(
        self,
        company_id: Optional[int] = None,
        year: Optional[int] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[Holiday], int]:
        """Get all holidays."""
        query = self.db.query(Holiday).filter(Holiday.is_deleted == False)
        
        if company_id:
            query = query.filter(
                (Holiday.company_id == company_id) | (Holiday.company_id == None)
            )
        
        if year:
            query = query.filter(Holiday.year == year)
        
        total = query.count()
        
        offset = (page - 1) * page_size
        holidays = query.order_by(Holiday.date).offset(offset).limit(page_size).all()
        
        return holidays, total
    
    def get_upcoming(self, company_id: Optional[int] = None, limit: int = 5) -> List[Holiday]:
        """Get upcoming holidays."""
        query = self.db.query(Holiday).filter(
            Holiday.date >= date.today(),
            Holiday.is_deleted == False
        )
        
        if company_id:
            query = query.filter(
                (Holiday.company_id == company_id) | (Holiday.company_id == None)
            )
        
        return query.order_by(Holiday.date).limit(limit).all()
    
    def create(self, company_id: Optional[int], name: str, holiday_date: date, 
               holiday_type: str = "public", created_by: int = None) -> Holiday:
        """Create a new holiday."""
        holiday = Holiday(
            company_id=company_id,
            name=name,
            date=holiday_date,
            year=holiday_date.year,
            holiday_type=holiday_type,
            created_by=created_by
        )
        
        self.db.add(holiday)
        self.db.commit()
        self.db.refresh(holiday)
        
        return holiday
    
    def delete(self, holiday_id: int, deleted_by: int = None) -> bool:
        """Delete a holiday."""
        holiday = self.get_by_id(holiday_id)
        if not holiday:
            return False
        
        holiday.soft_delete(deleted_by)
        self.db.commit()
        
        return True
