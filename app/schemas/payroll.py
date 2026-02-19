"""
Payroll Schemas.
Salary structures, payslips, and payroll generation.
"""

from datetime import date
from typing import Any

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema, TimestampSchema


# ============ Salary Structure ============

class SalaryStructureCreate(BaseSchema):
    """Create salary structure for an employee."""

    employee_id: int

    # Basic Components
    basic: float = 0
    hra: float = 0
    da: float = 0

    # Allowances
    transport_allowance: float = 0
    medical_allowance: float = 0
    special_allowance: float = 0
    other_allowances: dict[str, Any] | None = None

    # Deductions
    pf_employee: float = 0
    pf_employer: float = 0
    esi_employee: float = 0
    esi_employer: float = 0
    professional_tax: float = 0
    tds: float = 0
    other_deductions: dict[str, Any] | None = None

    effective_from: date = Field(default_factory=date.today)
    effective_to: date | None = None

    @field_validator('employee_id', mode='before')
    @classmethod
    def validate_employee_id(cls, v):
        if not v:
            raise ValueError("employee_id is required")
        return v


class SalaryStructureUpdate(BaseSchema):
    """Update salary structure."""

    basic: float | None = None
    hra: float | None = None
    da: float | None = None
    transport_allowance: float | None = None
    medical_allowance: float | None = None
    special_allowance: float | None = None
    other_allowances: dict[str, Any] | None = None

    pf_employee: float | None = None
    pf_employer: float | None = None
    esi_employee: float | None = None
    esi_employer: float | None = None
    professional_tax: float | None = None
    tds: float | None = None
    other_deductions: dict[str, Any] | None = None

    effective_from: date | None = None
    effective_to: date | None = None


class SalaryStructureResponse(TimestampSchema):
    """Salary structure response."""

    id: int
    employee_id: int

    # Employee info (populated in API)
    employee_name: str | None = None
    employee_code: str | None = None

    # Components
    basic: float = 0
    hra: float = 0
    da: float = 0
    transport_allowance: float = 0
    medical_allowance: float = 0
    special_allowance: float = 0
    other_allowances: dict[str, Any] | None = None

    # Deductions
    pf_employee: float = 0
    pf_employer: float = 0
    esi_employee: float = 0
    esi_employer: float = 0
    professional_tax: float = 0
    tds: float = 0
    other_deductions: dict[str, Any] | None = None

    # Totals
    gross_salary: float = 0
    net_salary: float = 0
    ctc: float = 0

    effective_from: date | None = None
    effective_to: date | None = None


# ============ Payslip ============

class PaySlipResponse(TimestampSchema):
    """Payslip response."""

    id: int
    employee_id: int

    # Employee info
    employee_name: str | None = None
    employee_code: str | None = None
    department_name: str | None = None

    # Period
    month: int
    year: int
    pay_period_start: date | None = None
    pay_period_end: date | None = None

    # Working days
    total_days: int = 0
    working_days: int = 0
    present_days: float = 0
    leave_days: float = 0
    lop_days: float = 0

    # Earnings
    basic: float = 0
    hra: float = 0
    da: float = 0
    transport: float = 0
    medical: float = 0
    special: float = 0
    overtime: float = 0
    bonus: float = 0
    other_earnings: dict[str, Any] | None = None
    gross: float = 0

    # Deductions
    pf: float = 0
    esi: float = 0
    professional_tax: float = 0
    tds: float = 0
    lop_deduction: float = 0
    other_deductions: dict[str, Any] | None = None
    total_deductions: float = 0

    # Net
    net: float = 0

    # Status & Payment
    status: str = "draft"
    payment_date: date | None = None
    payment_method: str | None = None
    bank_reference: str | None = None


# ============ Payroll Generation ============

class PayrollGenerateRequest(BaseSchema):
    """Request to generate payslips for a month."""

    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2020, le=2030)
    employee_ids: list[int] | None = None  # None = all active employees


class PaySlipApprove(BaseSchema):
    """Approve/pay a payslip."""

    status: str = "approved"  # approved, paid
    payment_date: date | None = None
    payment_method: str | None = None
    bank_reference: str | None = None


# ============ Summary ============

class PayrollSummary(BaseSchema):
    """Payroll dashboard summary."""

    total_employees_with_salary: int = 0
    total_payslips: int = 0
    pending_payslips: int = 0
    approved_payslips: int = 0
    paid_payslips: int = 0
    total_gross: float = 0
    total_net: float = 0
    total_deductions: float = 0
    current_month: int = 0
    current_year: int = 0
