"""
Client API routes.
Clients are now employees with the CLIENT role.
Uses the employees table instead of a separate clients table.
"""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import PermissionChecker, get_current_active_user
from app.core.exceptions import ResourceNotFoundError
from app.core.security import generate_random_password, hash_password
from app.database import get_db
from app.models.auth import Role, User
from app.models.client import Client, ClientContact, Deal
from app.models.employee import Employee
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
from app.services.employee_service import EmployeeService

router = APIRouter(tags=["CRM"])


def _get_client_role(db: Session) -> Role | None:
    """Get the CLIENT role from the database."""
    return db.query(Role).filter(Role.code == "CLIENT").first()


def _build_client_response(employee: Employee, db: Session) -> ClientResponse:
    """Build a ClientResponse from an Employee model."""
    # Check if there's a CRM Client profile linked via user_id or email
    client_profile = None
    if employee.user:
        client_profile = db.query(Client).filter(
            Client.user_id == employee.user.id,
            Client.is_deleted == False,
        ).first()
        if not client_profile and employee.user.email:
            client_profile = db.query(Client).filter(
                Client.email == employee.user.email,
                Client.is_deleted == False,
            ).first()

    return ClientResponse(
        id=employee.id,
        employee_code=employee.employee_code,
        first_name=employee.user.first_name if employee.user else "",
        last_name=employee.user.last_name if employee.user else None,
        email=employee.user.email if employee.user else "",
        phone=employee.user.phone if employee.user else None,
        avatar=employee.user.avatar if employee.user else None,
        department_id=employee.department_id,
        designation_id=employee.designation_id,
        department_name=employee.department.name if employee.department else None,
        designation_name=employee.designation.name if employee.designation else None,
        joining_date=employee.joining_date,
        employment_status=employee.employment_status,
        is_active=employee.is_active,
        company_name=client_profile.company_name if client_profile else None,
        company_id=employee.company_id,
        status=client_profile.status if client_profile else ("active" if employee.is_active else "inactive"),
        crm_client_id=client_profile.id if client_profile else None,
        crm_client_slug=client_profile.slug if client_profile else None,
        created_at=employee.created_at,
        updated_at=employee.updated_at,
    )


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
    """List all clients (employees with CLIENT role)."""
    client_role = _get_client_role(db)
    if not client_role:
        return PaginatedResponse.create([], 0, page, page_size)

    query = db.query(Employee).options(
        joinedload(Employee.user),
        joinedload(Employee.department),
        joinedload(Employee.designation),
    ).join(User, Employee.user_id == User.id).filter(
        Employee.is_deleted == False,
        User.role_id == client_role.id,
    )

    # Role-based filtering: if the user is a client, only show their own profile
    if current_user.role and current_user.role.code == 'CLIENT':
        query = query.filter(User.id == current_user.id)

    if status:
        query = query.filter(Employee.employment_status == status)

    if search:
        query = query.filter(
            User.first_name.ilike(f"%{search}%") |
            User.last_name.ilike(f"%{search}%") |
            User.email.ilike(f"%{search}%") |
            Employee.employee_code.ilike(f"%{search}%")
        )

    total = query.count()

    offset = (page - 1) * page_size
    employees = query.offset(offset).limit(page_size).all()

    # Batch-fetch CRM Client profiles to avoid N+1 queries
    employee_emails = [
        emp.user.email for emp in employees
        if emp.user and emp.user.email
    ]
    crm_clients_map = {}
    if employee_emails:
        crm_clients = db.query(Client).filter(
            Client.email.in_(employee_emails),
            Client.is_deleted == False,
        ).all()
        crm_clients_map = {c.email: c for c in crm_clients}

    items = []
    for emp in employees:
        email = emp.user.email if emp.user else None
        crm_client = crm_clients_map.get(email) if email else None

        items.append(ClientListResponse(
            id=emp.id,
            employee_code=emp.employee_code,
            first_name=emp.user.first_name if emp.user else "",
            last_name=emp.user.last_name if emp.user else None,
            email=emp.user.email if emp.user else "",
            avatar=emp.user.avatar if emp.user else None,
            department_name=emp.department.name if emp.department else None,
            designation_name=emp.designation.name if emp.designation else None,
            status=emp.employment_status,
            is_active=emp.is_active,
            crm_client_id=crm_client.id if crm_client else None,
            crm_client_slug=crm_client.slug if crm_client else None,
        ))

    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    current_user: User = Depends(PermissionChecker("client.view")),
    db: Session = Depends(get_db)
):
    """Get client by ID (employee ID)."""
    employee = db.query(Employee).options(
        joinedload(Employee.user),
        joinedload(Employee.department),
        joinedload(Employee.designation),
    ).filter(
        Employee.id == client_id,
        Employee.is_deleted == False
    ).first()

    if not employee:
        raise ResourceNotFoundError("Client", client_id)

    # Verify this employee has CLIENT role
    client_role = _get_client_role(db)
    if not client_role or not employee.user or employee.user.role_id != client_role.id:
        raise ResourceNotFoundError("Client", client_id)

    # Role-based check: clients can only view their own profile
    if current_user.role and current_user.role.code == 'CLIENT':
        if employee.user_id != current_user.id:
            raise ResourceNotFoundError("Client", client_id)

    return _build_client_response(employee, db)


