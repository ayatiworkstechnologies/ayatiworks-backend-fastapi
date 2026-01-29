"""
Client and CRM models.
Client management, leads, deals, and contracts.
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, JSON, Date, Float, DateTime
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel, AuditMixin


class LeadStatus(enum.Enum):
    """Lead status enum."""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"


class DealStage(enum.Enum):
    """Deal stage enum."""
    DISCOVERY = "discovery"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class Client(BaseModel, AuditMixin):
    """
    Client/Customer model.
    """
    
    __tablename__ = "clients"
    
    # Basic Info
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=True, index=True)
    company_name = Column(String(255), nullable=True)
    
    # Contact
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)
    
    # Address
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    
    # Business Info
    industry = Column(String(100), nullable=True)
    company_size = Column(String(50), nullable=True)
    annual_revenue = Column(Float, nullable=True)
    
    # Tax Info
    tax_id = Column(String(50), nullable=True)
    
    # Assignment
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    
    # Status
    status = Column(String(20), default="active")  # active, inactive, prospect
    
    # Source
    source = Column(String(50), nullable=True)  # referral, website, social, etc.
    
    # Tags
    tags = Column(JSON, nullable=True)
    
    # Relationships
    contacts = relationship("ClientContact", back_populates="client", cascade="all, delete-orphan")
    projects = relationship("Project", backref="client")


class ClientContact(BaseModel, AuditMixin):
    """
    Client contact person.
    """
    
    __tablename__ = "client_contacts"
    
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    mobile = Column(String(20), nullable=True)
    designation = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    
    is_primary = Column(Boolean, default=False)
    
    notes = Column(Text, nullable=True)
    
    # Relationships
    client = relationship("Client", back_populates="contacts")


class LeadSource(BaseModel, AuditMixin):
    """
    Lead source configuration.
    """
    
    __tablename__ = "lead_sources"
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)


class Lead(BaseModel, AuditMixin):
    """
    Sales lead.
    """
    
    __tablename__ = "leads"
    
    # Contact Info
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    company = Column(String(255), nullable=True)
    designation = Column(String(100), nullable=True)
    
    # Source
    source_id = Column(Integer, ForeignKey("lead_sources.id"), nullable=True)
    source_details = Column(String(255), nullable=True)
    campaign = Column(String(100), nullable=True)
    
    # Status
    status = Column(String(20), default=LeadStatus.NEW.value)
    
    # Assignment
    assigned_to = Column(Integer, ForeignKey("employees.id"), nullable=True)
    
    # Scoring
    score = Column(Integer, default=0)  # Lead score
    
    # Interest
    interest = Column(Text, nullable=True)
    budget = Column(Float, nullable=True)
    timeline = Column(String(50), nullable=True)
    
    # Conversion
    converted_at = Column(DateTime, nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)  # After conversion
    
    notes = Column(Text, nullable=True)
    
    # Relationships
    source = relationship("LeadSource", backref="leads")


class Pipeline(BaseModel, AuditMixin):
    """
    Sales pipeline configuration.
    """
    
    __tablename__ = "pipelines"
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    stages = Column(JSON, nullable=True)  # [{name, probability, order}]
    
    is_default = Column(Boolean, default=False)


class Deal(BaseModel, AuditMixin):
    """
    Sales deal/opportunity.
    """
    
    __tablename__ = "deals"
    
    name = Column(String(255), nullable=False)
    
    # Related
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    
    # Pipeline
    pipeline_id = Column(Integer, ForeignKey("pipelines.id"), nullable=True)
    stage = Column(String(50), nullable=True)
    
    # Value
    value = Column(Float, nullable=True)
    currency = Column(String(3), default="USD")
    probability = Column(Integer, default=0)  # 0-100
    weighted_value = Column(Float, nullable=True)  # value * probability
    
    # Timeline
    expected_close_date = Column(Date, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    
    # Assignment
    owner_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    
    # Result
    won_reason = Column(Text, nullable=True)
    lost_reason = Column(Text, nullable=True)
    
    notes = Column(Text, nullable=True)
    
    # Relationships
    pipeline = relationship("Pipeline", backref="deals")


class Contract(BaseModel, AuditMixin):
    """
    Client contract.
    """
    
    __tablename__ = "contracts"
    
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=True)
    
    title = Column(String(255), nullable=False)
    contract_number = Column(String(50), unique=True, nullable=True)
    
    # Type
    contract_type = Column(String(50), default="service")  # service, license, nda, etc.
    
    # Value
    value = Column(Float, nullable=True)
    currency = Column(String(3), default="USD")
    
    # Timeline
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    
    # Renewal
    auto_renewal = Column(Boolean, default=False)
    renewal_period = Column(Integer, nullable=True)  # months
    renewal_notice_days = Column(Integer, default=30)
    
    # Document
    file_path = Column(String(500), nullable=True)
    
    # Status
    status = Column(String(20), default="draft")  # draft, pending, signed, active, expired, cancelled
    
    signed_date = Column(Date, nullable=True)
    signed_by = Column(String(100), nullable=True)
    
    notes = Column(Text, nullable=True)
    
    # Relationships
    client = relationship("Client", backref="contracts")
