"""
Role schemas for API requests and responses.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.permission import PermissionResponse


class RoleBase(BaseModel):
    """Base role schema."""
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = Field(None, max_length=255)
    scope: str = Field(default="company", pattern="^(global|company|branch)$")


class RoleCreate(RoleBase):
    """Schema for creating a new role."""
    company_id: int | None = None
    permission_ids: list[int] | None = Field(default_factory=list)


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=255)
    is_active: bool | None = None


class RoleResponse(RoleBase):
    """Role response schema without permissions."""
    id: int
    company_id: int | None = None
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class RoleWithPermissions(RoleResponse):
    """Role response schema with full permission details."""
    permissions: list[PermissionResponse] = []
    permission_count: int = 0

    class Config:
        from_attributes = True


class RolePermissionUpdate(BaseModel):
    """Schema for updating role permissions."""
    add_permission_ids: list[int] | None = Field(default_factory=list)
    remove_permission_ids: list[int] | None = Field(default_factory=list)


class RoleListResponse(BaseModel):
    """Response schema for listing roles."""
    total: int
    roles: list[RoleResponse]