@router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    data: ClientCreate,
    current_user: User = Depends(PermissionChecker("client.create")),
    db: Session = Depends(get_db)
):
    """
    Create a new client.
    Creates a User (with CLIENT role) and an Employee record.
    Optionally creates a CRM Client profile for company data.
    """
    # Get CLIENT role
    client_role = _get_client_role(db)
    if not client_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CLIENT role not found. Please seed the database first."
        )

    # Check if email already exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )

    # Create User with CLIENT role
    password = data.password or generate_random_password()
    user = User(
        email=data.email,
        password_hash=hash_password(password),
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        role_id=client_role.id,
        company_id=data.company_id if data.company_id else None,
        is_active=True,
        is_verified=True,
        created_by=current_user.id,
    )
    db.add(user)
    db.flush()

    # Generate employee code with AWC prefix for clients
    service = EmployeeService(db)
    employee_code = service.generate_employee_code(prefix="AWC")

    # Create Employee record
    employee = Employee(
        user_id=user.id,
        employee_code=employee_code,
        company_id=data.company_id if data.company_id else None,
        department_id=data.department_id if data.department_id else None,
        designation_id=data.designation_id if data.designation_id else None,
        joining_date=data.joining_date,
        employment_type=data.employment_type or "contract",
        employment_status="active",
        work_mode=data.work_mode or "remote",
        created_by=current_user.id,
    )
    db.add(employee)
    db.flush()

    # Always create CRM Client profile for modules/mail
    import re
    client_name = data.company_name or f"{data.first_name} {data.last_name or ''}".strip()
    client_slug = client_name.lower().strip()
    client_slug = re.sub(r'[^\w\s-]', '', client_slug)
    client_slug = re.sub(r'[\s_]+', '-', client_slug)

    client_profile = Client(
        name=client_name,
        slug=client_slug,
        email=data.email,
        phone=data.phone,
        company_name=data.company_name,
        company_id=data.company_id if data.company_id else None,
        industry=data.industry,
        address=data.address,
        city=data.city,
        state=data.state,
        country=data.country,
        status="active",
        user_id=user.id,
        manager_id=employee.id,
        created_by=current_user.id,
    )
    db.add(client_profile)

    db.commit()
    db.refresh(employee)

    # Send welcome email
    try:
        from app.services.email_service import email_service, employee_welcome_email

        subject, html_content = employee_welcome_email(
            first_name=user.first_name,
            last_name=user.last_name or "",
            email=user.email,
            employee_code=employee.employee_code,
            department=employee.department.name if employee.department else "N/A",
            designation=employee.designation.name if employee.designation else "N/A",
            joining_date=str(employee.joining_date),
            password=password,
        )
        email_service.send_email(
            to_email=user.email,
            subject=subject,
            html_content=html_content,
        )
    except Exception as e:
        import logging
        logging.error(f"Failed to send client welcome email: {e}")

    return _build_client_response(employee, db)


@router.put("/clients/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    data: ClientUpdate,
    current_user: User = Depends(PermissionChecker("client.edit")),
    db: Session = Depends(get_db)
):
    """Update a client (employee with CLIENT role)."""
    employee = db.query(Employee).options(
        joinedload(Employee.user),
        joinedload(Employee.department),
        joinedload(Employee.designation),
    ).filter(
        Employee.id == client_id,
        Employee.is_deleted == False
    ).first()

    if not employee:
        raise ResourceNotFoundError("Client", client_id)

    # Verify this employee has CLIENT role
    client_role = _get_client_role(db)
    if not client_role or not employee.user or employee.user.role_id != client_role.id:
        raise ResourceNotFoundError("Client", client_id)

    update_data = data.model_dump(exclude_unset=True)

    # Update User fields
    user_fields = {'first_name', 'last_name', 'email', 'phone'}
    for field in user_fields:
        if field in update_data and employee.user:
            setattr(employee.user, field, update_data.pop(field))

    # Update Employee fields
    emp_fields = {'department_id', 'designation_id', 'manager_id'}
    for field in emp_fields:
        if field in update_data:
            val = update_data.pop(field)
            setattr(employee, field, val if val else None)

    # Update status
    if 'status' in update_data:
        status_val = update_data.pop('status')
        if status_val in ('active', 'inactive'):
            employee.is_active = status_val == 'active'
            employee.employment_status = status_val

    # Update CRM Client profile if exists
    crm_fields = {'company_name', 'industry', 'address', 'city', 'state', 'country', 'tags'}
    crm_data = {k: v for k, v in update_data.items() if k in crm_fields}
    if crm_data and employee.user:
        client_profile = db.query(Client).filter(
            Client.user_id == employee.user.id,
            Client.is_deleted == False,
        ).first()
        if not client_profile and employee.user.email:
            client_profile = db.query(Client).filter(
                Client.email == employee.user.email,
                Client.is_deleted == False,
            ).first()
        if client_profile:
            for field, value in crm_data.items():
                setattr(client_profile, field, value)

    employee.updated_by = current_user.id
    db.commit()
    db.refresh(employee)

    return _build_client_response(employee, db)


@router.delete("/clients/{client_id}", response_model=MessageResponse)
async def delete_client(
    client_id: int,
    current_user: User = Depends(PermissionChecker("client.delete")),
    db: Session = Depends(get_db)
):
    """Delete a client (soft delete employee with CLIENT role)."""
    employee = db.query(Employee).join(User).filter(
        Employee.id == client_id,
        Employee.is_deleted == False
    ).first()

    if not employee:
        raise ResourceNotFoundError("Client", client_id)

    # Verify this employee has CLIENT role
    client_role = _get_client_role(db)
    if not client_role or not employee.user or employee.user.role_id != client_role.id:
        raise ResourceNotFoundError("Client", client_id)

    employee.soft_delete(current_user.id)
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
