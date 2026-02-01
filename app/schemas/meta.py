"""
Meta Ads API Schemas.
"""

from datetime import datetime
from typing import Any

from app.schemas.common import BaseSchema, TimestampSchema

# ============ Credentials ============

class MetaCredentialBase(BaseSchema):
    ad_account_id: str
    access_token: str
    app_id: str | None = None
    app_secret: str | None = None
    is_active: bool | None = True

class MetaCredentialCreate(MetaCredentialBase):
    pass

class MetaCredentialUpdate(BaseSchema):
    ad_account_id: str | None = None
    access_token: str | None = None
    app_id: str | None = None
    app_secret: str | None = None
    is_active: bool | None = None

class MetaCredentialResponse(MetaCredentialBase, TimestampSchema):
    id: int
    client_id: int
    last_synced_at: datetime | None = None


# ============ Campaigns ============

class MetaCampaignBase(BaseSchema):
    campaign_id: str
    name: str
    status: str | None = None
    objective: str | None = None
    daily_budget: float | None = None
    lifetime_budget: float | None = None
    spend: float | None = None
    start_time: datetime | None = None
    stop_time: datetime | None = None

class MetaCampaignCreate(MetaCampaignBase):
    pass

class MetaCampaignUpdate(BaseSchema):
    name: str | None = None
    status: str | None = None
    spend: float | None = None

class MetaCampaignResponse(MetaCampaignBase, TimestampSchema):
    id: int
    client_id: int
    lead_count: int = 0


# ============ Leads ============

class MetaLeadBase(BaseSchema):
    lead_id: str
    form_id: str | None = None
    created_time: datetime | None = None
    full_name: str | None = None
    email: str | None = None
    phone_number: str | None = None
    raw_data: dict[str, Any] | None = None
    status: str | None = "new"

class MetaLeadCreate(MetaLeadBase):
    campaign_meta_id: str | None = None # To link by string ID during sync

class MetaLeadUpdate(BaseSchema):
    status: str | None = None
    notes: str | None = None

class MetaLeadResponse(MetaLeadBase, TimestampSchema):
    id: int
    client_id: int
    campaign_id: int | None = None
    campaign_name: str | None = None

