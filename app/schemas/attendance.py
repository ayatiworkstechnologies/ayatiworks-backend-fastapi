"""
Attendance schemas.
"""

from typing import Optional, List
from datetime import date, datetime, time
from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema, TimestampSchema


# ============== Shift Schemas ==============

class ShiftBase(BaseSchema):
    """Shift base schema."""
    
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=20)
    start_time: time
    end_time: time
    
    break_start: Optional[time] = None
    break_end: Optional[time] = None
    break_duration: int = 60
    
    working_hours: float = 8.0
    min_working_hours: float = 4.0
    
    grace_period_in: int = 15
    grace_period_out: int = 15
    
    ot_enabled: bool = False
    ot_start_after: int = 30
    
    weekends: List[str] = ["saturday", "sunday"]
    is_flexible: bool = False
    is_night_shift: bool = False


class ShiftCreate(ShiftBase):
    """Shift create schema."""
    
    company_id: Optional[int] = None


class ShiftUpdate(BaseSchema):
    """Shift update schema."""
    
    name: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    break_start: Optional[time] = None
    break_end: Optional[time] = None
    break_duration: Optional[int] = None
    working_hours: Optional[float] = None
    min_working_hours: Optional[float] = None
    grace_period_in: Optional[int] = None
    grace_period_out: Optional[int] = None
    ot_enabled: Optional[bool] = None
    weekends: Optional[List[str]] = None
    is_flexible: Optional[bool] = None
    is_active: Optional[bool] = None


class ShiftResponse(ShiftBase, TimestampSchema):
    """Shift response schema."""
    
    id: int
    company_id: Optional[int] = None
    is_active: bool


# ============== Attendance Schemas ==============

class CheckInRequest(BaseSchema):
    """Check-in request schema."""
    
    work_mode: str = "office"  # office, wfh, remote
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class CheckOutRequest(BaseSchema):
    """Check-out request schema."""
    
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class AttendanceCreate(BaseSchema):
    """Manual attendance creation (admin)."""
    
    employee_id: int
    date: date
    shift_id: Optional[int] = None
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    work_mode: str = "office"
    status: str = "present"
    notes: Optional[str] = None


class AttendanceUpdate(BaseSchema):
    """Attendance update schema."""
    
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    work_mode: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    approval_status: Optional[str] = None
    approval_notes: Optional[str] = None


class AttendanceResponse(TimestampSchema):
    """Attendance response schema."""
    
    id: int
    employee_id: int
    date: date
    shift_id: Optional[int] = None
    
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    
    work_mode: str
    
    check_in_latitude: Optional[str] = None
    check_in_longitude: Optional[str] = None
    check_in_address: Optional[str] = None
    check_out_latitude: Optional[str] = None
    check_out_longitude: Optional[str] = None
    check_out_address: Optional[str] = None
    
    status: str
    working_hours: float
    overtime_hours: float
    late_minutes: int
    early_leave_minutes: int
    
    is_late: bool
    is_early_leave: bool
    is_half_day: bool
    is_overtime: bool
    
    requires_approval: bool
    approval_status: Optional[str] = None
    approved_by: Optional[int] = None
    approval_notes: Optional[str] = None
    
    notes: Optional[str] = None
    
    # Employee info for display
    employee_code: Optional[str] = None
    employee_name: Optional[str] = None


class AttendanceListResponse(BaseSchema):
    """Minimal attendance for lists."""
    
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    work_mode: str
    status: str
    working_hours: float
    is_late: bool


class AttendanceSummary(BaseSchema):
    """Attendance summary for dashboard."""
    
    total_days: int
    present_days: int
    absent_days: int
    late_days: int
    wfh_days: int
    half_days: int
    total_working_hours: float
    total_overtime_hours: float


class AttendanceStatsResponse(BaseSchema):
    """Overall attendance statistics for admin dashboard."""
    
    total_active_employees: int
    total_present: int
    total_absent: int
    total_late: int
    total_wfh: int
    attendance_rate: float


# ============== Attendance Request Schemas ==============

class AttendanceRequestCreate(BaseSchema):
    """Attendance regularization/request."""
    
    date: date
    request_type: str  # regularization, correction, wfh_request
    requested_check_in: Optional[datetime] = None
    requested_check_out: Optional[datetime] = None
    requested_work_mode: Optional[str] = None
    reason: str


class AttendanceRequestResponse(TimestampSchema):
    """Attendance request response."""
    
    id: int
    employee_id: int
    attendance_id: Optional[int] = None
    date: date
    request_type: str
    requested_check_in: Optional[datetime] = None
    requested_check_out: Optional[datetime] = None
    requested_work_mode: Optional[str] = None
    reason: str
    status: str
    approver_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    approver_remarks: Optional[str] = None
