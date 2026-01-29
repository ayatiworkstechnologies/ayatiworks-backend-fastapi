"""
Attendance and Shift models.
Supports Office, WFH, and Remote attendance with geo-location.
"""

from datetime import datetime, date, time
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, JSON, Date, Time, DateTime, Float
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel, AuditMixin


class AttendanceStatus(enum.Enum):
    """Attendance status enum."""
    PRESENT = "present"
    ABSENT = "absent"
    HALF_DAY = "half_day"
    LATE = "late"
    EARLY_LEAVE = "early_leave"
    ON_LEAVE = "on_leave"
    HOLIDAY = "holiday"
    WEEKEND = "weekend"


class Shift(BaseModel, AuditMixin):
    """
    Shift model for different working schedules.
    """
    
    __tablename__ = "shifts"
    
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False, index=True)
    
    # Timing
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    break_start = Column(Time, nullable=True)
    break_end = Column(Time, nullable=True)
    break_duration = Column(Integer, default=60)  # minutes
    
    # Working Hours
    working_hours = Column(Float, default=8.0)
    min_working_hours = Column(Float, default=4.0)  # For half-day calculation
    
    # Grace Period
    grace_period_in = Column(Integer, default=15)  # minutes
    grace_period_out = Column(Integer, default=15)  # minutes
    
    # Overtime
    ot_enabled = Column(Boolean, default=False)
    ot_start_after = Column(Integer, default=30)  # minutes after shift end
    
    # Weekend Configuration
    weekends = Column(JSON, default=["saturday", "sunday"])  # Days that are off
    
    # Settings
    is_flexible = Column(Boolean, default=False)
    is_night_shift = Column(Boolean, default=False)
    
    # Relationships
    employees = relationship("Employee", backref="shift")
    attendances = relationship("Attendance", back_populates="shift")


class Attendance(BaseModel, AuditMixin):
    """
    Attendance record model.
    """
    
    __tablename__ = "attendances"
    
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True)
    
    # Check-in/out
    check_in = Column(DateTime, nullable=True)
    check_out = Column(DateTime, nullable=True)
    
    # Work Mode
    work_mode = Column(String(20), default="office")  # office, wfh, remote
    
    # Location (for geo-fencing)
    check_in_latitude = Column(String(20), nullable=True)
    check_in_longitude = Column(String(20), nullable=True)
    check_in_address = Column(String(255), nullable=True)
    check_out_latitude = Column(String(20), nullable=True)
    check_out_longitude = Column(String(20), nullable=True)
    check_out_address = Column(String(255), nullable=True)
    
    # Device Info
    check_in_device = Column(String(255), nullable=True)
    check_out_device = Column(String(255), nullable=True)
    check_in_ip = Column(String(50), nullable=True)
    check_out_ip = Column(String(50), nullable=True)
    
    # Calculated Fields
    status = Column(String(20), default=AttendanceStatus.PRESENT.value)
    working_hours = Column(Float, default=0.0)
    overtime_hours = Column(Float, default=0.0)
    late_minutes = Column(Integer, default=0)
    early_leave_minutes = Column(Integer, default=0)
    
    # Break Tracking
    breaks = Column(JSON, nullable=True)  # [{start, end, duration}]
    total_break_duration = Column(Integer, default=0)  # minutes
    
    # Status Flags
    is_late = Column(Boolean, default=False)
    is_early_leave = Column(Boolean, default=False)
    is_half_day = Column(Boolean, default=False)
    is_overtime = Column(Boolean, default=False)
    
    # Approval
    requires_approval = Column(Boolean, default=False)
    approval_status = Column(String(20), nullable=True)  # pending, approved, rejected
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_notes = Column(Text, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Relationships
    shift = relationship("Shift", back_populates="attendances")
    employee = relationship("Employee", backref="attendances")
    
    def calculate_working_hours(self):
        """Calculate total working hours."""
        if self.check_in and self.check_out:
            delta = self.check_out - self.check_in
            hours = delta.total_seconds() / 3600
            # Subtract break time
            hours -= (self.total_break_duration / 60)
            self.working_hours = round(max(0, hours), 2)
        return self.working_hours


class AttendanceRequest(BaseModel, AuditMixin):
    """
    Attendance correction/regularization requests.
    """
    
    __tablename__ = "attendance_requests"
    
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    attendance_id = Column(Integer, ForeignKey("attendances.id"), nullable=True)
    date = Column(Date, nullable=False)
    
    request_type = Column(String(50), nullable=False)  # regularization, correction, wfh_request
    
    # Requested Changes
    requested_check_in = Column(DateTime, nullable=True)
    requested_check_out = Column(DateTime, nullable=True)
    requested_work_mode = Column(String(20), nullable=True)
    
    reason = Column(Text, nullable=False)
    supporting_document = Column(String(500), nullable=True)
    
    # Approval
    status = Column(String(20), default="pending")  # pending, approved, rejected
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approver_remarks = Column(Text, nullable=True)
