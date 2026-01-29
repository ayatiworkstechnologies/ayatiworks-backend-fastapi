"""
Employee schemas.
"""

from typing import Optional, List, Any
from datetime import date
from pydantic import BaseModel, EmailStr, Field, field_validator

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
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    marital_status: Optional[str] = None
    nationality: Optional[str] = None
    
    # Contact
    personal_email: Optional[EmailStr] = None
    personal_phone: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    
    # Address
    current_address: Optional[str] = None
    permanent_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None


class EmployeeCreate(EmployeeBase):
    """Employee create schema."""
    
    # Required: either user_id or new user details
    user_id: Optional[int] = None
    
    # New user creation (if user_id not provided)
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None
    
    # Organization
    company_id: Optional[int] = None
    branch_id: Optional[int] = None
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    manager_id: Optional[int] = None
    role_id: Optional[int] = None
    
    # Employment
    joining_date: date = Field(default_factory=date.today)
    employment_type: str = "full_time"
    work_mode: str = "office"
    shift_id: Optional[int] = None
    
    # Validators to convert empty strings to None
    @field_validator('user_id', 'company_id', 'branch_id', 'department_id', 'designation_id', 'manager_id', 'shift_id', 'role_id', mode='before')
    @classmethod
    def validate_int_fields(cls, v):
        if v == '' or v is None:
            return None
        return v
    
    # Bank
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc_code: Optional[str] = None
    
    # Documents
    pan_number: Optional[str] = None
    aadhar_number: Optional[str] = None


class EmployeeUpdate(EmployeeBase):
    """Employee update schema."""
    
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    manager_id: Optional[int] = None
    shift_id: Optional[int] = None
    
    # Validators to convert empty strings to None
    @field_validator('department_id', 'designation_id', 'manager_id', 'shift_id', mode='before')
    @classmethod
    def validate_int_fields(cls, v):
        if v == '' or v is None:
            return None
        return v
    
    employment_type: Optional[str] = None
    employment_status: Optional[str] = None
    work_mode: Optional[str] = None
    
    probation_end_date: Optional[date] = None
    confirmation_date: Optional[date] = None
    
    # Bank
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc_code: Optional[str] = None
    bank_branch: Optional[str] = None
    
    # Documents
    pan_number: Optional[str] = None
    aadhar_number: Optional[str] = None
    passport_number: Optional[str] = None
    passport_expiry: Optional[date] = None
    
    # Skills
    skills: Optional[List[str]] = None
    notes: Optional[str] = None
    
    is_active: Optional[bool] = None


class EmployeeTeamResponse(BaseSchema):
    """Simplified team info for employee profile."""
    id: int
    name: str
    code: str
    team_type: Optional[str] = None
    role: Optional[str] = None  # Role in the team
    joined_date: Optional[date] = None


class EmployeeResponse(EmployeeBase, TimestampSchema):
    """Employee response schema."""
    
    id: int
    user_id: int
    employee_code: str  # AW0001 format
    
    # Organization
    company_id: Optional[int] = None
    branch_id: Optional[int] = None
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    manager_id: Optional[int] = None
    
    # Employment
    joining_date: date
    probation_end_date: Optional[date] = None
    confirmation_date: Optional[date] = None
    employment_type: str
    employment_status: str
    work_mode: str
    shift_id: Optional[int] = None
    
    is_active: bool
    
    # User info (nested)
    user: Optional[dict] = None
    
    # Department/Designation names (for display)
    department_name: Optional[str] = None
    designation_name: Optional[str] = None
    manager_name: Optional[str] = None
    
    # Teams
    teams: Optional[List[EmployeeTeamResponse]] = None


class EmployeeListResponse(BaseSchema):
    """Minimal employee info for lists."""
    
    id: int
    user_id: int
    employee_code: str
    first_name: str
    last_name: Optional[str] = None
    email: str
    department_name: Optional[str] = None
    designation_name: Optional[str] = None
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
    expiry_date: Optional[date] = None
    notes: Optional[str] = None


class EmployeeDocumentResponse(TimestampSchema):
    """Employee document response."""
    
    id: int
    employee_id: int
    document_type: str
    document_name: str
    file_path: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    expiry_date: Optional[date] = None
    is_verified: bool
    verified_by: Optional[int] = None
    verified_at: Optional[date] = None
    notes: Optional[str] = None
