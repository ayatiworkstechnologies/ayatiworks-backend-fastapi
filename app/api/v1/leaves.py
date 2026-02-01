"""
Leave and Holiday API routes.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import PermissionChecker, get_current_active_user
from app.core.exceptions import ResourceNotFoundError
from app.database import get_db
from app.models.auth import User
from app.models.leave import LeaveType
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.leave import (
    HolidayCreate,
    HolidayResponse,
    LeaveApprovalRequest,
    LeaveBalanceResponse,
    LeaveCancelRequest,
    LeaveCreate,
    LeaveListResponse,
    LeaveResponse,
    LeaveTypeCreate,
    LeaveTypeResponse,
)
from app.services.employee_service import EmployeeService
from app.services.leave_service import HolidayService, LeaveService

router = APIRouter(tags=["Leave & Holidays"])


# ============== Leave Balance ==============

@router.get("/leaves/my-balance", response_model=list[LeaveBalanceResponse])
async def get_my_leave_balance(
    year: int = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's leave balance."""
    if year is None:
        year = date.today().year

    emp_service = EmployeeService(db)
    employee = emp_service.get_by_user_id(current_user.id)

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )

    leave_service = LeaveService(db)
    balances = leave_service.get_all_balances(employee.id, year)

    return balances


# ============== Leave Application ==============

