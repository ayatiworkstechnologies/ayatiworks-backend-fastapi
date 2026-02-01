"""
Client and CRM API routes.
"""


from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import PermissionChecker
from app.core.exceptions import ResourceNotFoundError
from app.database import get_db
from app.models.auth import User
from app.models.client import Client, ClientContact, Deal
from app.schemas.client import (
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
    DealCreate,
    DealResponse,
    DealUpdate,
)
from app.schemas.common import MessageResponse, PaginatedResponse

router = APIRouter(tags=["CRM"])


# ============== Client Endpoints ==============

@router.get("/clients", response_model=PaginatedResponse[ClientListResponse])
async def list_clients(
    status: str | None = None,
    search: str | None = None,
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
        raise ResourceNotFoundError("Client", client_id)

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
    # Extract contacts if present
    client_data = data.model_dump()
    contacts_data = client_data.pop("contacts", [])

    client = Client(
        **client_data,
        created_by=current_user.id
    )

    db.add(client)
    db.flush()  # Generate ID

    # Create contacts
    if contacts_data:
        for contact in contacts_data:
            db.add(ClientContact(
                client_id=client.id,
                **contact
            ))

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
        raise ResourceNotFoundError("Client", client_id)

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
        raise ResourceNotFoundError("Client", client_id)

    client.soft_delete(current_user.id)
    db.commit()

    return MessageResponse(message="Client deleted successfully")


# ============== Deal Endpoints ==============

@router.get("/deals", response_model=PaginatedResponse[DealResponse])
async def list_deals(
    pipeline_id: int | None = None,
    stage: str | None = None,
    owner_id: int | None = None,
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
        raise ResourceNotFoundError("Deal", deal_id)

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

