"""
Client and CRM schemas.
Client schemas now use employee-based fields since clients are employees with CLIENT role.
"""

from datetime import date

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import BaseSchema, TimestampSchema


# ============== Client Schemas (Employee-based) ==============

class ClientCreate(BaseSchema):
    """Client create schema — creates a User + Employee with CLIENT role."""

    # Required user fields
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str | None = None
    email: EmailStr
    password: str | None = None
    phone: str | None = None
    avatar: str | None = None

    # Employee organization fields
    company_id: int | None = None
    department_id: int | None = None
    designation_id: int | None = None
    joining_date: date = Field(default_factory=date.today)
    employment_type: str | None = "contract"
    work_mode: str | None = "remote"

    # CRM company fields (optional)
    company_name: str | None = None
    industry: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    website: str | None = None
    postal_code: str | None = None
    company_size: str | None = None
    annual_revenue: float | None = None
    tax_id: str | None = None
    source: str | None = None
    tags: list[str] | None = None

    @field_validator('company_id', 'department_id', 'designation_id', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class ClientUpdate(BaseSchema):
    """Client update schema."""

    # User fields
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    avatar: str | None = None

    # Employee fields
    department_id: int | None = None
    designation_id: int | None = None
    manager_id: int | None = None
    status: str | None = None

    # CRM company fields
    company_name: str | None = None
    industry: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    website: str | None = None
    postal_code: str | None = None
    company_size: str | None = None
    annual_revenue: float | None = None
    tax_id: str | None = None
    source: str | None = None
    tags: list[str] | None = None

    @field_validator('department_id', 'designation_id', 'manager_id', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class ClientResponse(TimestampSchema):
    """Client response schema — employee with CLIENT role."""

    id: int
    employee_code: str
    first_name: str
    last_name: str | None = None
    email: str
    phone: str | None = None
    avatar: str | None = None

    # Organization
    department_id: int | None = None
    designation_id: int | None = None
    department_name: str | None = None
    designation_name: str | None = None
    company_id: int | None = None
    company_name: str | None = None

    # Employment
    joining_date: date | None = None
    employment_status: str | None = None
    is_active: bool = True
    status: str = "active"

    # CRM Client profile ID (for modules, mail, etc.)
    crm_client_id: int | None = None
    crm_client_slug: str | None = None


class ClientListResponse(BaseSchema):
    """Client list item — employee with CLIENT role."""

    id: int
    employee_code: str
    first_name: str
    last_name: str | None = None
    email: str
    avatar: str | None = None
    department_name: str | None = None
    designation_name: str | None = None
    status: str = "active"
    is_active: bool = True

    # CRM Client profile ID (for modules, mail, etc.)
    crm_client_id: int | None = None
    crm_client_slug: str | None = None


# ============== Lead Schemas ==============

class LeadCreate(BaseSchema):
    """Lead create schema."""

    name: str
    email: EmailStr | None = None
    phone: str | None = None
    company: str | None = None
    designation: str | None = None
    source_id: int | None = None
    campaign: str | None = None
    source_details: str | None = None
    interest: str | None = None
    budget: float | None = None


class LeadUpdate(BaseSchema):
    """Lead update schema."""

    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    company: str | None = None
    status: str | None = None
    score: int | None = None
    campaign: str | None = None
    assigned_to: int | None = None


class LeadResponse(TimestampSchema):
    """Lead response schema."""

    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    status: str
    score: int
    campaign: str | None = None
    assigned_to: int | None = None

    # Display
    source_name: str | None = None
    assigned_to_name: str | None = None


# ============== Deal Schemas ==============

class DealCreate(BaseSchema):
    """Deal create schema."""

    name: str
    lead_id: int | None = None
    client_id: int | None = None
    pipeline_id: int | None = None
    stage: str | None = None
    value: float | None = None
    currency: str = "USD"
    expected_close_date: date | None = None
    owner_id: int | None = None


class DealUpdate(BaseSchema):
    """Deal update schema."""

    name: str | None = None
    stage: str | None = None
    value: float | None = None
    probability: int | None = None
    expected_close_date: date | None = None
    owner_id: int | None = None
    won_reason: str | None = None
    lost_reason: str | None = None


class DealResponse(TimestampSchema):
    """Deal response schema."""

    id: int
    name: str
    lead_id: int | None = None
    client_id: int | None = None
    pipeline_id: int | None = None
    stage: str | None = None
    value: float | None = None
    currency: str
    probability: int
    weighted_value: float | None = None
    expected_close_date: date | None = None
    owner_id: int | None = None

    # Display
    client_name: str | None = None
    owner_name: str | None = None
