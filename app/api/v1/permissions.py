"""
Permission API endpoints.
"""

from collections import defaultdict
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_superuser, get_current_active_user, get_user_permissions
from app.core.permissions import check_permission
from app.database import get_db
from app.models.auth import Permission, RolePermission, User
from app.schemas.common import MessageResponse
from app.schemas.permission import (
    PermissionCreate,
    PermissionGroupedResponse,
    PermissionListResponse,
    PermissionResponse,
    PermissionUpdate,
    UserPermissionCheck,
)

router = APIRouter()


@router.get("/all", response_model=PermissionGroupedResponse)
def list_all_permissions_grouped(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    List all permissions grouped by module.
    Available to all authenticated users.
    """
    permissions = db.query(Permission).filter(
        Permission.is_active.is_(True),
        Permission.is_deleted.is_(False),
    ).all()

    # Group by module
    grouped: dict[str, list[Permission]] = defaultdict(list)
    for perm in permissions:
        grouped[perm.module].append(perm)

    # Format response
    modules = []
    for module_name, perms in sorted(grouped.items()):
        modules.append(PermissionListResponse(
            module=module_name,
            permissions=perms
        ))

    return PermissionGroupedResponse(
        total=len(permissions),
        modules=modules
    )


@router.get("/role/{role_id}", response_model=list[PermissionResponse])
def get_role_permissions(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get all permissions assigned to a specific role.
    """
    role_perms = db.query(RolePermission).filter(
        RolePermission.role_id == role_id,
        RolePermission.is_deleted.is_(False),
    ).all()

    permissions = []
    for rp in role_perms:
        if rp.permission and not rp.permission.is_deleted:
            permissions.append(rp.permission)

    return permissions


@router.get("/my-permissions", response_model=list[PermissionResponse])
def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get permissions for the current user.
    """
    if not current_user.role_id:
        return []

    role_perms = db.query(RolePermission).filter(
        RolePermission.role_id == current_user.role_id,
        RolePermission.is_deleted.is_(False),
    ).all()

    permissions = []
    for rp in role_perms:
        if rp.permission and not rp.permission.is_deleted:
            permissions.append(rp.permission)

    return permissions


@router.post("/check", response_model=UserPermissionCheck)
def check_user_permission(
    permission_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Check if current user has a specific permission.
    """
    user_perms = get_user_permissions(current_user, db)
    has_perm = check_permission(user_perms, permission_code)

    return UserPermissionCheck(
        permission_code=permission_code,
        has_permission=has_perm
    )


@router.get("", response_model=list[PermissionResponse])
def list_permissions(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    module: str = None,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    List permissions with optional filtering by module.
    """
    query = db.query(Permission).filter(Permission.is_deleted.is_(False))

    if module:
        query = query.filter(Permission.module == module)

    permissions = query.offset(skip).limit(limit).all()
    return permissions


@router.get("/{permission_id}", response_model=PermissionResponse)
def get_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get a single permission by ID.
    """
    permission = db.query(Permission).filter(
        Permission.id == permission_id,
        Permission.is_deleted.is_(False),
    ).first()
    if not permission:
        raise HTTPException(
            status_code=404,
            detail="Permission not found",
        )
    return permission


@router.post("", response_model=PermissionResponse)
def create_permission(
    permission_in: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Create new permission (Super Admin only).
    """
    permission = db.query(Permission).filter(
        Permission.code == permission_in.code,
        Permission.is_deleted.is_(False),
    ).first()
    if permission:
        raise HTTPException(
            status_code=400,
            detail="The permission with this code already exists in the system.",
        )

    permission = Permission(**permission_in.model_dump(), is_active=True)
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return permission


@router.put("/{permission_id}", response_model=PermissionResponse)
def update_permission(
    permission_id: int,
    permission_in: PermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Update a permission (Super Admin only).
    """
    permission = db.query(Permission).filter(
        Permission.id == permission_id,
        Permission.is_deleted.is_(False),
    ).first()
    if not permission:
        raise HTTPException(
            status_code=404,
            detail="The permission does not exist in the system",
        )

    update_data = permission_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(permission, field, value)

    permission.updated_at = datetime.utcnow()
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return permission


@router.delete("/{permission_id}", response_model=MessageResponse)
def delete_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Soft delete a permission (Super Admin only).
    Related role assignments are soft-deleted so they no longer grant access.
    """
    permission = db.query(Permission).filter(
        Permission.id == permission_id,
        Permission.is_deleted.is_(False),
    ).first()
    if not permission:
        raise HTTPException(
            status_code=404,
            detail="The permission does not exist in the system",
        )

    permission.soft_delete(current_user.id)
    db.query(RolePermission).filter(
        RolePermission.permission_id == permission.id,
        RolePermission.is_deleted.is_(False),
    ).update({
        "is_deleted": True,
        "deleted_at": datetime.utcnow(),
        "deleted_by": current_user.id,
    })
    db.commit()
    return MessageResponse(message="Permission deleted successfully")

