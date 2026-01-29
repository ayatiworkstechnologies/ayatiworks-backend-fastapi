"""
Role schemas for API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.schemas.permission import PermissionResponse


class RoleBase(BaseModel):
    """Base role schema."""
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    scope: str = Field(default="company", pattern="^(global|company|branch)$")


class RoleCreate(RoleBase):
    """Schema for creating a new role."""
    company_id: Optional[int] = None
    permission_ids: Optional[List[int]] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class RoleResponse(RoleBase):
    """Role response schema without permissions."""
    id: int
    company_id: Optional[int] = None
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoleWithPermissions(RoleResponse):
    """Role response schema with full permission details."""
    permissions: List[PermissionResponse] = []
    permission_count: int = 0

    class Config:
        from_attributes = True


class RolePermissionUpdate(BaseModel):
    """Schema for updating role permissions."""
    add_permission_ids: Optional[List[int]] = Field(default_factory=list)
    remove_permission_ids: Optional[List[int]] = Field(default_factory=list)


class RoleListResponse(BaseModel):
    """Response schema for listing roles."""
    total: int
    roles: List[RoleResponse]
