"""
User management API routes.
"""


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import PermissionChecker
from app.database import get_db
from app.models.auth import Permission, Role, RolePermission, User
from app.schemas.auth import (
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
    RoleCreate,
    RoleListResponse,
    RoleResponse,
    RoleUpdate,
)
from app.schemas.common import MessageResponse

router = APIRouter(tags=["Users & Roles"])


# ... (User and Role endpoints unchanged)


# ============== Permission Endpoints ==============

@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    module: str | None = None,
    current_user: User = Depends(PermissionChecker("role.view")),
    db: Session = Depends(get_db)
):
    """List all available permissions."""
    query = db.query(Permission)

    if module:
        query = query.filter(Permission.module == module)

    permissions = query.order_by(Permission.module, Permission.name).all()
    return [PermissionResponse.model_validate(p) for p in permissions]


@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    data: PermissionCreate,
    current_user: User = Depends(PermissionChecker("role.create")),
    db: Session = Depends(get_db)
):
    """Create a new permission."""
    # Check if code exists
    existing = db.query(Permission).filter(Permission.code == data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission code already exists"
        )

    permission = Permission(
        name=data.name,
        code=data.code,
        module=data.module,
        description=data.description
    )

    db.add(permission)
    db.commit()
    db.refresh(permission)

    return PermissionResponse.model_validate(permission)


@router.put("/permissions/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: int,
    data: PermissionUpdate,
    current_user: User = Depends(PermissionChecker("role.edit")),
    db: Session = Depends(get_db)
):
    """Update a permission."""
    permission = db.query(Permission).filter(Permission.id == permission_id).first()

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    update_data = data.model_dump(exclude_unset=True)

    # Check code uniqueness if changing
    if 'code' in update_data and update_data['code'] != permission.code:
        existing = db.query(Permission).filter(Permission.code == update_data['code']).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permission code already exists"
            )

    for field, value in update_data.items():
        setattr(permission, field, value)

    db.commit()
    db.refresh(permission)

    return PermissionResponse.model_validate(permission)


@router.delete("/permissions/{permission_id}", response_model=MessageResponse)
async def delete_permission(
    permission_id: int,
    current_user: User = Depends(PermissionChecker("role.delete")),
    db: Session = Depends(get_db)
):
    """Delete a permission."""
    permission = db.query(Permission).filter(Permission.id == permission_id).first()

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )

    db.delete(permission)
    db.commit()

    return MessageResponse(message="Permission deleted successfully")


# ============== User Endpoints ==============
# ... (User endpoints unchanged)

# ============== Role Endpoints ==============

@router.get("/roles", response_model=list[RoleListResponse])
async def list_roles(
    company_id: int | None = None,
    current_user: User = Depends(PermissionChecker("role.view")),
    db: Session = Depends(get_db)
):
    """List all roles."""
    query = db.query(Role).filter(Role.is_deleted == False)

    if company_id:
        query = query.filter(
            (Role.company_id == company_id) | (Role.company_id is None)
        )

    roles = query.all()

    result = []
    for role in roles:
        result.append(RoleListResponse(
            id=role.id,
            name=role.name,
            code=role.code,
            description=role.description,
            scope=role.scope,
            is_active=role.is_active,
            is_system=role.is_system,
            permission_count=len(role.permissions)
        ))

    return result


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    current_user: User = Depends(PermissionChecker("role.view")),
    db: Session = Depends(get_db)
):
    """Get role by ID with permissions."""
    role = db.query(Role).filter(
        Role.id == role_id,
        Role.is_deleted == False
    ).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Construct response with permissions
    response = RoleResponse.model_validate(role)
    response.permissions = [PermissionResponse.model_validate(rp.permission) for rp in role.permissions]

    return response


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    current_user: User = Depends(PermissionChecker("role.create")),
    db: Session = Depends(get_db)
):
    """Create a new role."""
    # Check if code exists
    existing = db.query(Role).filter(Role.code == data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role code already exists"
        )

    role = Role(
        name=data.name,
        code=data.code,
        description=data.description,
        scope=data.scope,
        company_id=data.company_id,
        created_by=current_user.id
    )

    db.add(role)
    db.commit()
    db.refresh(role)

    # Add permissions
    if data.permission_ids:
        for perm_id in data.permission_ids:
            rp = RolePermission(role_id=role.id, permission_id=perm_id)
            db.add(rp)
        db.commit()
        db.refresh(role)

    # Construct response with permissions
    response = RoleResponse.model_validate(role)
    # Re-fetch with permissions explicitly to be safe or rely on lazy loading if configured
    # Using explicit list comprehension to ensure schema compatibility
    response.permissions = [PermissionResponse.model_validate(rp.permission) for rp in role.permissions]

    return response


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    data: RoleUpdate,
    current_user: User = Depends(PermissionChecker("role.edit")),
    db: Session = Depends(get_db)
):
    """Update a role."""
    role = db.query(Role).filter(
        Role.id == role_id,
        Role.is_deleted == False
    ).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    if role.is_system and data.is_active == False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate system role"
        )

    update_data = data.model_dump(exclude_unset=True)

    # Handle permissions separately
    if 'permission_ids' in update_data:
        permission_ids = update_data.pop('permission_ids')

        # Remove existing permissions
        db.query(RolePermission).filter(RolePermission.role_id == role.id).delete()

        # Add new permissions
        for perm_id in permission_ids:
            rp = RolePermission(role_id=role.id, permission_id=perm_id)
            db.add(rp)

    for field, value in update_data.items():
        setattr(role, field, value)

    role.updated_by = current_user.id
    db.commit()
    db.refresh(role)

    # Construct response with permissions
    response = RoleResponse.model_validate(role)
    response.permissions = [PermissionResponse.model_validate(rp.permission) for rp in role.permissions]

    return response


@router.delete("/roles/{role_id}", response_model=MessageResponse)
async def delete_role(
    role_id: int,
    current_user: User = Depends(PermissionChecker("role.delete")),
    db: Session = Depends(get_db)
):
    """Delete a role."""
    role = db.query(Role).filter(
        Role.id == role_id,
        Role.is_deleted == False
    ).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system role"
        )

    role.soft_delete(current_user.id)
    db.commit()

    return MessageResponse(message="Role deleted successfully")

