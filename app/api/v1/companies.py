"""
Company and Branch API routes.
"""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import PermissionChecker
from app.core.exceptions import ResourceNotFoundError
from app.database import get_db
from app.models.auth import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.company import (
    BranchCreate,
    BranchListResponse,
    BranchResponse,
    BranchUpdate,
    CompanyCreate,
    CompanyListResponse,
    CompanyResponse,
    CompanyUpdate,
)
from app.services.company_service import BranchService, CompanyService

router = APIRouter(tags=["Companies & Branches"])


# ============== Company Endpoints ==============

@router.get("/companies", response_model=PaginatedResponse[CompanyListResponse])
async def list_companies(
    search: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("company.view")),
    db: Session = Depends(get_db)
):
    """List all companies."""
    service = CompanyService(db)

    companies, total = service.get_all(
        search=search,
        is_active=is_active,
        page=page,
        page_size=page_size
    )

    items = [CompanyListResponse.model_validate(c) for c in companies]
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int,
    current_user: User = Depends(PermissionChecker("company.view")),
    db: Session = Depends(get_db)
):
    """Get company by ID."""
    print(f"DEBUG: Entering get_company id={company_id}")
    service = CompanyService(db)
    company = service.get_by_id(company_id)
    print(f"DEBUG: Company found: {company}")

    if not company:
        raise ResourceNotFoundError("Company", company_id)

    print("DEBUG: Validating model")
    response = CompanyResponse.model_validate(company)
    print("DEBUG: Getting counts")
    response.branch_count = service.get_branch_count(company_id)
    response.employee_count = service.get_employee_count(company_id)
    print("DEBUG: Returning response")

    return response


@router.post("/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    data: CompanyCreate,
    current_user: User = Depends(PermissionChecker("company.create")),
    db: Session = Depends(get_db)
):
    """Create a new company."""
    service = CompanyService(db)

    # Check if code exists
    if service.get_by_code(data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company code already exists"
        )

    company = service.create(data, created_by=current_user.id)
    return CompanyResponse.model_validate(company)


@router.put("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    data: CompanyUpdate,
    current_user: User = Depends(PermissionChecker("company.edit")),
    db: Session = Depends(get_db)
):
    """Update a company."""
    service = CompanyService(db)

    company = service.update(company_id, data, updated_by=current_user.id)

    if not company:
        raise ResourceNotFoundError("Company", company_id)

    return CompanyResponse.model_validate(company)


@router.delete("/companies/{company_id}", response_model=MessageResponse)
async def delete_company(
    company_id: int,
    current_user: User = Depends(PermissionChecker("company.delete")),
    db: Session = Depends(get_db)
):
    """Delete a company (soft delete)."""
    service = CompanyService(db)

    if not service.delete(company_id, deleted_by=current_user.id):
        raise ResourceNotFoundError("Company", company_id)

    return MessageResponse(message="Company deleted successfully")


# ============== Branch Endpoints ==============

@router.get("/branches", response_model=PaginatedResponse[BranchListResponse])
async def list_branches(
    company_id: int | None = None,
    search: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("branch.view")),
    db: Session = Depends(get_db)
):
    """List all branches."""
    service = BranchService(db)

    branches, total = service.get_all(
        company_id=company_id,
        search=search,
        is_active=is_active,
        page=page,
        page_size=page_size
    )

    items = [BranchListResponse.model_validate(b) for b in branches]
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/companies/{company_id}/branches", response_model=list[BranchListResponse])
async def get_company_branches(
    company_id: int,
    current_user: User = Depends(PermissionChecker("branch.view")),
    db: Session = Depends(get_db)
):
    """Get all branches for a company."""
    service = BranchService(db)
    branches = service.get_by_company(company_id)
    return [BranchListResponse.model_validate(b) for b in branches]


@router.get("/branches/{branch_id}", response_model=BranchResponse)
async def get_branch(
    branch_id: int,
    current_user: User = Depends(PermissionChecker("branch.view")),
    db: Session = Depends(get_db)
):
    """Get branch by ID."""
    service = BranchService(db)
    branch = service.get_by_id(branch_id)

    if not branch:
        raise ResourceNotFoundError("Branch", branch_id)

    response = BranchResponse.model_validate(branch)
    response.company_name = branch.company.name if branch.company else None
    response.employee_count = service.get_employee_count(branch_id)

    return response


@router.post("/branches", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def create_branch(
    data: BranchCreate,
    current_user: User = Depends(PermissionChecker("branch.create")),
    db: Session = Depends(get_db)
):
    """Create a new branch."""
    service = BranchService(db)

    # Check if code exists in company
    if service.get_by_code(data.company_id, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Branch code already exists in this company"
        )

    branch = service.create(data, created_by=current_user.id)
    return BranchResponse.model_validate(branch)


@router.put("/branches/{branch_id}", response_model=BranchResponse)
async def update_branch(
    branch_id: int,
    data: BranchUpdate,
    current_user: User = Depends(PermissionChecker("branch.edit")),
    db: Session = Depends(get_db)
):
    """Update a branch."""
    service = BranchService(db)

    branch = service.update(branch_id, data, updated_by=current_user.id)

    if not branch:
        raise ResourceNotFoundError("Branch", branch_id)

    return BranchResponse.model_validate(branch)


@router.delete("/branches/{branch_id}", response_model=MessageResponse)
async def delete_branch(
    branch_id: int,
    current_user: User = Depends(PermissionChecker("branch.delete")),
    db: Session = Depends(get_db)
):
    """Delete a branch (soft delete)."""
    service = BranchService(db)

    if not service.delete(branch_id, deleted_by=current_user.id):
        raise ResourceNotFoundError("Branch", branch_id)

    return MessageResponse(message="Branch deleted successfully")

