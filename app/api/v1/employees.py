"""
Employee API routes.
Employee CRUD and management.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_active_user, PermissionChecker
from app.models.auth import User
from app.services.employee_service import EmployeeService
from app.schemas.employee import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeListResponse,
    EmployeeDocumentCreate, EmployeeDocumentResponse, EmployeeTeamResponse
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.core.exceptions import ResourceNotFoundError, PermissionDeniedError


router = APIRouter(prefix="/employees", tags=["Employees"])


def build_employee_response(employee) -> EmployeeResponse:
    """Helper function to build EmployeeResponse from Employee model."""
    
    # Build teams list
    teams_data = []
    if hasattr(employee, 'team_memberships') and employee.team_memberships:
        for tm in employee.team_memberships:
            if tm.team:
                teams_data.append(EmployeeTeamResponse(
                    id=tm.team.id,
                    name=tm.team.name,
                    code=tm.team.code,
                    team_type=tm.team.team_type,
                    role=tm.role,
                    joined_date=tm.joined_date
                ))
    
    return EmployeeResponse(
        id=employee.id,
        user_id=employee.user_id,
        employee_code=employee.employee_code,
        company_id=employee.company_id,
        branch_id=employee.branch_id,
        department_id=employee.department_id,
        designation_id=employee.designation_id,
        manager_id=employee.manager_id,
        joining_date=employee.joining_date,
        probation_end_date=employee.probation_end_date,
        confirmation_date=employee.confirmation_date,
        employment_type=employee.employment_type,
        employment_status=employee.employment_status,
        work_mode=employee.work_mode,
        shift_id=employee.shift_id,
        is_active=employee.is_active,
        date_of_birth=employee.date_of_birth,
        gender=employee.gender,
        blood_group=employee.blood_group,
        marital_status=employee.marital_status,
        nationality=employee.nationality,
        personal_email=employee.personal_email,
        personal_phone=employee.personal_phone,
        emergency_contact_name=employee.emergency_contact_name,
        emergency_contact_phone=employee.emergency_contact_phone,
        emergency_contact_relation=employee.emergency_contact_relation,
        current_address=employee.current_address,
        permanent_address=employee.permanent_address,
        city=employee.city,
        state=employee.state,
        country=employee.country,
        postal_code=employee.postal_code,
        created_at=employee.created_at,
        updated_at=employee.updated_at,
        user={
            "id": employee.user.id,
            "email": employee.user.email,
            "first_name": employee.user.first_name,
            "last_name": employee.user.last_name,
            "phone": employee.user.phone,
            "avatar": employee.user.avatar
        } if employee.user else None,
        department_name=employee.department.name if employee.department else None,
        designation_name=employee.designation.name if employee.designation else None,
        manager_name=employee.manager.user.full_name if employee.manager and employee.manager.user else None,
        teams=teams_data
    )


@router.get("", response_model=PaginatedResponse[EmployeeListResponse])
async def list_employees(
    company_id: Optional[int] = None,
    branch_id: Optional[int] = None,
    department_id: Optional[int] = None,
    designation_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("employee.view_all")),
    db: Session = Depends(get_db)
):
    """List all employees with filters and pagination."""
    service = EmployeeService(db)
    
    employees, total = service.get_all(
        company_id=company_id,
        branch_id=branch_id,
        department_id=department_id,
        designation_id=designation_id,
        status=status,
        search=search,
        page=page,
        page_size=page_size
    )
    
    # Convert to response format
    items = []
    for emp in employees:
        items.append(EmployeeListResponse(
            id=emp.id,
            user_id=emp.user_id,
            employee_code=emp.employee_code,
            first_name=emp.user.first_name if emp.user else "",
            last_name=emp.user.last_name if emp.user else None,
            email=emp.user.email if emp.user else "",
            department_name=emp.department.name if emp.department else None,
            designation_name=emp.designation.name if emp.designation else None,
            employment_status=emp.employment_status,
            is_active=emp.is_active
        ))
    
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/me", response_model=EmployeeResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's employee profile."""
    service = EmployeeService(db)
    
    employee = service.get_by_user_id(current_user.id)
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )
    
    return build_employee_response(employee)


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    current_user: User = Depends(PermissionChecker("employee.view")),
    db: Session = Depends(get_db)
):
    """Get employee by ID."""
    service = EmployeeService(db)
    
    employee = service.get_by_id(employee_id)
    
    if not employee:
        raise ResourceNotFoundError("Employee", Employee_id)
    
    return build_employee_response(employee)


