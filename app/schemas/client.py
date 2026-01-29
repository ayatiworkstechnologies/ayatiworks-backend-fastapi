"""
Client and CRM schemas.
"""

from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, Field, EmailStr, field_validator

from app.schemas.common import BaseSchema, TimestampSchema


# ============== Client Schemas ==============

class ClientBase(BaseSchema):
    """Client base schema."""
    
    name: str = Field(..., min_length=2, max_length=255)
    company_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class ClientCreate(ClientBase):
    """Client create schema."""
    
    code: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    annual_revenue: Optional[float] = None
    tax_id: Optional[str] = None
    manager_id: Optional[int] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = None
    
    @field_validator('manager_id', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class ClientUpdate(BaseSchema):
    """Client update schema."""
    
    name: Optional[str] = None
    company_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    annual_revenue: Optional[float] = None
    tax_id: Optional[str] = None
    manager_id: Optional[int] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    
    @field_validator('manager_id', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class ClientResponse(ClientBase, TimestampSchema):
    """Client response schema."""
    
    id: int
    code: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    annual_revenue: Optional[float] = None
    tax_id: Optional[str] = None
    manager_id: Optional[int] = None
    status: str
    
    # Counts
    project_count: int = 0
    invoice_count: int = 0


class ClientListResponse(BaseSchema):
    """Client list item."""
    
    id: int
    name: str
    company_name: Optional[str] = None
    email: Optional[str] = None
    status: str


# ============== Lead Schemas ==============

class LeadCreate(BaseSchema):
    """Lead create schema."""
    
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    designation: Optional[str] = None
    source_id: Optional[int] = None
    campaign: Optional[str] = None
    interest: Optional[str] = None
    budget: Optional[float] = None


class LeadUpdate(BaseSchema):
    """Lead update schema."""
    
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    status: Optional[str] = None
    score: Optional[int] = None
    campaign: Optional[str] = None
    assigned_to: Optional[int] = None


class LeadResponse(TimestampSchema):
    """Lead response schema."""
    
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    status: str
    score: int
    campaign: Optional[str] = None
    assigned_to: Optional[int] = None
    
    # Display
    source_name: Optional[str] = None
    assigned_to_name: Optional[str] = None


# ============== Deal Schemas ==============

class DealCreate(BaseSchema):
    """Deal create schema."""
    
    name: str
    lead_id: Optional[int] = None
    client_id: Optional[int] = None
    pipeline_id: Optional[int] = None
    stage: Optional[str] = None
    value: Optional[float] = None
    currency: str = "USD"
    expected_close_date: Optional[date] = None
    owner_id: Optional[int] = None


class DealUpdate(BaseSchema):
    """Deal update schema."""
    
    name: Optional[str] = None
    stage: Optional[str] = None
    value: Optional[float] = None
    probability: Optional[int] = None
    expected_close_date: Optional[date] = None
    owner_id: Optional[int] = None
    won_reason: Optional[str] = None
    lost_reason: Optional[str] = None


class DealResponse(TimestampSchema):
    """Deal response schema."""
    
    id: int
    name: str
    lead_id: Optional[int] = None
    client_id: Optional[int] = None
    pipeline_id: Optional[int] = None
    stage: Optional[str] = None
    value: Optional[float] = None
    currency: str
    probability: int
    weighted_value: Optional[float] = None
    expected_close_date: Optional[date] = None
    owner_id: Optional[int] = None
    
    # Display
    client_name: Optional[str] = None
    owner_name: Optional[str] = None
