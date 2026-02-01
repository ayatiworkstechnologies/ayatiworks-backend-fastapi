"""
Public facing schemas for Contact and Careers.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, HttpUrl

from app.schemas.common import PaginatedResponse

# =======================
# Contact Schemas
# =======================

class ContactCreate(BaseModel):
    """Schema for creating a contact enquiry."""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str | None = Field(None, max_length=20)
    subject: str = Field(..., min_length=5, max_length=200)
    message: str = Field(..., min_length=10)

class ContactUpdate(BaseModel):
    """Schema for updating contact enquiry status."""
    status: str = Field(..., pattern="^(new|read|replied|closed)$")
    notes: str | None = None

class ContactResponse(BaseModel):
    """Response schema for contact enquiry."""
    id: int
    name: str
    email: str
    phone: str | None
    subject: str
    message: str
    status: str
    ip_address: str | None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True

class ContactListResponse(PaginatedResponse[ContactResponse]):
    """Paginated list of contact enquiries."""
    pass


# =======================
# Career Schemas
# =======================

class CareerCreate(BaseModel):
    """Schema for submitting a job application."""
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)

    position_applied: str = Field(..., min_length=2, max_length=100)
    experience_years: int | None = Field(None, ge=0, le=50)
    current_company: str | None = None

    portfolio_url: HttpUrl | None = None
    linkedin_url: HttpUrl | None = None
    cover_letter: str | None = None
    # resume_url is handled by backend

class CareerUpdate(BaseModel):
    """Schema for updating career application status."""
    status: str = Field(..., pattern="^(new|reviewed|interviewed|rejected|hired)$")
    notes: str | None = None

class CareerResponse(BaseModel):
    """Response schema for job application."""
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    position_applied: str
    experience_years: int | None
    current_company: str | None
    portfolio_url: str | None
    linkedin_url: str | None
    resume_url: str | None
    cover_letter: str | None
    status: str
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True

class CareerListResponse(PaginatedResponse[CareerResponse]):
    """Paginated list of career applications."""
    pass

