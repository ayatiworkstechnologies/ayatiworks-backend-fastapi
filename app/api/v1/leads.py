"""
Leads API routes.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.api.deps import PermissionChecker
from app.models.auth import User
from app.models.client import Lead, Client, LeadSource
from app.schemas.client import (
    LeadCreate, LeadUpdate, LeadResponse
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.core.exceptions import ResourceNotFoundError

router = APIRouter(tags=["Leads"])


@router.get("", response_model=PaginatedResponse[LeadResponse])
async def list_leads(
    status: Optional[str] = None,
    source: Optional[str] = None,
    assigned_to: Optional[int] = None,
    client_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("lead.view")),
    db: Session = Depends(get_db)
):
    """List all leads."""
    query = db.query(Lead).filter(Lead.is_deleted == False)
    
    # Role-based filtering for Clients
    if current_user.role and current_user.role.code == 'client':
        # Find client by user email
        client = db.query(Client).filter(Client.email == current_user.email).first()
        if client:
            query = query.filter(Lead.client_id == client.id)
        else:
            # If no client found for this user, return nothing
            query = query.filter(Lead.id == -1)
    
    if status:
        query = query.filter(Lead.status == status)
        
    if source:
        # Case-insensitive source filter
        query = query.join(LeadSource).filter(LeadSource.name.ilike(f"%{source}%"))
    
    if assigned_to:
        query = query.filter(Lead.assigned_to == assigned_to)
        
    if client_id:
        query = query.filter(Lead.client_id == client_id)
    
    if search:
        query = query.filter(
            Lead.name.ilike(f"%{search}%") |
            Lead.company.ilike(f"%{search}%") |
            Lead.email.ilike(f"%{search}%")
        )
    
    total = query.count()
    
    offset = (page - 1) * page_size
    leads = query.order_by(desc(Lead.score), desc(Lead.created_at)).offset(offset).limit(page_size).all()
    
    items = [LeadResponse.model_validate(l) for l in leads]
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: int,
    current_user: User = Depends(PermissionChecker("lead.view")),
    db: Session = Depends(get_db)
):
    """Get lead by ID."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.is_deleted == False
    ).first()
    
    if not lead:
        raise ResourceNotFoundError("Lead", lead_id)
    
    return LeadResponse.model_validate(lead)


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    data: LeadCreate,
    current_user: User = Depends(PermissionChecker("lead.create")),
    db: Session = Depends(get_db)
):
    """Create a new lead."""
    lead = Lead(
        **data.model_dump(),
        created_by=current_user.id
    )
    
    db.add(lead)
    db.commit()
    db.refresh(lead)
    
    return LeadResponse.model_validate(lead)


@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: int,
    data: LeadUpdate,
    current_user: User = Depends(PermissionChecker("lead.edit")),
    db: Session = Depends(get_db)
):
    """Update a lead."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.is_deleted == False
    ).first()
    
    if not lead:
        raise ResourceNotFoundError("Lead", lead_id)
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)
    
    lead.updated_by = current_user.id
    db.commit()
    db.refresh(lead)
    
    return LeadResponse.model_validate(lead)


@router.delete("/{lead_id}", response_model=MessageResponse)
async def delete_lead(
    lead_id: int,
    current_user: User = Depends(PermissionChecker("lead.delete")),
    db: Session = Depends(get_db)
):
    """Delete a lead."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.is_deleted == False
    ).first()
    
    if not lead:
        raise ResourceNotFoundError("Lead", lead_id)
    
    lead.soft_delete(current_user.id)
    db.commit()
    
    return MessageResponse(message="Lead deleted successfully")
