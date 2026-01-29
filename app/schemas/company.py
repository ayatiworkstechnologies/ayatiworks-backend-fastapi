"""
Company and Branch schemas.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr

from app.schemas.common import BaseSchema, TimestampSchema


# ============== Company Schemas ==============

class CompanyBase(BaseSchema):
    """Company base schema."""
    
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=50)
    logo: Optional[str] = None
    
    # Contact
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    
    # Address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    
    # Legal
    registration_number: Optional[str] = None
    tax_id: Optional[str] = None
    
    # Settings
    timezone: str = "UTC"
    currency: str = "USD"
    date_format: str = "YYYY-MM-DD"


class CompanyCreate(CompanyBase):
    """Company create schema."""
    pass


class CompanyUpdate(BaseSchema):
    """Company update schema."""
    
    name: Optional[str] = None
    logo: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    registration_number: Optional[str] = None
    tax_id: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None


class CompanyResponse(CompanyBase, TimestampSchema):
    """Company response schema."""
    
    id: int
    is_active: bool
    subscription_plan: Optional[str] = None
    branch_count: int = 0
    employee_count: int = 0


class CompanyListResponse(BaseSchema):
    """Minimal company info for lists."""
    
    id: int
    name: str
    code: str
    logo: Optional[str] = None
    is_active: bool


# ============== Branch Schemas ==============

class BranchBase(BaseSchema):
    """Branch base schema."""
    
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=50)
    
    # Contact
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    
    # Address
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    
    # Location
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    geo_fence_radius: int = 100


class BranchCreate(BranchBase):
    """Branch create schema."""
    
    company_id: int
    manager_id: Optional[int] = None
    timezone: Optional[str] = None


class BranchUpdate(BaseSchema):
    """Branch update schema."""
    
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    geo_fence_radius: Optional[int] = None
    manager_id: Optional[int] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None


class BranchResponse(BranchBase, TimestampSchema):
    """Branch response schema."""
    
    id: int
    company_id: int
    manager_id: Optional[int] = None
    timezone: Optional[str] = None
    is_active: bool
    
    # Display
    company_name: Optional[str] = None
    manager_name: Optional[str] = None
    employee_count: int = 0


class BranchListResponse(BaseSchema):
    """Minimal branch info for lists."""
    
    id: int
    company_id: int
    name: str
    code: str
    city: Optional[str] = None
    is_active: bool
