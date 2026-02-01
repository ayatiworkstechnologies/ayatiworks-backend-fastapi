"""
Employee schemas.
"""

from datetime import date
from typing import Any

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import BaseSchema, TimestampSchema


def empty_str_to_none(v: Any) -> Any:
    """Convert empty strings to None for optional fields."""
    if v == "" or v == "":
        return None
    return v


# ============== Employee Schemas ==============

class EmployeeBase(BaseSchema):
    """Employee base schema."""

    # Personal
    date_of_birth: date | None = None
    gender: str | None = None
    blood_group: str | None = None
    marital_status: str | None = None
    nationality: str | None = None

    # Contact
    personal_email: EmailStr | None = None
    personal_phone: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    emergency_contact_relation: str | None = None

    # Address
    current_address: str | None = None
    permanent_address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None


class EmployeeCreate(EmployeeBase):
    """Employee create schema."""

    # Required: either user_id or new user details
    user_id: int | None = None

    # New user creation (if user_id not provided)
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    password: str | None = None

    # Organization
    company_id: int | None = None
    branch_id: int | None = None
    department_id: int | None = None
    designation_id: int | None = None
    manager_id: int | None = None
    role_id: int | None = None

    # Employment
    joining_date: date = Field(default_factory=date.today)
    employment_type: str = "full_time"
    work_mode: str = "office"
    shift_id: int | None = None

    # Validators to convert empty strings to None
    @field_validator('user_id', 'company_id', 'branch_id', 'department_id', 'designation_id', 'manager_id', 'shift_id', 'role_id', mode='before')
    @classmethod
    def validate_int_fields(cls, v):
        if v == '' or v is None:
            return None
        return v

    # Bank
    bank_name: str | None = None
    bank_account_number: str | None = None
    bank_ifsc_code: str | None = None

    # Documents
    pan_number: str | None = None
    aadhar_number: str | None = None


class EmployeeUpdate(EmployeeBase):
    """Employee update schema."""

    department_id: int | None = None
    designation_id: int | None = None
    manager_id: int | None = None
    shift_id: int | None = None

    # Validators to convert empty strings to None
    @field_validator('department_id', 'designation_id', 'manager_id', 'shift_id', mode='before')
    @classmethod
    def validate_int_fields(cls, v):
        if v == '' or v is None:
            return None
        return v

    employment_type: str | None = None
    employment_status: str | None = None
    work_mode: str | None = None

    probation_end_date: date | None = None
    confirmation_date: date | None = None

    # Bank
    bank_name: str | None = None
    bank_account_number: str | None = None
    bank_ifsc_code: str | None = None
    bank_branch: str | None = None

    # Documents
    pan_number: str | None = None
    aadhar_number: str | None = None
    passport_number: str | None = None
    passport_expiry: date | None = None

    # Skills
    skills: list[str] | None = None
    notes: str | None = None

    is_active: bool | None = None


class EmployeeTeamResponse(BaseSchema):
    """Simplified team info for employee profile."""
    id: int
    name: str
    code: str
    team_type: str | None = None
    role: str | None = None  # Role in the team
    joined_date: date | None = None


class EmployeeResponse(EmployeeBase, TimestampSchema):
    """Employee response schema."""

    id: int
    user_id: int
    employee_code: str  # AW0001 format

    # Organization
    company_id: int | None = None
    branch_id: int | None = None
    department_id: int | None = None
    designation_id: int | None = None
    manager_id: int | None = None

    # Employment
    joining_date: date
    probation_end_date: date | None = None
    confirmation_date: date | None = None
    employment_type: str
    employment_status: str
    work_mode: str
    shift_id: int | None = None

    is_active: bool

    # User info (nested)
    user: dict | None = None

    # Department/Designation names (for display)
    department_name: str | None = None
    designation_name: str | None = None
    manager_name: str | None = None

    # Teams
    teams: list[EmployeeTeamResponse] | None = None


class EmployeeListResponse(BaseSchema):
    """Minimal employee info for lists."""

    id: int
    user_id: int
    employee_code: str
    first_name: str
    last_name: str | None = None
    email: str
    avatar: str | None = None
    department_name: str | None = None
    designation_name: str | None = None
    employment_status: str
    is_active: bool

    @property
    def full_name(self) -> str:
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name


# ============== Employee Document Schemas ==============

class EmployeeDocumentCreate(BaseSchema):
    """Employee document upload schema."""

    document_type: str
    document_name: str
    expiry_date: date | None = None
    notes: str | None = None


class EmployeeDocumentResponse(TimestampSchema):
    """Employee document response."""

    id: int
    employee_id: int
    document_type: str
    document_name: str
    file_path: str
    file_size: int | None = None
    mime_type: str | None = None
    expiry_date: date | None = None
    is_verified: bool
    verified_by: int | None = None
    verified_at: date | None = None
    notes: str | None = None

