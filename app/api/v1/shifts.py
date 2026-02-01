"""
Shift management API routes.
"""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import PermissionChecker
from app.database import get_db
from app.models.attendance import Shift
from app.models.auth import User
from app.schemas.attendance import ShiftCreate, ShiftResponse, ShiftUpdate
from app.schemas.common import MessageResponse, PaginatedResponse

router = APIRouter(prefix="/shifts", tags=["Shifts"])


@router.get("", response_model=PaginatedResponse[ShiftResponse])
async def list_shifts(
    company_id: int | None = None,
    search: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("shift.view")),
    db: Session = Depends(get_db)
):
    """List all shifts."""
    query = db.query(Shift).filter(Shift.is_deleted == False)

    if company_id:
        query = query.filter(Shift.company_id == company_id)

    if search:
        query = query.filter(
            Shift.name.ilike(f"%{search}%") |
            Shift.code.ilike(f"%{search}%")
        )

    if is_active is not None:
        query = query.filter(Shift.is_active == is_active)

    total = query.count()

    offset = (page - 1) * page_size
    shifts = query.offset(offset).limit(page_size).all()

    items = [ShiftResponse.model_validate(s) for s in shifts]
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/{shift_id}", response_model=ShiftResponse)
async def get_shift(
    shift_id: int,
    current_user: User = Depends(PermissionChecker("shift.view")),
    db: Session = Depends(get_db)
):
    """Get shift by ID."""
    shift = db.query(Shift).filter(
        Shift.id == shift_id,
        Shift.is_deleted == False
    ).first()

    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shift not found"
        )

    return ShiftResponse.model_validate(shift)


@router.post("", response_model=ShiftResponse, status_code=status.HTTP_201_CREATED)
async def create_shift(
    data: ShiftCreate,
    current_user: User = Depends(PermissionChecker("shift.manage")),
    db: Session = Depends(get_db)
):
    """Create a new shift."""
    # Check if code exists
    existing = db.query(Shift).filter(
        Shift.code == data.code,
        Shift.is_deleted == False
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shift code already exists"
        )

    shift = Shift(
        **data.model_dump(),
        created_by=current_user.id
    )

    db.add(shift)
    db.commit()
    db.refresh(shift)

    return ShiftResponse.model_validate(shift)


@router.put("/{shift_id}", response_model=ShiftResponse)
async def update_shift(
    shift_id: int,
    data: ShiftUpdate,
    current_user: User = Depends(PermissionChecker("shift.manage")),
    db: Session = Depends(get_db)
):
    """Update a shift."""
    shift = db.query(Shift).filter(
        Shift.id == shift_id,
        Shift.is_deleted == False
    ).first()

    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shift not found"
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(shift, field, value)

    shift.updated_by = current_user.id
    db.commit()
    db.refresh(shift)

    return ShiftResponse.model_validate(shift)


@router.delete("/{shift_id}", response_model=MessageResponse)
async def delete_shift(
    shift_id: int,
    current_user: User = Depends(PermissionChecker("shift.manage")),
    db: Session = Depends(get_db)
):
    """Delete a shift (soft delete)."""
    shift = db.query(Shift).filter(
        Shift.id == shift_id,
        Shift.is_deleted == False
    ).first()

    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shift not found"
        )

    shift.soft_delete(current_user.id)
    db.commit()

    return MessageResponse(message="Shift deleted successfully")

