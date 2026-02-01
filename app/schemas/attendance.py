"""
Attendance schemas.
"""

from datetime import date, datetime, time

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema

# ============== Shift Schemas ==============

class ShiftBase(BaseSchema):
    """Shift base schema."""

    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=20)
    start_time: time
    end_time: time

    break_start: time | None = None
    break_end: time | None = None
    break_duration: int = 60

    working_hours: float = 8.0
    min_working_hours: float = 4.0

    grace_period_in: int = 15
    grace_period_out: int = 15

    ot_enabled: bool = False
    ot_start_after: int = 30

    weekends: list[str] = ["saturday", "sunday"]
    is_flexible: bool = False
    is_night_shift: bool = False


class ShiftCreate(ShiftBase):
    """Shift create schema."""

    company_id: int | None = None


class ShiftUpdate(BaseSchema):
    """Shift update schema."""

    name: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    break_start: time | None = None
    break_end: time | None = None
    break_duration: int | None = None
    working_hours: float | None = None
    min_working_hours: float | None = None
    grace_period_in: int | None = None
    grace_period_out: int | None = None
    ot_enabled: bool | None = None
    weekends: list[str] | None = None
    is_flexible: bool | None = None
    is_active: bool | None = None


class ShiftResponse(ShiftBase, TimestampSchema):
    """Shift response schema."""

    id: int
    company_id: int | None = None
    is_active: bool


# ============== Attendance Schemas ==============

class CheckInRequest(BaseSchema):
    """Check-in request schema."""

    work_mode: str = "office"  # office, wfh, remote
    latitude: str | None = None
    longitude: str | None = None
    address: str | None = None
    notes: str | None = None


class CheckOutRequest(BaseSchema):
    """Check-out request schema."""

    latitude: str | None = None
    longitude: str | None = None
    address: str | None = None
    notes: str | None = None


class AttendanceCreate(BaseSchema):
    """Manual attendance creation (admin)."""

    employee_id: int
    date: date
    shift_id: int | None = None
    check_in: datetime | None = None
    check_out: datetime | None = None
    work_mode: str = "office"
    status: str = "present"
    notes: str | None = None


class AttendanceUpdate(BaseSchema):
    """Attendance update schema."""

    check_in: datetime | None = None
    check_out: datetime | None = None
    work_mode: str | None = None
    status: str | None = None
    notes: str | None = None
    approval_status: str | None = None
    approval_notes: str | None = None


class AttendanceResponse(TimestampSchema):
    """Attendance response schema."""

    id: int
    employee_id: int
    date: date
    shift_id: int | None = None

    check_in: datetime | None = None
    check_out: datetime | None = None

    work_mode: str

    check_in_latitude: str | None = None
    check_in_longitude: str | None = None
    check_in_address: str | None = None
    check_out_latitude: str | None = None
    check_out_longitude: str | None = None
    check_out_address: str | None = None

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
    approval_status: str | None = None
    approved_by: int | None = None
    approval_notes: str | None = None

    notes: str | None = None

    # Employee info for display
    employee_code: str | None = None
    employee_name: str | None = None


class AttendanceListResponse(BaseSchema):
    """Minimal attendance for lists."""

    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    date: date
    check_in: datetime | None = None
    check_out: datetime | None = None
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
    requested_check_in: datetime | None = None
    requested_check_out: datetime | None = None
    requested_work_mode: str | None = None
    reason: str


class AttendanceRequestResponse(TimestampSchema):
    """Attendance request response."""

    id: int
    employee_id: int
    attendance_id: int | None = None
    date: date
    request_type: str
    requested_check_in: datetime | None = None
    requested_check_out: datetime | None = None
    requested_work_mode: str | None = None
    reason: str
    status: str
    approver_id: int | None = None
    approved_at: datetime | None = None
    approver_remarks: str | None = None

