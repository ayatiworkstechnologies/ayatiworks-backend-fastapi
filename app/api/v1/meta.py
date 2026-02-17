"""
Meta Ads API Endpoints.

Uses the real Meta Graph API via MetaGraphService.
"""

import logging
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

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Meta Ads"])


# ============ Helper: Resolve client_id ============

def _resolve_client_id(current_user: User, db: Session, client_id: int | None = None) -> int:
    """Resolve the client_id based on user role."""
    if current_user.role.code == 'CLIENT':
        client = db.query(Client).filter(Client.email == current_user.email).first()
        if not client:
            raise ResourceNotFoundError("Client Profile", "current_user")
        return client.id

    if current_user.role.is_system or current_user.role.code in ['ADMIN', 'SUPER_ADMIN']:
        if not client_id:
            raise HTTPException(status_code=400, detail="client_id parameter is required for Admins")
        return client_id

    raise PermissionDeniedError("Valid Client ID required.")


# ============ Credentials / Config ============

@router.get("/meta/config", response_model=MetaCredentialResponse)
async def get_meta_config(
    client_id: int | None = None,
    current_user: User = Depends(PermissionChecker("meta.view")),
    db: Session = Depends(get_db)
):
    """Get Meta Ads configuration for the client."""
    target_id = _resolve_client_id(current_user, db, client_id)

    config = db.query(MetaCredential).filter(MetaCredential.client_id == target_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    return MetaCredentialResponse.model_validate(config)


@router.post("/meta/config", response_model=MetaCredentialResponse)
async def save_meta_config(
    data: MetaCredentialCreate,
    client_id: int | None = None,
    current_user: User = Depends(PermissionChecker("meta.manage")),
    db: Session = Depends(get_db)
):
    """Save or update Meta Ads configuration."""
    target_id = _resolve_client_id(current_user, db, client_id)

    config = db.query(MetaCredential).filter(MetaCredential.client_id == target_id).first()

    if config:
        config.ad_account_id = data.ad_account_id
        config.access_token = data.access_token
        if data.app_id:
            config.app_id = data.app_id
        if data.app_secret:
            config.app_secret = data.app_secret
        config.updated_by = current_user.id
    else:
        config = MetaCredential(
            client_id=target_id,
            **data.model_dump(),
            created_by=current_user.id
        )
        db.add(config)

    db.commit()
    db.refresh(config)
    return MetaCredentialResponse.model_validate(config)


# ============ Token Exchange ============

@router.post("/meta/exchange-token")
async def exchange_token(
    short_lived_token: str,
    client_id: int | None = None,
    current_user: User = Depends(PermissionChecker("meta.manage")),
    db: Session = Depends(get_db)
):
    """
    Exchange a short-lived Meta token for a long-lived token.
    Requires app_id and app_secret to be configured in Meta settings.
    Automatically saves the new long-lived token.
    """
    from app.services.meta_service import MetaGraphService

    target_id = _resolve_client_id(current_user, db, client_id)

    config = db.query(MetaCredential).filter(MetaCredential.client_id == target_id).first()
    if not config:
        raise HTTPException(status_code=400, detail="Configure Meta settings first (Ad Account ID, App ID, App Secret)")

    if not config.app_id or not config.app_secret:
        raise HTTPException(status_code=400, detail="App ID and App Secret required for token exchange")

    try:
        with MetaGraphService(
            access_token=config.access_token,
            ad_account_id=config.ad_account_id,
            app_id=config.app_id,
            app_secret=config.app_secret,
        ) as service:
            result = service.exchange_token(short_lived_token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Save the new long-lived token
    new_token = result.get("access_token")
    if new_token:
        config.access_token = new_token
        config.updated_by = current_user.id
        db.commit()

    return {
        "message": "Token exchanged successfully",
        "token_type": result.get("token_type", "bearer"),
        "expires_in": result.get("expires_in"),
    }


# ============ Campaigns ============

@router.get("/meta/campaigns", response_model=PaginatedResponse[MetaCampaignResponse])
async def list_meta_campaigns(
    client_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("meta.view")),
    db: Session = Depends(get_db)
):
    """List synced campaigns."""
    target_id = _resolve_client_id(current_user, db, client_id)

    query = db.query(MetaCampaign).filter(MetaCampaign.client_id == target_id)
    total = query.count()

    campaigns = query.order_by(desc(MetaCampaign.id)).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for c in campaigns:
        resp = MetaCampaignResponse.model_validate(c)
        resp.lead_count = db.query(MetaLead).filter(MetaLead.campaign_id == c.id).count()
        items.append(resp)

    return PaginatedResponse.create(items, total, page, page_size)


# ============ Leads ============

@router.get("/meta/leads", response_model=PaginatedResponse[MetaLeadResponse])
async def list_meta_leads(
    client_id: int | None = None,
    campaign_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("meta.view")),
    db: Session = Depends(get_db)
):
    """List synced leads."""
    from sqlalchemy.orm import joinedload

    target_id = _resolve_client_id(current_user, db, client_id)

    query = db.query(MetaLead).filter(MetaLead.client_id == target_id)

    if campaign_id:
        query = query.filter(MetaLead.campaign_id == campaign_id)

    total = query.count()
    leads = query.options(
        joinedload(MetaLead.campaign)
    ).order_by(desc(MetaLead.created_time)).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for lead_item in leads:
        resp = MetaLeadResponse.model_validate(lead_item)
        if lead_item.campaign:
            resp.campaign_name = lead_item.campaign.name
            resp.campaign_id = lead_item.campaign.id
        items.append(resp)

    return PaginatedResponse.create(items, total, page, page_size)


# ============ Sync (REAL Meta Graph API) ============

@router.post("/meta/sync", response_model=MessageResponse)
async def sync_meta_data(
    client_id: int | None = None,
    current_user: User = Depends(PermissionChecker("meta.manage")),
    db: Session = Depends(get_db)
):
    """
    Trigger real synchronization with Meta Graph API.

    Flow:
      1. Fetch campaigns from ad account
      2. For each campaign → fetch ads
      3. For each ad → fetch lead forms
      4. For each form → fetch leads
      5. Store everything in database
    """
    from app.services.meta_service import MetaGraphService

    target_id = _resolve_client_id(current_user, db, client_id)

    config = db.query(MetaCredential).filter(MetaCredential.client_id == target_id).first()
    if not config:
        raise HTTPException(status_code=400, detail="Meta credentials not configured. Go to Settings.")

    if not config.access_token or not config.ad_account_id:
        raise HTTPException(status_code=400, detail="Access token and Ad Account ID are required.")

    try:
        with MetaGraphService(
            access_token=config.access_token,
            ad_account_id=config.ad_account_id,
            app_id=config.app_id,
            app_secret=config.app_secret,
        ) as service:
            stats = service.full_sync(db, target_id)
    except Exception as e:
        logger.error(f"Meta sync error: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

    # Update last synced timestamp
    config.last_synced_at = datetime.utcnow()
    config.updated_by = current_user.id
    db.commit()

    errors_text = f" ({len(stats['errors'])} warnings)" if stats.get("errors") else ""
    return MessageResponse(
        message=f"Sync complete: {stats['campaigns_synced']} campaigns, {stats['leads_synced']} leads synced{errors_text}"
    )
