"""
Leave and holiday schemas.
"""

from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema, TimestampSchema


# ============== Leave Type Schemas ==============

class LeaveTypeBase(BaseSchema):
    """Leave type base schema."""
    
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=20)
    description: Optional[str] = None
    
    days_allowed: int = 0
    max_days_at_once: Optional[int] = None
    min_days_notice: int = 0
    
    carry_forward: bool = False
    max_carry_forward: int = 0
    carry_forward_expiry_months: int = 3
    
    encashable: bool = False
    max_encashment: int = 0
    
    requires_approval: bool = True
    requires_document: bool = False
    applicable_after_days: int = 0
    applicable_gender: Optional[str] = None
    
    prorate: bool = True
    half_day_allowed: bool = True
    color: str = "#3B82F6"


class LeaveTypeCreate(LeaveTypeBase):
    """Leave type create schema."""
    
    company_id: Optional[int] = None


class LeaveTypeUpdate(BaseSchema):
    """Leave type update schema."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    days_allowed: Optional[int] = None
    max_days_at_once: Optional[int] = None
    min_days_notice: Optional[int] = None
    carry_forward: Optional[bool] = None
    max_carry_forward: Optional[int] = None
    encashable: Optional[bool] = None
    max_encashment: Optional[int] = None
    requires_approval: Optional[bool] = None
    requires_document: Optional[bool] = None
    half_day_allowed: Optional[bool] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


class LeaveTypeResponse(LeaveTypeBase, TimestampSchema):
    """Leave type response schema."""
    
    id: int
    company_id: Optional[int] = None
    is_active: bool


# ============== Leave Balance Schemas ==============

class LeaveBalanceResponse(BaseSchema):
    """Leave balance response."""
    
    id: Optional[int] = None
    employee_id: Optional[int] = None
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
    
    allocated: Optional[float] = None
    carry_forward: Optional[float] = None


# ============== Leave Request Schemas ==============

class LeaveCreate(BaseSchema):
    """Leave application schema."""
    
    leave_type_id: int
    from_date: date
    to_date: date
    is_half_day: bool = False
    half_day_type: Optional[str] = None  # first_half, second_half
    reason: str = Field(..., min_length=5)
    contact_during_leave: Optional[str] = None


class LeaveUpdate(BaseSchema):
    """Leave update schema (before approval)."""
    
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    reason: Optional[str] = None
    contact_during_leave: Optional[str] = None


class LeaveApprovalRequest(BaseSchema):
    """Leave approval/rejection request."""
    
    status: str  # approved, rejected, partially_approved
    remarks: Optional[str] = None
    approved_days: Optional[float] = None  # For partial approval


class LeaveResponse(TimestampSchema):
    """Leave response schema."""
    
    id: int
    employee_id: int
    leave_type_id: int
    
    from_date: date
    to_date: date
    days: float
    
    is_half_day: bool
    half_day_type: Optional[str] = None
    
    reason: str
    contact_during_leave: Optional[str] = None
    document_path: Optional[str] = None
    
    status: str
    
    approver_id: Optional[int] = None
    approved_at: Optional[date] = None
    approver_remarks: Optional[str] = None
    
    cancelled_by: Optional[int] = None
    cancelled_at: Optional[date] = None
    cancellation_reason: Optional[str] = None
    
    # Display info
    leave_type_name: Optional[str] = None
    leave_type_color: Optional[str] = None
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    approver_name: Optional[str] = None


class LeaveListResponse(BaseSchema):
    """Minimal leave info for lists."""
    
    id: int
    employee_id: int
    employee_name: str
    leave_type_name: str
    leave_type_color: str
    from_date: date
    to_date: date
    days: float
    status: str


class LeaveCancelRequest(BaseSchema):
    """Leave cancellation request."""
    
    reason: str


# ============== Holiday Schemas ==============

class HolidayBase(BaseSchema):
    """Holiday base schema."""
    
    name: str = Field(..., min_length=2, max_length=100)
    date: date
    holiday_type: str = "public"  # public, restricted, optional
    is_optional: bool = False
    description: Optional[str] = None


class HolidayCreate(HolidayBase):
    """Holiday create schema."""
    
    company_id: Optional[int] = None
    branch_id: Optional[int] = None
    applicable_departments: Optional[List[int]] = None
    applicable_designations: Optional[List[int]] = None


class HolidayUpdate(BaseSchema):
    """Holiday update schema."""
    
    name: Optional[str] = None
    date: Optional[date] = None
    holiday_type: Optional[str] = None
    is_optional: Optional[bool] = None
    description: Optional[str] = None
    applicable_departments: Optional[List[int]] = None
    applicable_designations: Optional[List[int]] = None
    is_active: Optional[bool] = None


class HolidayResponse(HolidayBase, TimestampSchema):
    """Holiday response schema."""
    
    id: int
    company_id: Optional[int] = None
    branch_id: Optional[int] = None
    year: int
    applicable_departments: Optional[List[int]] = None
    applicable_designations: Optional[List[int]] = None
    is_active: bool
