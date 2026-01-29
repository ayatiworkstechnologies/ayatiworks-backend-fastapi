"""
API Dependencies.
Common dependencies for route handlers.
"""

from typing import Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth import User, RolePermission
from app.core.security import decode_token
from app.core.permissions import check_permission
from app.core.feature_control import is_feature_enabled


# Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    Raises HTTPException if not authenticated.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user = db.query(User).filter(
        User.id == int(user_id),
        User.is_deleted == False
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current user and verify they are active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    if current_user.is_locked():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is locked"
        )
    
    return current_user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise None."""
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    return db.query(User).filter(
        User.id == int(user_id),
        User.is_deleted == False
    ).first()


def get_user_permissions(user: User, db: Session) -> List[str]:
    """Get all permission codes for a user."""
    if not user.role_id:
        return []
    
    role_permissions = db.query(RolePermission).filter(
        RolePermission.role_id == user.role_id
    ).all()
    
    permissions = []
    for rp in role_permissions:
        if rp.permission:
            permissions.append(rp.permission.code)
    
    return permissions


class PermissionChecker:
    """
    Permission checker dependency.
    Usage: Depends(PermissionChecker("user.create"))
    """
    
    def __init__(self, required_permission: str):
        self.required_permission = required_permission
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        permissions = get_user_permissions(current_user, db)
        
        if not check_permission(permissions, self.required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {self.required_permission}"
            )
        
        return current_user


class RoleChecker:
    """
    Role-based access checker dependency.
    Usage: Depends(RoleChecker(["Admin", "HR", "Manager"]))
    """
    
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = [r.lower() for r in allowed_roles]
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        # Get user's role name
        user_role = None
        if current_user.role:
            user_role = current_user.role.name.lower() if current_user.role.name else None
        
        if not user_role or user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access restricted to: {', '.join(self.allowed_roles)}"
            )
        
        return current_user


class FeatureChecker:
    """
    Feature flag checker dependency.
    Usage: Depends(FeatureChecker("attendance", "geo_location"))
    """
    
    def __init__(self, module: str, feature: str):
        self.module = module
        self.feature = feature
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        if not is_feature_enabled(
            db,
            self.module,
            self.feature,
            company_id=current_user.company_id,
            role_id=current_user.role_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature not available: {self.module}.{self.feature}"
            )
        
        return current_user


def require_permission(permission: str):
    """Shortcut for requiring a permission."""
    return Depends(PermissionChecker(permission))


def require_feature(module: str, feature: str):
    """Shortcut for requiring a feature."""
    return Depends(FeatureChecker(module, feature))


class AnyPermissionChecker:
    """
    Check if user has ANY of the required permissions (OR logic).
    Usage: Depends(AnyPermissionChecker(["project.view", "project.view_all"]))
    """
    
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        permissions = get_user_permissions(current_user, db)
        
        # Check if user has any of the required permissions
        from app.core.permissions import has_any_permission
        if not has_any_permission(permissions, self.required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required any of: {', '.join(self.required_permissions)}"
            )
        
        return current_user


class AllPermissionsChecker:
    """
    Check if user has ALL of the required permissions (AND logic).
    Usage: Depends(AllPermissionsChecker(["project.view", "project.edit"]))
    """
    
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        permissions = get_user_permissions(current_user, db)
        
        # Check if user has all required permissions
        from app.core.permissions import has_all_permissions
        if not has_all_permissions(permissions, self.required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required all of: {', '.join(self.required_permissions)}"
            )
        
        return current_user


def require_any_permission(permissions: List[str]):
    """Shortcut for requiring any of the permissions (OR logic)."""
    return Depends(AnyPermissionChecker(permissions))


def require_all_permissions(permissions: List[str]):
    """Shortcut for requiring all of the permissions (AND logic)."""
    return Depends(AllPermissionsChecker(permissions))


async def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Get current user and verify they are a superuser (admin or super_admin).
    """
    if current_user.role and current_user.role.code in ["ADMIN", "SUPER_ADMIN"]:
        return current_user
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="The user does not have enough privileges"
    )