@router.get("/code/{code}", response_model=EmployeeResponse)
async def get_employee_by_code(
    code: str,
    current_user: User = Depends(PermissionChecker("employee.view")),
    db: Session = Depends(get_db)
):
    """Get employee by employee code (e.g., AW0001)."""
    service = EmployeeService(db)
    
    employee = service.get_by_code(code.upper())
    
    if not employee:
        raise ResourceNotFoundError("Employee", Employee_id)
    
    return build_employee_response(employee)


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    data: EmployeeCreate,
    current_user: User = Depends(PermissionChecker("employee.create")),
    db: Session = Depends(get_db)
):
    """
    Create a new employee.
    If user_id is not provided, a new user account will be created.
    Employee code (like AW0001) is auto-generated.
    A welcome email will be sent to the new employee.
    """
    from app.services.email_service import email_service, employee_welcome_email
    
    service = EmployeeService(db)
    
    # Store password before hashing (for email)
    raw_password = data.password
    
    try:
        employee = service.create(data, created_by=current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Send welcome email
    try:
        department_name = employee.department.name if employee.department else "N/A"
        designation_name = employee.designation.name if employee.designation else "N/A"
        
        subject, html_content = employee_welcome_email(
            first_name=employee.user.first_name,
            last_name=employee.user.last_name or "",
            email=employee.user.email,
            employee_code=employee.employee_code,
            department=department_name,
            designation=designation_name,
            joining_date=str(employee.joining_date),
            password=raw_password  # Only include if new user was created
        )
        
        email_service.send_email(
            to_email=employee.user.email,
            subject=subject,
            html_content=html_content
        )
    except Exception as e:
        # Log email error but don't fail the request
        import logging
        logging.error(f"Failed to send welcome email: {e}")
    
    return build_employee_response(employee)


@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    current_user: User = Depends(PermissionChecker("employee.edit")),
    db: Session = Depends(get_db)
):
    """Update an employee."""
    service = EmployeeService(db)
    
    employee = service.update(employee_id, data, updated_by=current_user.id)
    
    if not employee:
        raise ResourceNotFoundError("Employee", Employee_id)
    
    return build_employee_response(employee)


@router.delete("/{employee_id}", response_model=MessageResponse)
async def delete_employee(
    employee_id: int,
    current_user: User = Depends(PermissionChecker("employee.delete")),
    db: Session = Depends(get_db)
):
    """Delete an employee (soft delete)."""
    service = EmployeeService(db)
    
    if not service.delete(employee_id, deleted_by=current_user.id):
        raise ResourceNotFoundError("Employee", Employee_id)
    
    return MessageResponse(message="Employee deleted successfully")


@router.get("/{employee_id}/team", response_model=list[EmployeeListResponse])
async def get_team_members(
    employee_id: int,
    current_user: User = Depends(PermissionChecker("employee.view")),
    db: Session = Depends(get_db)
):
    """Get all team members under an employee (manager)."""
    service = EmployeeService(db)
    
    employees = service.get_team_members(employee_id)
    
    items = []
    for emp in employees:
        items.append(EmployeeListResponse(
            id=emp.id,
            user_id=emp.user_id,
            employee_code=emp.employee_code,
            first_name=emp.user.first_name if emp.user else "",
            last_name=emp.user.last_name if emp.user else None,
            email=emp.user.email if emp.user else "",
            department_name=emp.department.name if emp.department else None,
            designation_name=emp.designation.name if emp.designation else None,
            employment_status=emp.employment_status,
            is_active=emp.is_active
        ))
    return items


# Document endpoints
@router.get("/{employee_id}/documents", response_model=list[EmployeeDocumentResponse])
async def get_employee_documents(
    employee_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all documents for an employee."""
    service = EmployeeService(db)
    
    # Check if user can view this employee's documents
    employee = service.get_by_id(employee_id)
    if not employee:
        raise ResourceNotFoundError("Employee", Employee_id)
    
    documents = service.get_documents(employee_id)
    
    return [EmployeeDocumentResponse.model_validate(doc) for doc in documents]


@router.post("/{employee_id}/documents/{document_id}/verify", response_model=EmployeeDocumentResponse)
async def verify_document(
    employee_id: int,
    document_id: int,
    current_user: User = Depends(PermissionChecker("employee.edit")),
    db: Session = Depends(get_db)
):
    """Mark a document as verified."""
    service = EmployeeService(db)
    
    document = service.verify_document(document_id, verified_by=current_user.id)
    
    if not document:
        raise ResourceNotFoundError("Document", Document_id)
    
    return EmployeeDocumentResponse.model_validate(document)
