"""
Client and CRM API routes.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_active_user, PermissionChecker
from app.models.auth import User
from app.models.client import Client, ClientContact, Lead, Deal, LeadSource
from app.schemas.client import (
    ClientCreate, ClientUpdate, ClientResponse, ClientListResponse,
    LeadCreate, LeadUpdate, LeadResponse,
    DealCreate, DealUpdate, DealResponse
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.core.exceptions import (
    ResourceNotFoundError,
    ResourceAlreadyExistsError,
    InvalidCredentialsError,
    PermissionDeniedError,
    ValidationError,
    BusinessLogicError
)


router = APIRouter(tags=["CRM"])


# ============== Client Endpoints ==============

@router.get("/clients", response_model=PaginatedResponse[ClientListResponse])
async def list_clients(
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("client.view")),
    db: Session = Depends(get_db)
):
    """List all clients."""
    query = db.query(Client).filter(Client.is_deleted == False)
    
    # Role-based filtering
    if current_user.role and current_user.role.code == 'client':
        query = query.filter(Client.email == current_user.email)
    
    if status:
        query = query.filter(Client.status == status)
    
    if search:
        query = query.filter(
            Client.name.ilike(f"%{search}%") |
            Client.company_name.ilike(f"%{search}%") |
            Client.email.ilike(f"%{search}%")
        )
    
    total = query.count()
    
    offset = (page - 1) * page_size
    clients = query.offset(offset).limit(page_size).all()
    
    items = [ClientListResponse.model_validate(c) for c in clients]
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    current_user: User = Depends(PermissionChecker("client.view")),
    db: Session = Depends(get_db)
):
    """Get client by ID."""
    query = db.query(Client).filter(
        Client.id == client_id,
        Client.is_deleted == False
    )
    
    # Role-based filtering
    if current_user.role and current_user.role.code == 'client':
        query = query.filter(Client.email == current_user.email)
        
    client = query.first()
    
    if not client:
        raise ResourceNotFoundError("Client", Client_id)
    
    response = ClientResponse.model_validate(client)
    response.project_count = len(client.projects)
    response.invoice_count = len(client.invoices)
    
    return response


@router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    data: ClientCreate,
    current_user: User = Depends(PermissionChecker("client.create")),
    db: Session = Depends(get_db)
):
    """Create a new client."""
    client = Client(
        **data.model_dump(),
        created_by=current_user.id
    )
    
    db.add(client)
    db.commit()
    db.refresh(client)
    
    return ClientResponse.model_validate(client)


@router.put("/clients/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    data: ClientUpdate,
    current_user: User = Depends(PermissionChecker("client.edit")),
    db: Session = Depends(get_db)
):
    """Update a client."""
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.is_deleted == False
    ).first()
    
    if not client:
        raise ResourceNotFoundError("Client", Client_id)
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)
    
    client.updated_by = current_user.id
    db.commit()
    db.refresh(client)
    
    return ClientResponse.model_validate(client)


@router.delete("/clients/{client_id}", response_model=MessageResponse)
async def delete_client(
    client_id: int,
    current_user: User = Depends(PermissionChecker("client.delete")),
    db: Session = Depends(get_db)
):
    """Delete a client."""
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.is_deleted == False
    ).first()
    
    if not client:
        raise ResourceNotFoundError("Client", Client_id)
    
    client.soft_delete(current_user.id)
    db.commit()
    
    return MessageResponse(message="Client deleted successfully")


# ============== Lead Endpoints ==============

@router.get("/leads", response_model=PaginatedResponse[LeadResponse])
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
    leads = query.order_by(Lead.score.desc()).offset(offset).limit(page_size).all()
    
    items = [LeadResponse.model_validate(l) for l in leads]
    return PaginatedResponse.create(items, total, page, page_size)


@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
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


@router.put("/leads/{lead_id}", response_model=LeadResponse)
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
        raise ResourceNotFoundError("Lead", Lead_id)
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)
    
    lead.updated_by = current_user.id
    db.commit()
    db.refresh(lead)
    
    return LeadResponse.model_validate(lead)


# ============== Deal Endpoints ==============

@router.get("/deals", response_model=PaginatedResponse[DealResponse])
async def list_deals(
    pipeline_id: Optional[int] = None,
    stage: Optional[str] = None,
    owner_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("deal.view")),
    db: Session = Depends(get_db)
):
    """List all deals."""
    query = db.query(Deal).filter(Deal.is_deleted == False)
    
    if pipeline_id:
        query = query.filter(Deal.pipeline_id == pipeline_id)
    
    if stage:
        query = query.filter(Deal.stage == stage)
    
    if owner_id:
        query = query.filter(Deal.owner_id == owner_id)
    
    total = query.count()
    
    offset = (page - 1) * page_size
    deals = query.order_by(Deal.value.desc()).offset(offset).limit(page_size).all()
    
    items = [DealResponse.model_validate(d) for d in deals]
    return PaginatedResponse.create(items, total, page, page_size)


@router.post("/deals", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
async def create_deal(
    data: DealCreate,
    current_user: User = Depends(PermissionChecker("deal.create")),
    db: Session = Depends(get_db)
):
    """Create a new deal."""
    deal = Deal(
        **data.model_dump(),
        created_by=current_user.id
    )
    
    db.add(deal)
    db.commit()
    db.refresh(deal)
    
    return DealResponse.model_validate(deal)


@router.put("/deals/{deal_id}", response_model=DealResponse)
async def update_deal(
    deal_id: int,
    data: DealUpdate,
    current_user: User = Depends(PermissionChecker("deal.edit")),
    db: Session = Depends(get_db)
):
    """Update a deal."""
    deal = db.query(Deal).filter(
        Deal.id == deal_id,
        Deal.is_deleted == False
    ).first()
    
    if not deal:
        raise ResourceNotFoundError("Deal", Deal_id)
    
    update_data = data.model_dump(exclude_unset=True)
    
    # Calculate weighted value
    if 'probability' in update_data or 'value' in update_data:
        value = update_data.get('value', deal.value) or 0
        prob = update_data.get('probability', deal.probability) or 0
        deal.weighted_value = value * (prob / 100)
    
    for field, value in update_data.items():
        setattr(deal, field, value)
    
    deal.updated_by = current_user.id
    db.commit()
    db.refresh(deal)
    
    return DealResponse.model_validate(deal)
