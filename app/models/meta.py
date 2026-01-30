"""
Meta Ads Integration Models.
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, JSON, DateTime, Float
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, AuditMixin

class MetaCredential(BaseModel, AuditMixin):
    """
    Stores Meta App credentials for a client.
    One record per client company (or user, depending on scope).
    """
    __tablename__ = "meta_credentials"
    
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    ad_account_id = Column(String(100), nullable=False)
    access_token = Column(Text, nullable=False) # Long-lived token
    app_id = Column(String(100), nullable=True)
    app_secret = Column(String(100), nullable=True)
    
    is_active = Column(Boolean, default=True)
    last_synced_at = Column(DateTime, nullable=True)
    
    # Relationships
    client = relationship("Client", backref="meta_credential")


class MetaCampaign(BaseModel, AuditMixin):
    """
    Campaigns synced from Meta Ads.
    """
    __tablename__ = "meta_campaigns"
    
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    
    campaign_id = Column(String(100), nullable=False, unique=True) # Meta ID
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=True) # ACTIVE, PAUSED, etc.
    objective = Column(String(100), nullable=True)
    
    daily_budget = Column(Float, nullable=True)
    lifetime_budget = Column(Float, nullable=True)
    spend = Column(Float, default=0.0)
    
    start_time = Column(DateTime, nullable=True)
    stop_time = Column(DateTime, nullable=True)
    
    # Relationships
    client = relationship("Client", backref="meta_campaigns")
    leads = relationship("MetaLead", back_populates="campaign", cascade="all, delete-orphan")


class MetaLead(BaseModel, AuditMixin):
    """
    Leads retrieved from Meta Lead Ads.
    """
    __tablename__ = "meta_leads"
    
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("meta_campaigns.id"), nullable=True)
    
    lead_id = Column(String(100), nullable=False, unique=True) # Meta Lead ID
    form_id = Column(String(100), nullable=True)
    
    created_time = Column(DateTime, nullable=True) # When lead was created on Meta
    
    # Lead Data
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone_number = Column(String(50), nullable=True)
    
    raw_data = Column(JSON, nullable=True) # Full JSON response from Meta
    
    status = Column(String(50), default="new") # new, processed, contacted
    
    # Relationships
    campaign = relationship("MetaCampaign", back_populates="leads")
    client = relationship("Client", backref="meta_leads")
