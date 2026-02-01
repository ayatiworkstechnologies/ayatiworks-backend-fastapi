"""
Company and Branch models.
Multi-company and multi-branch support.
"""

from sqlalchemy import JSON, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import AuditMixin, BaseModel


class Company(BaseModel, AuditMixin):
    """
    Company model for multi-tenant support.
    """

    __tablename__ = "companies"

    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    logo = Column(String(255), nullable=True)

    # Contact Information
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)

    # Address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)

    # Legal Information
    registration_number = Column(String(100), nullable=True)
    tax_id = Column(String(50), nullable=True)

    # Settings
    settings = Column(JSON, nullable=True)
    timezone = Column(String(50), default="UTC")
    currency = Column(String(3), default="USD")
    date_format = Column(String(20), default="YYYY-MM-DD")

    # Status
    subscription_plan = Column(String(50), nullable=True)
    subscription_expires = Column(String(50), nullable=True)

    # Relationships
    branches = relationship("Branch", back_populates="company", cascade="all, delete-orphan")
    departments = relationship("Department", back_populates="company", cascade="all, delete-orphan")
    teams = relationship("Team", back_populates="company", cascade="all, delete-orphan")


class Branch(BaseModel, AuditMixin):
    """
    Branch model for companies with multiple locations.
    """

    __tablename__ = "branches"

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False, index=True)

    # Contact Information
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)

    # Address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)

    # Location
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)
    geo_fence_radius = Column(Integer, default=100)  # meters for geo-fencing

    # Manager
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Settings
    settings = Column(JSON, nullable=True)
    timezone = Column(String(50), nullable=True)  # Inherits from company if null

    # Relationships
    company = relationship("Company", back_populates="branches")

