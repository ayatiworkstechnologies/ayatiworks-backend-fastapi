"""
Leave and holiday schemas.
"""

from datetime import date as date_type

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema

# ============== Leave Type Schemas ==============

class LeaveTypeBase(BaseSchema):
    """Leave type base schema."""

    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=20)
    description: str | None = None

    days_allowed: int = 0
    max_days_at_once: int | None = None
    min_days_notice: int = 0

    carry_forward: bool = False
    max_carry_forward: int = 0
    carry_forward_expiry_months: int = 3

    encashable: bool = False
    max_encashment: int = 0

    requires_approval: bool = True
    requires_document: bool = False
    applicable_after_days: int = 0
    applicable_gender: str | None = None

    prorate: bool = True
    half_day_allowed: bool = True
    color: str = "#3B82F6"


class LeaveTypeCreate(LeaveTypeBase):
    """Leave type create schema."""

    company_id: int | None = None


class LeaveTypeUpdate(BaseSchema):
    """Leave type update schema."""

    name: str | None = None
    description: str | None = None
    days_allowed: int | None = None
    max_days_at_once: int | None = None
    min_days_notice: int | None = None
    carry_forward: bool | None = None
    max_carry_forward: int | None = None
    encashable: bool | None = None
    max_encashment: int | None = None
    requires_approval: bool | None = None
    requires_document: bool | None = None
    half_day_allowed: bool | None = None
    color: str | None = None
    is_active: bool | None = None


class LeaveTypeResponse(LeaveTypeBase, TimestampSchema):
    """Leave type response schema."""

    id: int
    company_id: int | None = None
    is_active: bool


# ============== Leave Balance Schemas ==============

class LeaveBalanceResponse(BaseSchema):
    """Leave balance response."""

    id: int | None = None
    employee_id: int | None = None
    leave_type_id: int
    leave_type_name: str
    leave_type_code: str
    year: int
    allocated: float
    used: float
    pending: float
    carry_forward: float
    encashed: float
    available: float


class LeaveBalanceUpdate(BaseSchema):
    """Update leave balance (admin)."""

    allocated: float | None = None
    carry_forward: float | None = None


# ============== Leave Request Schemas ==============

class LeaveCreate(BaseSchema):
    """Leave application schema."""

    leave_type_id: int
    from_date: date_type
    to_date: date_type
    is_half_day: bool = False
    half_day_type: str | None = None  # first_half, second_half
    reason: str = Field(..., min_length=5)
    contact_during_leave: str | None = None


class LeaveUpdate(BaseSchema):
    """Leave update schema (before approval)."""

    from_date: date_type | None = None
    to_date: date_type | None = None
    reason: str | None = None
    contact_during_leave: str | None = None


class LeaveApprovalRequest(BaseSchema):
    """Leave approval/rejection request."""

    status: str  # approved, rejected, partially_approved
    remarks: str | None = None
    approved_days: float | None = None  # For partial approval


class LeaveResponse(TimestampSchema):
    """Leave response schema."""

    id: int
    employee_id: int
    leave_type_id: int

    from_date: date_type
    to_date: date_type
    days: float

    is_half_day: bool
    half_day_type: str | None = None

    reason: str
    contact_during_leave: str | None = None
    document_path: str | None = None

    status: str

    approver_id: int | None = None
    approved_at: date_type | None = None
    approver_remarks: str | None = None

    cancelled_by: int | None = None
    cancelled_at: date_type | None = None
    cancellation_reason: str | None = None

    # Display info
    leave_type_name: str | None = None
    leave_type_color: str | None = None
    employee_name: str | None = None
    employee_code: str | None = None
    approver_name: str | None = None


class LeaveListResponse(BaseSchema):
    """Minimal leave info for lists."""

    id: int
    employee_id: int
    employee_name: str
    leave_type_name: str
    leave_type_color: str
    from_date: date_type
    to_date: date_type
    days: float
    status: str


class LeaveCancelRequest(BaseSchema):
    """Leave cancellation request."""

    reason: str


# ============== Holiday Schemas ==============

class HolidayBase(BaseSchema):
    """Holiday base schema."""

    name: str = Field(..., min_length=2, max_length=100)
    date: date_type
    holiday_type: str = "public"  # public, restricted, optional
    is_optional: bool = False
    description: str | None = None


class HolidayCreate(HolidayBase):
    """Holiday create schema."""

    company_id: int | None = None
    branch_id: int | None = None
    applicable_departments: list[int] | None = None
    applicable_designations: list[int] | None = None


class HolidayUpdate(BaseSchema):
    """Holiday update schema."""

    name: str | None = None
    date: date_type | None = None
    holiday_type: str | None = None
    is_optional: bool | None = None
    description: str | None = None
    applicable_departments: list[int] | None = None
    applicable_designations: list[int] | None = None
    is_active: bool | None = None


class HolidayResponse(HolidayBase, TimestampSchema):
    """Holiday response schema."""

    id: int
    company_id: int | None = None
    branch_id: int | None = None
    year: int
    applicable_departments: list[int] | None = None
    applicable_designations: list[int] | None = None
    is_active: bool

