"""
Payroll models.
Salary structure, payslips, and tax management.
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, JSON, Date, Float, Numeric
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel, AuditMixin


class PayrollStatus(enum.Enum):
    """Payslip status enum."""
    DRAFT = "draft"
    GENERATED = "generated"
    APPROVED = "approved"
    PAID = "paid"
    CANCELLED = "cancelled"


class SalaryStructure(BaseModel, AuditMixin):
    """
    Salary structure for an employee.
    """
    
    __tablename__ = "salary_structures"
    
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    
    # Basic Components
    basic = Column(Numeric(12, 2), default=0)
    hra = Column(Numeric(12, 2), default=0)  # House Rent Allowance
    da = Column(Numeric(12, 2), default=0)  # Dearness Allowance
    
    # Allowances
    transport_allowance = Column(Numeric(12, 2), default=0)
    medical_allowance = Column(Numeric(12, 2), default=0)
    special_allowance = Column(Numeric(12, 2), default=0)
    other_allowances = Column(JSON, nullable=True)  # Custom allowances
    
    # Deductions
    pf_employee = Column(Numeric(12, 2), default=0)  # Provident Fund
    pf_employer = Column(Numeric(12, 2), default=0)
    esi_employee = Column(Numeric(12, 2), default=0)  # Employee State Insurance
    esi_employer = Column(Numeric(12, 2), default=0)
    professional_tax = Column(Numeric(12, 2), default=0)
    tds = Column(Numeric(12, 2), default=0)  # Tax Deducted at Source
    other_deductions = Column(JSON, nullable=True)  # Custom deductions
    
    # Calculated
    gross_salary = Column(Numeric(12, 2), default=0)
    net_salary = Column(Numeric(12, 2), default=0)
    ctc = Column(Numeric(12, 2), default=0)  # Cost to Company
    
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    
    # Relationships
    employee = relationship("Employee", backref="salary_structures")


class PaySlip(BaseModel, AuditMixin):
    """
    Monthly payslip for an employee.
    """
    
    __tablename__ = "payslips"
    
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    salary_structure_id = Column(Integer, ForeignKey("salary_structures.id"), nullable=True)
    
    # Period
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    pay_period_start = Column(Date, nullable=True)
    pay_period_end = Column(Date, nullable=True)
    
    # Working Days
    total_days = Column(Integer, default=0)
    working_days = Column(Integer, default=0)
    present_days = Column(Float, default=0)
    leave_days = Column(Float, default=0)
    lop_days = Column(Float, default=0)  # Loss of Pay
    
    # Earnings
    basic = Column(Numeric(12, 2), default=0)
    hra = Column(Numeric(12, 2), default=0)
    da = Column(Numeric(12, 2), default=0)
    transport = Column(Numeric(12, 2), default=0)
    medical = Column(Numeric(12, 2), default=0)
    special = Column(Numeric(12, 2), default=0)
    overtime = Column(Numeric(12, 2), default=0)
    bonus = Column(Numeric(12, 2), default=0)
    other_earnings = Column(JSON, nullable=True)
    gross = Column(Numeric(12, 2), default=0)
    
    # Deductions
    pf = Column(Numeric(12, 2), default=0)
    esi = Column(Numeric(12, 2), default=0)
    professional_tax = Column(Numeric(12, 2), default=0)
    tds = Column(Numeric(12, 2), default=0)
    lop_deduction = Column(Numeric(12, 2), default=0)
    other_deductions = Column(JSON, nullable=True)
    total_deductions = Column(Numeric(12, 2), default=0)
    
    # Net
    net = Column(Numeric(12, 2), default=0)
    
    # Status
    status = Column(String(20), default=PayrollStatus.DRAFT.value)
    
    # Payment
    payment_date = Column(Date, nullable=True)
    payment_method = Column(String(50), nullable=True)
    bank_reference = Column(String(100), nullable=True)
    
    # Approval
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(Date, nullable=True)
    
    # Relationships
    employee = relationship("Employee", backref="payslips")


class TaxSlab(BaseModel, AuditMixin):
    """
    Tax slab configuration.
    """
    
    __tablename__ = "tax_slabs"
    
    financial_year = Column(String(10), nullable=False)  # e.g., "2025-26"
    regime = Column(String(20), default="new")  # old, new
    
    min_income = Column(Numeric(12, 2), nullable=False)
    max_income = Column(Numeric(12, 2), nullable=True)  # null for no upper limit
    rate = Column(Float, nullable=False)  # percentage
    
    description = Column(String(255), nullable=True)


class SalaryRevision(BaseModel, AuditMixin):
    """
    Salary revision history.
    """
    
    __tablename__ = "salary_revisions"
    
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    
    revision_type = Column(String(50), nullable=False)  # increment, promotion, correction
    effective_date = Column(Date, nullable=False)
    
    previous_gross = Column(Numeric(12, 2), nullable=True)
    new_gross = Column(Numeric(12, 2), nullable=True)
    previous_ctc = Column(Numeric(12, 2), nullable=True)
    new_ctc = Column(Numeric(12, 2), nullable=True)
    
    increment_percentage = Column(Float, nullable=True)
    
    reason = Column(Text, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(Date, nullable=True)
    
    # Relationships
    employee = relationship("Employee", backref="salary_revisions")
