"""
Company and Branch schemas.
"""


from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema, TimestampSchema

# ============== Company Schemas ==============

class CompanyBase(BaseSchema):
    """Company base schema."""

    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=50)
    logo: str | None = None

    # Contact
    email: EmailStr | None = None
    phone: str | None = None
    website: str | None = None

    # Address
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None

    # Legal
    registration_number: str | None = None
    tax_id: str | None = None

    # Settings
    timezone: str = "UTC"
    currency: str = "USD"
    date_format: str = "YYYY-MM-DD"


class CompanyCreate(CompanyBase):
    """Company create schema."""
    pass


class CompanyUpdate(BaseSchema):
    """Company update schema."""

    name: str | None = None
    logo: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    website: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    registration_number: str | None = None
    tax_id: str | None = None
    timezone: str | None = None
    currency: str | None = None
    is_active: bool | None = None


class CompanyResponse(CompanyBase, TimestampSchema):
    """Company response schema."""

    id: int
    is_active: bool
    subscription_plan: str | None = None
    branch_count: int = 0
    employee_count: int = 0


class CompanyListResponse(BaseSchema):
    """Minimal company info for lists."""

    id: int
    name: str
    code: str
    logo: str | None = None
    is_active: bool


# ============== Branch Schemas ==============

class BranchBase(BaseSchema):
    """Branch base schema."""

    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=50)

    # Contact
    email: EmailStr | None = None
    phone: str | None = None

    # Address
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None

    # Location
    latitude: str | None = None
    longitude: str | None = None
    geo_fence_radius: int = 100


class BranchCreate(BranchBase):
    """Branch create schema."""

    company_id: int
    manager_id: int | None = None
    timezone: str | None = None


class BranchUpdate(BaseSchema):
    """Branch update schema."""

    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    latitude: str | None = None
    longitude: str | None = None
    geo_fence_radius: int | None = None
    manager_id: int | None = None
    timezone: str | None = None
    is_active: bool | None = None


class BranchResponse(BranchBase, TimestampSchema):
    """Branch response schema."""

    id: int
    company_id: int
    manager_id: int | None = None
    timezone: str | None = None
    is_active: bool

    # Display
    company_name: str | None = None
    manager_name: str | None = None
    employee_count: int = 0


class BranchListResponse(BaseSchema):
    """Minimal branch info for lists."""

    id: int
    company_id: int
    name: str
    code: str
    city: str | None = None
    is_active: bool

