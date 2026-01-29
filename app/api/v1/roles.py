"""
Role API endpoints.
"""

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth import Role, User, Permission, RolePermission
from app.schemas.role import (
    RoleCreate, RoleUpdate, RoleResponse,
    RoleWithPermissions, RolePermissionUpdate, RoleListResponse
)
from app.schemas.common import MessageResponse
from app.api.deps import get_current_active_user, get_current_active_superuser

router = APIRouter()


@router.get("", response_model=List[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    List all roles.
    Available to all authenticated users.
    """
    roles = db.query(Role).filter(Role.is_active == True).offset(skip).limit(limit).all()
    return roles


@router.get("/{role_id}", response_model=RoleWithPermissions)
def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get a single role with full permission details by ID.
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=404,
            detail="Role not found",
        )
    
    # Get permissions
    role_perms = db.query(RolePermission).filter(RolePermission.role_id == role.id).all()
    permissions = []
    for rp in role_perms:
        if rp.permission:
            permissions.append(rp.permission)
    
    # Build response
    role_dict = {
        "id": role.id,
        "name": role.name,
        "code": role.code,
        "description": role.description,
        "scope": role.scope,
        "company_id": role.company_id,
        "is_system": role.is_system,
        "is_active": role.is_active,
        "created_at": role.created_at,
        "updated_at": role.updated_at,
        "permissions": permissions,
        "permission_count": len(permissions)
    }
    
    return role_dict


@router.post("", response_model=RoleResponse)
def create_role(
    role_in: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Create new custom role (Admin/Super Admin only).
    """
    # Check if role code already exists
    existing_role = db.query(Role).filter(Role.code == role_in.code).first()
    if existing_role:
        raise HTTPException(
            status_code=400,
            detail="The role with this code already exists.",
        )
    
    # Create role
    role_data = role_in.model_dump(exclude={"permission_ids"})
    role = Role(**role_data, is_system=False, is_active=True)
    db.add(role)
    db.commit()
    db.refresh(role)
    
    # Assign permissions if provided
    if role_in.permission_ids:
        for pid in role_in.permission_ids:
            # Verify permission exists
            perm = db.query(Permission).filter(Permission.id == pid).first()
            if perm:
                rp = RolePermission(role_id=role.id, permission_id=pid)
                db.add(rp)
        db.commit()
        db.refresh(role)
        
    return role


@router.put("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    role_in: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Update a role (Admin/Super Admin only).
    System roles can be updated but not deleted.
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=404,
            detail="Role not found",
        )
    
    update_data = role_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(role, field, value)
        
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.put("/{role_id}/permissions", response_model=MessageResponse)
def update_role_permissions(
    role_id: int,
    perm_update: RolePermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Add or remove permissions from a role (Admin/Super Admin only).
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=404,
            detail="Role not found",
        )
    
    # Add permissions
    added_count = 0
    if perm_update.add_permission_ids:
        for pid in perm_update.add_permission_ids:
            # Check if already exists
            existing = db.query(RolePermission).filter(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == pid
            ).first()
            
            if not existing:
                # Verify permission exists
                perm = db.query(Permission).filter(Permission.id == pid).first()
                if perm:
                    rp = RolePermission(role_id=role.id, permission_id=pid)
                    db.add(rp)
                    added_count += 1
    
    # Remove permissions
    removed_count = 0
    if perm_update.remove_permission_ids:
        for pid in perm_update.remove_permission_ids:
            deleted = db.query(RolePermission).filter(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == pid
            ).delete()
            removed_count += deleted
    
    db.commit()
    
    return MessageResponse(
        message=f"Updated permissions for role '{role.name}': {added_count} added, {removed_count} removed"
    )


@router.delete("/{role_id}", response_model=MessageResponse)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Delete a role (Admin/Super Admin only).
    System roles cannot be deleted.
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=404,
            detail="Role not found",
        )
    
    # Prevent deletion of system roles
    if role.is_system:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete system roles. System roles are: SUPER_ADMIN, ADMIN, EMPLOYEE, CLIENT.",
        )
    
    # Check if role is assigned to any users
    users_with_role = db.query(User).filter(User.role_id == role.id).count()
    if users_with_role > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete role. It is assigned to {users_with_role} user(s). Please reassign those users first.",
        )
    
    # Delete the role (cascade will delete role_permissions)
    db.delete(role)
    db.commit()
    
    return MessageResponse(message=f"Role '{role.name}' deleted successfully")
