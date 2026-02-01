"""
Client and CRM schemas.
"""

from datetime import date

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import BaseSchema, TimestampSchema

# ============== Client Schemas ==============

class ClientBase(BaseSchema):
    """Client base schema."""

    name: str = Field(..., min_length=2, max_length=255)
    company_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None


class ClientContactCreate(BaseSchema):
    """Client contact creation schema."""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr | None = None
    phone: str | None = None
    designation: str | None = None
    is_primary: bool = False


class ClientCreate(ClientBase):
    """Client create schema."""

    code: str | None = None
    website: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    industry: str | None = None
    company_size: str | None = None
    annual_revenue: float | None = None
    tax_id: str | None = None
    manager_id: int | None = None
    source: str | None = None
    source: str | None = None
    tags: list[str] | None = None
    contacts: list[ClientContactCreate] | None = None

    @field_validator('manager_id', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class ClientUpdate(BaseSchema):
    """Client update schema."""

    name: str | None = None
    company_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    industry: str | None = None
    company_size: str | None = None
    annual_revenue: float | None = None
    tax_id: str | None = None
    manager_id: int | None = None
    status: str | None = None
    tags: list[str] | None = None

    @field_validator('manager_id', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class ClientResponse(ClientBase, TimestampSchema):
    """Client response schema."""

    id: int
    code: str | None = None
    website: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    industry: str | None = None
    company_size: str | None = None
    annual_revenue: float | None = None
    tax_id: str | None = None
    manager_id: int | None = None
    status: str

    # Counts
    project_count: int = 0
    invoice_count: int = 0


class ClientListResponse(BaseSchema):
    """Client list item."""

    id: int
    name: str
    company_name: str | None = None
    email: str | None = None
    status: str


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

