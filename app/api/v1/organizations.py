"""
Department and Designation API routes.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_active_user, PermissionChecker
from app.models.auth import User
from app.services.organization_service import DepartmentService, DesignationService
from app.schemas.organization import (
    DepartmentCreate, DepartmentUpdate, DepartmentResponse, DepartmentListResponse, DepartmentTreeResponse,
    DesignationCreate, DesignationUpdate, DesignationResponse, DesignationListResponse
)
from app.schemas.common import PaginatedResponse, MessageResponse


router = APIRouter(tags=["Departments & Designations"])


# ============== Department Endpoints ==============

@router.get("/departments", response_model=PaginatedResponse[DepartmentListResponse])
async def list_departments(
    company_id: Optional[int] = None,
    parent_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("department.view")),
    db: Session = Depends(get_db)
):
    """List all departments."""
    print("DEBUG: Entering list_departments")
    service = DepartmentService(db)
    
    departments, total = service.get_all(
        company_id=company_id,
        parent_id=parent_id,
        search=search,
        page=page,
        page_size=page_size
    )
    print(f"DEBUG: Found {len(departments)} departments. Total: {total}")
    
    # Debug individual items
    items = []
    for d in departments:
        # print(f"DEBUG: Validating dept {d.id} {d.name}")
        try:
            item = DepartmentListResponse.model_validate(d)
            items.append(item)
        except Exception as e:
            print(f"DEBUG: Validation failed for dept {d.id}: {e}")
            raise e

    print("DEBUG: Validation complete. Creating PaginatedResponse")
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/companies/{company_id}/departments/tree", response_model=list[DepartmentTreeResponse])
async def get_department_tree(
    company_id: int,
    current_user: User = Depends(PermissionChecker("department.view")),
    db: Session = Depends(get_db)
):
    """Get department hierarchy tree for a company."""
    service = DepartmentService(db)
    root_departments = service.get_tree(company_id)
    
    def build_tree(dept):
        return DepartmentTreeResponse(
            id=dept.id,
            name=dept.name,
            code=dept.code,
            level=dept.level,
            children=[build_tree(child) for child in dept.children if not child.is_deleted]
        )
    
    return [build_tree(d) for d in root_departments]


@router.get("/departments/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: int,
    current_user: User = Depends(PermissionChecker("department.view")),
    db: Session = Depends(get_db)
):
    """Get department by ID."""
    service = DepartmentService(db)
    department = service.get_by_id(department_id)
    
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    response = DepartmentResponse.model_validate(department)
    response.parent_name = department.parent.name if department.parent else None
    response.employee_count = service.get_employee_count(department_id)
    
    return response


@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    data: DepartmentCreate,
    current_user: User = Depends(PermissionChecker("department.create")),
    db: Session = Depends(get_db)
):
    """Create a new department."""
    service = DepartmentService(db)
    
    # Check if code exists in company
    if service.get_by_code(data.company_id, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department code already exists in this company"
        )
    
    department = service.create(data, created_by=current_user.id)
    return DepartmentResponse.model_validate(department)


@router.put("/departments/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: int,
    data: DepartmentUpdate,
    current_user: User = Depends(PermissionChecker("department.edit")),
    db: Session = Depends(get_db)
):
    """Update a department."""
    service = DepartmentService(db)
    
    department = service.update(department_id, data, updated_by=current_user.id)
    
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    return DepartmentResponse.model_validate(department)


@router.delete("/departments/{department_id}", response_model=MessageResponse)
async def delete_department(
    department_id: int,
    current_user: User = Depends(PermissionChecker("department.delete")),
    db: Session = Depends(get_db)
):
    """Delete a department (soft delete)."""
    service = DepartmentService(db)
    
    if not service.delete(department_id, deleted_by=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    return MessageResponse(message="Department deleted successfully")


# ============== Designation Endpoints ==============

@router.get("/designations", response_model=PaginatedResponse[DesignationListResponse])
async def list_designations(
    department_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("designation.view")),
    db: Session = Depends(get_db)
):
    """List all designations."""
    service = DesignationService(db)
    
    designations, total = service.get_all(
        department_id=department_id,
        search=search,
        page=page,
        page_size=page_size
    )
    
    items = [DesignationListResponse.model_validate(d) for d in designations]
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/designations/{designation_id}", response_model=DesignationResponse)
async def get_designation(
    designation_id: int,
    current_user: User = Depends(PermissionChecker("designation.view")),
    db: Session = Depends(get_db)
):
    """Get designation by ID."""
    service = DesignationService(db)
    designation = service.get_by_id(designation_id)
    
    if not designation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Designation not found"
        )
    
    response = DesignationResponse.model_validate(designation)
    response.department_name = designation.department.name if designation.department else None
    response.employee_count = service.get_employee_count(designation_id)
    
    return response


@router.post("/designations", response_model=DesignationResponse, status_code=status.HTTP_201_CREATED)
async def create_designation(
    data: DesignationCreate,
    current_user: User = Depends(PermissionChecker("designation.create")),
    db: Session = Depends(get_db)
):
    """Create a new designation."""
    service = DesignationService(db)
    
    # Check if code exists
    if service.get_by_code(data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Designation code already exists"
        )
    
    designation = service.create(data, created_by=current_user.id)
    return DesignationResponse.model_validate(designation)


@router.put("/designations/{designation_id}", response_model=DesignationResponse)
async def update_designation(
    designation_id: int,
    data: DesignationUpdate,
    current_user: User = Depends(PermissionChecker("designation.edit")),
    db: Session = Depends(get_db)
):
    """Update a designation."""
    service = DesignationService(db)
    
    designation = service.update(designation_id, data, updated_by=current_user.id)
    
    if not designation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Designation not found"
        )
    
    return DesignationResponse.model_validate(designation)


@router.delete("/designations/{designation_id}", response_model=MessageResponse)
async def delete_designation(
    designation_id: int,
    current_user: User = Depends(PermissionChecker("designation.delete")),
    db: Session = Depends(get_db)
):
    """Delete a designation (soft delete)."""
    service = DesignationService(db)
    
    if not service.delete(designation_id, deleted_by=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Designation not found"
        )
    
    return MessageResponse(message="Designation deleted successfully")
