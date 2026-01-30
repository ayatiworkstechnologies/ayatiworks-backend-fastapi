"""
Meta Ads API Schemas.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema, TimestampSchema

# ============ Credentials ============

class MetaCredentialBase(BaseSchema):
    ad_account_id: str
    access_token: str
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    is_active: Optional[bool] = True

class MetaCredentialCreate(MetaCredentialBase):
    pass

class MetaCredentialUpdate(BaseSchema):
    ad_account_id: Optional[str] = None
    access_token: Optional[str] = None
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    is_active: Optional[bool] = None

class MetaCredentialResponse(MetaCredentialBase, TimestampSchema):
    id: int
    client_id: int
    last_synced_at: Optional[datetime] = None


# ============ Campaigns ============

class MetaCampaignBase(BaseSchema):
    campaign_id: str
    name: str
    status: Optional[str] = None
    objective: Optional[str] = None
    daily_budget: Optional[float] = None
    lifetime_budget: Optional[float] = None
    spend: Optional[float] = None
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None

class MetaCampaignCreate(MetaCampaignBase):
    pass

class MetaCampaignUpdate(BaseSchema):
    name: Optional[str] = None
    status: Optional[str] = None
    spend: Optional[float] = None

class MetaCampaignResponse(MetaCampaignBase, TimestampSchema):
    id: int
    client_id: int
    lead_count: int = 0


# ============ Leads ============

class MetaLeadBase(BaseSchema):
    lead_id: str
    form_id: Optional[str] = None
    created_time: Optional[datetime] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    status: Optional[str] = "new"

class MetaLeadCreate(MetaLeadBase):
    campaign_meta_id: Optional[str] = None # To link by string ID during sync

class MetaLeadUpdate(BaseSchema):
    status: Optional[str] = None
    notes: Optional[str] = None

class MetaLeadResponse(MetaLeadBase, TimestampSchema):
    id: int
    client_id: int
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
