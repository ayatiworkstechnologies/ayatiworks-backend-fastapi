"""
Leave and Holiday models.
Leave types, leave requests, leave balance, and holiday management.
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, JSON, Date, Float
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel, AuditMixin


class LeaveStatus(enum.Enum):
    """Leave request status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    PARTIALLY_APPROVED = "partially_approved"


class LeaveType(BaseModel, AuditMixin):
    """
    Leave type configuration.
    """
    
    __tablename__ = "leave_types"
    
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Allocation
    days_allowed = Column(Integer, default=0)  # Per year
    max_days_at_once = Column(Integer, nullable=True)  # Max days in single application
    min_days_notice = Column(Integer, default=0)  # Advance notice required
    
    # Carry Forward
    carry_forward = Column(Boolean, default=False)
    max_carry_forward = Column(Integer, default=0)
    carry_forward_expiry_months = Column(Integer, default=3)
    
    # Encashment
    encashable = Column(Boolean, default=False)
    max_encashment = Column(Integer, default=0)
    
    # Rules
    requires_approval = Column(Boolean, default=True)
    requires_document = Column(Boolean, default=False)
    applicable_after_days = Column(Integer, default=0)  # Days after joining
    applicable_gender = Column(String(20), nullable=True)  # male, female, all
    
    # Prorate for new joiners
    prorate = Column(Boolean, default=True)
    
    # Half-day allowed
    half_day_allowed = Column(Boolean, default=True)
    
    # Color for calendar
    color = Column(String(10), default="#3B82F6")
    
    # Relationships
    leaves = relationship("Leave", back_populates="leave_type")


class LeaveBalance(BaseModel, AuditMixin):
    """
    Employee leave balance tracking.
    """
    
    __tablename__ = "leave_balances"
    
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False)
    year = Column(Integer, nullable=False)
    
    # Balance
    allocated = Column(Float, default=0)
    used = Column(Float, default=0)
    pending = Column(Float, default=0)  # Approved but not yet taken
    carry_forward = Column(Float, default=0)
    
    # Encashment
    encashed = Column(Float, default=0)
    
    @property
    def available(self) -> float:
        """Calculate available balance."""
        return self.allocated + self.carry_forward - self.used - self.pending - self.encashed
    
    # Relationships
    leave_type = relationship("LeaveType")


class Leave(BaseModel, AuditMixin):
    """
    Leave request model.
    """
    
    __tablename__ = "leaves"
    
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    
    # Duration
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False)
    days = Column(Float, nullable=False)  # Total days (supports half-days)
    
    # Half-day specification
    is_half_day = Column(Boolean, default=False)
    half_day_type = Column(String(20), nullable=True)  # first_half, second_half
    
    # Details
    reason = Column(Text, nullable=False)
    contact_during_leave = Column(String(100), nullable=True)
    document_path = Column(String(500), nullable=True)
    
    # Status
    status = Column(String(20), default=LeaveStatus.PENDING.value)
    
    # Approval Chain
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(Date, nullable=True)
    approver_remarks = Column(Text, nullable=True)
    
    # Cancellation
    cancelled_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    cancelled_at = Column(Date, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    # Relationships
    leave_type = relationship("LeaveType", back_populates="leaves")
    employee = relationship("Employee", backref="leaves")


class Holiday(BaseModel, AuditMixin):
    """
    Holiday calendar model.
    """
    
    __tablename__ = "holidays"
    
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    
    name = Column(String(100), nullable=False)
    date = Column(Date, nullable=False, index=True)
    year = Column(Integer, nullable=False)
    
    # Type
    holiday_type = Column(String(50), default="public")  # public, restricted, optional
    is_optional = Column(Boolean, default=False)
    
    # Restrictions
    applicable_departments = Column(JSON, nullable=True)  # List of department IDs
    applicable_designations = Column(JSON, nullable=True)  # List of designation IDs
    
    description = Column(Text, nullable=True)


class LeaveEncashment(BaseModel, AuditMixin):
    """
    Leave encashment requests.
    """
    
    __tablename__ = "leave_encashments"
    
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    year = Column(Integer, nullable=False)
    
    days = Column(Float, nullable=False)
    amount_per_day = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=True)
    
    status = Column(String(20), default="pending")
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(Date, nullable=True)
    paid_at = Column(Date, nullable=True)
    remarks = Column(Text, nullable=True)
