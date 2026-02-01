"""
Meta Ads API Endpoints.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import PermissionChecker
from app.core.exceptions import PermissionDeniedError, ResourceNotFoundError
from app.database import get_db
from app.models.auth import User
from app.models.client import Client
from app.models.meta import MetaCampaign, MetaCredential, MetaLead
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.meta import (
    MetaCampaignResponse,
    MetaCredentialCreate,
    MetaCredentialResponse,
    MetaLeadResponse,
)

router = APIRouter(tags=["Meta Ads"])


# ============ Credentials / Config ============

@router.get("/meta/config", response_model=MetaCredentialResponse)
async def get_meta_config(
    client_id: int | None = None,
    current_user: User = Depends(PermissionChecker("meta.view")),
    db: Session = Depends(get_db)
):
    """Get Meta Ads configuration for the current client."""

    target_client_id = None

    # 1. If Client Role, force their own ID
    if current_user.role.code == 'CLIENT':
        client = db.query(Client).filter(Client.email == current_user.email).first()
        if not client:
            raise ResourceNotFoundError("Client Profile", "current_user")
        target_client_id = client.id

    # 2. If Admin/Super Admin, use provided ID or error
    elif current_user.role.is_system or current_user.role.code in ['ADMIN', 'SUPER_ADMIN']:
        if not client_id:
            # For list views, we might return null, but for config we need specific client
            raise HTTPException(status_code=400, detail="client_id parameter is required for Admins")
        target_client_id = client_id

    if not target_client_id:
        raise PermissionDeniedError("Valid Client ID required.")

    config = db.query(MetaCredential).filter(MetaCredential.client_id == target_client_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    return MetaCredentialResponse.model_validate(config)


@router.post("/meta/config", response_model=MetaCredentialResponse)
async def save_meta_config(
    data: MetaCredentialCreate,
    current_user: User = Depends(PermissionChecker("meta.manage")),
    db: Session = Depends(get_db)
):
    """Save or update Meta Ads configuration."""
    client_id = None
    if current_user.role.code == 'CLIENT':
        client = db.query(Client).filter(Client.email == current_user.email).first()
        if not client:
            raise ResourceNotFoundError("Client Profile", "current_user")
        client_id = client.id

    if not client_id:
        raise PermissionDeniedError("No associated client profile found.")

    config = db.query(MetaCredential).filter(MetaCredential.client_id == client_id).first()

    if config:
        # Update
        config.ad_account_id = data.ad_account_id
        config.access_token = data.access_token
        if data.app_id:
            config.app_id = data.app_id
        if data.app_secret:
            config.app_secret = data.app_secret
        config.updated_by = current_user.id
    else:
        # Create
        config = MetaCredential(
            client_id=client_id,
            **data.model_dump(),
            created_by=current_user.id
        )
        db.add(config)

    db.commit()
    db.refresh(config)
    return MetaCredentialResponse.model_validate(config)


# ============ Campaigns ============

@router.get("/meta/campaigns", response_model=PaginatedResponse[MetaCampaignResponse])
async def list_meta_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("meta.view")),
    db: Session = Depends(get_db)
):
    """List synced campaigns."""
    client_id = None
    if current_user.role.code == 'CLIENT':
        client = db.query(Client).filter(Client.email == current_user.email).first()
        client_id = client.id if client else -1

    query = db.query(MetaCampaign).filter(MetaCampaign.client_id == client_id)
    total = query.count()

    campaigns = query.offset((page - 1) * page_size).limit(page_size).all()

    # Enrich with simple lead count (could be optimized)
    items = []
    for c in campaigns:
        resp = MetaCampaignResponse.model_validate(c)
        resp.lead_count = db.query(MetaLead).filter(MetaLead.campaign_id == c.id).count()
        items.append(resp)

    return PaginatedResponse.create(items, total, page, page_size)


# ============ Leads ============

@router.get("/meta/leads", response_model=PaginatedResponse[MetaLeadResponse])
async def list_meta_leads(
    campaign_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("meta.view")),
    db: Session = Depends(get_db)
):
    """List synced leads."""
    from sqlalchemy.orm import joinedload

    client_id = None
    if current_user.role.code == 'CLIENT':
        client = db.query(Client).filter(Client.email == current_user.email).first()
        client_id = client.id if client else -1

    query = db.query(MetaLead).filter(MetaLead.client_id == client_id)

    if campaign_id:
        query = query.filter(MetaLead.campaign_id == campaign_id)

    total = query.count()
    leads = query.options(joinedload(MetaLead.campaign)).order_by(desc(MetaLead.created_time)).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for lead_item in leads:
        resp = MetaLeadResponse.model_validate(lead_item)
        if lead_item.campaign:
            resp.campaign_name = lead_item.campaign.name
            resp.campaign_id = lead_item.campaign.id
        items.append(resp)

    return PaginatedResponse.create(items, total, page, page_size)


# ============ Sync (Simulation) ============

@router.post("/meta/sync", response_model=MessageResponse)
async def sync_meta_data(
    current_user: User = Depends(PermissionChecker("meta.manage")),
    db: Session = Depends(get_db)
):
    """
    Trigger synchronization with Meta API.
    (Currently MOCKED for demonstration)
    """
    client_id = None
    if current_user.role.code == 'CLIENT':
        client = db.query(Client).filter(Client.email == current_user.email).first()
        client_id = client.id if client else None

    if not client_id:
        raise PermissionDeniedError("Client profile required for sync.")

    config = db.query(MetaCredential).filter(MetaCredential.client_id == client_id).first()
    if not config:
        raise HTTPException(status_code=400, detail="Meta credentials not configured.")

    # --- MOCKED SYNC LOGIC START ---
    import random

    # 1. Mock Campaigns
    campaigns_data = [
        {"id": "camp_123", "name": "Summer Sale Promo", "status": "ACTIVE", "budget": 100.0},
        {"id": "camp_456", "name": "Brand Awareness", "status": "PAUSED", "budget": 50.0},
        {"id": "camp_789", "name": "Lead Gen - Ebook", "status": "ACTIVE", "budget": 200.0},
    ]

    for c_data in campaigns_data:
        camp = db.query(MetaCampaign).filter(
            MetaCampaign.client_id == client_id,
            MetaCampaign.campaign_id == c_data["id"]
        ).first()

        if not camp:
            camp = MetaCampaign(
                client_id=client_id,
                campaign_id=c_data["id"],
                name=c_data["name"],
                status=c_data["status"],
                daily_budget=c_data["budget"],
                start_time=datetime.utcnow()
            )
            db.add(camp)

    db.flush() # Get IDs

    # 2. Mock Leads
    campaigns = db.query(MetaCampaign).filter(MetaCampaign.client_id == client_id).all()
    if campaigns:
        # Create a random lead
        camp = random.choice(campaigns)
        lead_id = f"lead_{random.randint(1000, 9999)}"

        # Check duplicate
        if not db.query(MetaLead).filter(MetaLead.lead_id == lead_id).first():
            new_lead = MetaLead(
                client_id=client_id,
                campaign_id=camp.id,
                lead_id=lead_id,
                created_time=datetime.utcnow(),
                full_name=f"Lead {random.randint(1, 100)}",
                email=f"lead{random.randint(1, 100)}@example.com",
                phone_number=f"+1555{random.randint(100000, 999999)}",
                status="new",
                raw_data={"source": "fb", "ad_id": "ad_123"}
            )
            db.add(new_lead)

    config.last_synced_at = datetime.utcnow()
    # --- MOCKED SYNC LOGIC END ---

    db.commit()

    return MessageResponse(message="Synchronization completed successfully (Mocked).")