@router.post("/leaves", response_model=LeaveResponse, status_code=status.HTTP_201_CREATED)
async def apply_leave(
    data: LeaveCreate,
    current_user: User = Depends(PermissionChecker("leave.apply")),
    db: Session = Depends(get_db)
):
    """Apply for leave."""
    emp_service = EmployeeService(db)
    employee = emp_service.get_by_user_id(current_user.id)

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )

    leave_service = LeaveService(db)

    try:
        leave = leave_service.apply_leave(employee.id, data, created_by=current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return LeaveResponse.model_validate(leave)


@router.get("/leaves/my-leaves", response_model=PaginatedResponse[LeaveListResponse])
async def get_my_leaves(
    year: int | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's leave history."""
    emp_service = EmployeeService(db)
    employee = emp_service.get_by_user_id(current_user.id)

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )

    leave_service = LeaveService(db)
    leaves, total = leave_service.get_employee_leaves(
        employee_id=employee.id,
        year=year,
        status=status,
        page=page,
        page_size=page_size
    )

    items = []
    for leave in leaves:
        items.append(LeaveListResponse(
            id=leave.id,
            employee_id=leave.employee_id,
            employee_name=current_user.full_name,
            leave_type_name=leave.leave_type.name if leave.leave_type else "",
            leave_type_color=leave.leave_type.color if leave.leave_type else "#3B82F6",
            from_date=leave.from_date,
            to_date=leave.to_date,
            days=leave.days,
            status=leave.status
        ))

    return PaginatedResponse.create(items, total, page, page_size)


@router.post("/leaves/{leave_id}/cancel", response_model=LeaveResponse)
async def cancel_leave(
    leave_id: int,
    data: LeaveCancelRequest,
    current_user: User = Depends(PermissionChecker("leave.cancel")),
    db: Session = Depends(get_db)
):
    """Cancel a leave request."""
    leave_service = LeaveService(db)

    try:
        leave = leave_service.cancel_leave(leave_id, current_user.id, data.reason)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    if not leave:
        raise ResourceNotFoundError("Leave", leave_id)

    return LeaveResponse.model_validate(leave)


# ============== Leave Approval ==============

@router.get("/leaves/pending-approvals", response_model=list[LeaveListResponse])
async def get_pending_approvals(
    current_user: User = Depends(PermissionChecker("leave.approve")),
    db: Session = Depends(get_db)
):
    """Get pending leave requests for approval."""
    emp_service = EmployeeService(db)
    employee = emp_service.get_by_user_id(current_user.id)

    if not employee:
        return []

    leave_service = LeaveService(db)
    leaves = leave_service.get_pending_approvals(employee.id)

    items = []
    for leave in leaves:
        items.append(LeaveListResponse(
            id=leave.id,
            employee_id=leave.employee_id,
            employee_name=leave.employee.user.full_name if leave.employee and leave.employee.user else "",
            leave_type_name=leave.leave_type.name if leave.leave_type else "",
            leave_type_color=leave.leave_type.color if leave.leave_type else "#3B82F6",
            from_date=leave.from_date,
            to_date=leave.to_date,
            days=leave.days,
            status=leave.status
        ))

    return items


@router.post("/leaves/{leave_id}/approve", response_model=LeaveResponse)
async def approve_or_reject_leave(
    leave_id: int,
    data: LeaveApprovalRequest,
    current_user: User = Depends(PermissionChecker("leave.approve")),
    db: Session = Depends(get_db)
):
    """Approve or reject a leave request."""
    leave_service = LeaveService(db)

    try:
        leave = leave_service.approve_leave(leave_id, current_user.id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    if not leave:
        raise ResourceNotFoundError("Leave", leave_id)

    return LeaveResponse.model_validate(leave)


# ============== Leave Types ==============

@router.get("/leave-types", response_model=list[LeaveTypeResponse])
async def list_leave_types(
    company_id: int | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all leave types."""
    query = db.query(LeaveType).filter(
        LeaveType.is_deleted == False,
        LeaveType.is_active == True
    )

    if company_id:
        query = query.filter(
            (LeaveType.company_id == company_id) | (LeaveType.company_id is None)
        )

    leave_types = query.all()
    return [LeaveTypeResponse.model_validate(lt) for lt in leave_types]


@router.post("/leave-types", response_model=LeaveTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_leave_type(
    data: LeaveTypeCreate,
    current_user: User = Depends(PermissionChecker("leave.approve")),
    db: Session = Depends(get_db)
):
    """Create a new leave type."""
    leave_type = LeaveType(
        **data.model_dump(),
        created_by=current_user.id
    )

    db.add(leave_type)
    db.commit()
    db.refresh(leave_type)

    return LeaveTypeResponse.model_validate(leave_type)


# ============== Holidays ==============

@router.get("/holidays", response_model=PaginatedResponse[HolidayResponse])
async def list_holidays(
    company_id: int | None = None,
    year: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all holidays."""
    holiday_service = HolidayService(db)

    if year is None:
        year = date.today().year

    holidays, total = holiday_service.get_all(
        company_id=company_id,
        year=year,
        page=page,
        page_size=page_size
    )

    items = [HolidayResponse.model_validate(h) for h in holidays]
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/holidays/upcoming", response_model=list[HolidayResponse])
async def get_upcoming_holidays(
    company_id: int | None = None,
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get upcoming holidays."""
    holiday_service = HolidayService(db)
    holidays = holiday_service.get_upcoming(company_id, limit)
    return [HolidayResponse.model_validate(h) for h in holidays]


@router.post("/holidays", response_model=HolidayResponse, status_code=status.HTTP_201_CREATED)
async def create_holiday(
    data: HolidayCreate,
    current_user: User = Depends(PermissionChecker("holiday.manage")),
    db: Session = Depends(get_db)
):
    """Create a new holiday."""
    holiday_service = HolidayService(db)

    holiday = holiday_service.create(
        company_id=data.company_id,
        name=data.name,
        holiday_date=data.date,
        holiday_type=data.holiday_type,
        created_by=current_user.id
    )

    return HolidayResponse.model_validate(holiday)


@router.delete("/holidays/{holiday_id}", response_model=MessageResponse)
async def delete_holiday(
    holiday_id: int,
    current_user: User = Depends(PermissionChecker("holiday.manage")),
    db: Session = Depends(get_db)
):
    """Delete a holiday."""
    holiday_service = HolidayService(db)

    if not holiday_service.delete(holiday_id, current_user.id):
        raise ResourceNotFoundError("Holiday", holiday_id)

    return MessageResponse(message="Holiday deleted successfully")

