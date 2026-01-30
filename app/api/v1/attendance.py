"""
Attendance API routes.
Check-in, check-out, and attendance management.
"""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_active_user, PermissionChecker, FeatureChecker
from app.models.auth import User
from app.services.attendance_service import AttendanceService
from app.services.employee_service import EmployeeService
from app.schemas.attendance import (
    CheckInRequest, CheckOutRequest, AttendanceCreate, AttendanceUpdate,
    AttendanceResponse, AttendanceListResponse, AttendanceSummary,
    AttendanceStatsResponse
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


router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("/check-in", response_model=AttendanceResponse)
async def check_in(
    request: Request,
    data: CheckInRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mark check-in for current user.
    Supports office, WFH, and remote work modes.
    """
    # Get employee for current user
    emp_service = EmployeeService(db)
    employee = emp_service.get_by_user_id(current_user.id)
    
    if not employee:
        raise ResourceNotFoundError("Employee profile", current_user.id)
    
    att_service = AttendanceService(db)
    
    try:
        attendance = att_service.check_in(
            employee_id=employee.id,
            data=data,
            ip_address=request.client.host if request.client else None,
            device_info=request.headers.get("user-agent")
        )
    except ValueError as e:
        raise BusinessLogicError(str(e))
    
    return AttendanceResponse(
        id=attendance.id,
        employee_id=attendance.employee_id,
        date=attendance.date,
        shift_id=attendance.shift_id,
        check_in=attendance.check_in,
        check_out=attendance.check_out,
        work_mode=attendance.work_mode,
        check_in_latitude=attendance.check_in_latitude,
        check_in_longitude=attendance.check_in_longitude,
        check_in_address=attendance.check_in_address,
        status=attendance.status,
        working_hours=attendance.working_hours,
        overtime_hours=attendance.overtime_hours,
        late_minutes=attendance.late_minutes,
        early_leave_minutes=attendance.early_leave_minutes,
        is_late=attendance.is_late,
        is_early_leave=attendance.is_early_leave,
        is_half_day=attendance.is_half_day,
        is_overtime=attendance.is_overtime,
        requires_approval=attendance.requires_approval,
        approval_status=attendance.approval_status,
        notes=attendance.notes,
        employee_code=employee.employee_code,
        employee_name=current_user.full_name
    )


@router.post("/check-out", response_model=AttendanceResponse)
async def check_out(
    request: Request,
    data: CheckOutRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark check-out for current user."""
    emp_service = EmployeeService(db)
    employee = emp_service.get_by_user_id(current_user.id)
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )
    
    att_service = AttendanceService(db)
    
    try:
        attendance = att_service.check_out(
            employee_id=employee.id,
            data=data,
            ip_address=request.client.host if request.client else None,
            device_info=request.headers.get("user-agent")
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    return AttendanceResponse.model_validate(attendance)


@router.get("/today", response_model=Optional[AttendanceResponse])
async def get_today_attendance(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get today's attendance for current user."""
    emp_service = EmployeeService(db)
    employee = emp_service.get_by_user_id(current_user.id)
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )
    
    att_service = AttendanceService(db)
    attendance = att_service.get_today_attendance(employee.id)
    
    if not attendance:
        return None
    
    return AttendanceResponse.model_validate(attendance)


@router.get("/my-history", response_model=list[AttendanceResponse])
async def get_my_attendance_history(
    from_date: date = Query(...),
    to_date: date = Query(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get attendance history for current user."""
    emp_service = EmployeeService(db)
    employee = emp_service.get_by_user_id(current_user.id)
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )
    
    att_service = AttendanceService(db)
    attendances = att_service.get_employee_attendance(employee.id, from_date, to_date)
    
    return [AttendanceResponse.model_validate(a) for a in attendances]


@router.get("/my-summary", response_model=AttendanceSummary)
async def get_my_summary(
    from_date: date = Query(...),
    to_date: date = Query(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get attendance summary for current user."""
    emp_service = EmployeeService(db)
    employee = emp_service.get_by_user_id(current_user.id)
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee profile not found"
        )
    
    att_service = AttendanceService(db)
    return att_service.get_summary(employee.id, from_date, to_date)


# Admin endpoints
@router.get("", response_model=PaginatedResponse[AttendanceListResponse])
async def list_attendance(
    from_date: date = Query(...),
    to_date: date = Query(...),
    company_id: Optional[int] = None,
    branch_id: Optional[int] = None,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("attendance.view_all")),
    db: Session = Depends(get_db)
):
    """List all attendance records (admin)."""
    att_service = AttendanceService(db)
    
    attendances, total = att_service.get_all_attendance(
        from_date=from_date,
        to_date=to_date,
        company_id=company_id,
        branch_id=branch_id,
        department_id=department_id,
        status=status,
        page=page,
        page_size=page_size
    )
    
    items = []
    for att in attendances:
        items.append(AttendanceListResponse(
            id=att.id,
            employee_id=att.employee_id,
            employee_code=att.employee.employee_code if att.employee else "",
            employee_name=att.employee.user.full_name if att.employee and att.employee.user else "",
            date=att.date,
            check_in=att.check_in,
            check_out=att.check_out,
            work_mode=att.work_mode,
            status=att.status,
            working_hours=att.working_hours,
            is_late=att.is_late
        ))
    
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/stats", response_model=AttendanceStatsResponse)
async def get_attendance_stats(
    from_date: date = Query(...),
    to_date: date = Query(...),
    company_id: Optional[int] = None,
    branch_id: Optional[int] = None,
    department_id: Optional[int] = None,
    current_user: User = Depends(PermissionChecker("attendance.view_all")),
    db: Session = Depends(get_db)
):
    """Get overall attendance statistics (admin)."""
    att_service = AttendanceService(db)
    return att_service.get_overall_stats(
        from_date=from_date,
        to_date=to_date,
        company_id=company_id,
        branch_id=branch_id,
        department_id=department_id
    )


@router.get("/employee/{employee_id}/summary", response_model=AttendanceSummary)
async def get_employee_attendance_summary(
    employee_id: int,
    from_date: date = Query(...),
    to_date: date = Query(...),
    current_user: User = Depends(PermissionChecker("attendance.view_all")),
    db: Session = Depends(get_db)
):
    """Get attendance summary for specific employee (admin)."""
    att_service = AttendanceService(db)
    return att_service.get_summary(employee_id, from_date, to_date)


@router.get("/employee/{employee_id}/history", response_model=list[AttendanceResponse])
async def get_employee_attendance_history_admin(
    employee_id: int,
    from_date: date = Query(...),
    to_date: date = Query(...),
    current_user: User = Depends(PermissionChecker("attendance.view_all")),
    db: Session = Depends(get_db)
):
    """Get attendance history for specific employee (admin)."""
    att_service = AttendanceService(db)
    attendances = att_service.get_employee_attendance(employee_id, from_date, to_date)
    return [AttendanceResponse.model_validate(a) for a in attendances]




@router.get("/{attendance_id}", response_model=AttendanceResponse)
async def get_attendance(
    attendance_id: int,
    current_user: User = Depends(PermissionChecker("attendance.view")),
    db: Session = Depends(get_db)
):
    """Get attendance by ID."""
    att_service = AttendanceService(db)
    
    attendance = att_service.get_by_id(attendance_id)
    
    if not attendance:
        raise ResourceNotFoundError("Attendance", attendance_id)
    
    return AttendanceResponse.model_validate(attendance)


@router.post("/manual", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_attendance(
    data: AttendanceCreate,
    current_user: User = Depends(PermissionChecker("attendance.edit")),
    db: Session = Depends(get_db)
):
    """Create attendance record manually (admin)."""
    att_service = AttendanceService(db)
    
    attendance = att_service.create_manual(data, created_by=current_user.id)
    
    return AttendanceResponse.model_validate(attendance)


@router.post("/{attendance_id}/approve", response_model=AttendanceResponse)
async def approve_attendance(
    attendance_id: int,
    status: str = Query(..., regex="^(approved|rejected)$"),
    notes: Optional[str] = None,
    current_user: User = Depends(PermissionChecker("attendance.approve")),
    db: Session = Depends(get_db)
):
    """Approve or reject attendance."""
    att_service = AttendanceService(db)
    
    attendance = att_service.approve(
        attendance_id=attendance_id,
        approved_by=current_user.id,
        status=status,
        notes=notes
    )
    
    if not attendance:
        raise ResourceNotFoundError("Attendance", attendance_id)
    
    return AttendanceResponse.model_validate(attendance)
