"""
Permission schemas for API requests and responses.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PermissionBase(BaseModel):
    """Base permission schema."""
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=100)
    module: str = Field(..., min_length=1, max_length=50)
    description: str | None = Field(None, max_length=255)


class PermissionCreate(PermissionBase):
    """Schema for creating a new permission."""
    pass


class PermissionUpdate(BaseModel):
    """Schema for updating a permission."""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=255)
    is_active: bool | None = None


class PermissionResponse(PermissionBase):
    """Permission response schema."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class PermissionListResponse(BaseModel):
    """Response schema for listing permissions grouped by module."""
    module: str
    permissions: list[PermissionResponse]


class PermissionGroupedResponse(BaseModel):
    """Response schema for all permissions grouped by module."""
    total: int
    modules: list[PermissionListResponse]


class RolePermissionAssign(BaseModel):
    """Schema for assigning/removing permissions to/from a role."""
    permission_ids: list[int] = Field(..., min_items=1)


class UserPermissionCheck(BaseModel):
    """Schema for checking if user has specific permission."""
    permission_code: str
    has_permission: bool

