"""
Authentication and user schemas.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import BaseSchema, TimestampSchema

# ============== Token Schemas ==============

class Token(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: int  # user_id
    email: str
    role_id: int | None = None
    company_id: int | None = None
    exp: datetime
    type: str  # access, refresh


# ============== Login Schemas ==============

class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str = Field(..., min_length=1)
    remember_me: bool = False


class LoginResponse(BaseModel):
    """Login response with user info and token."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"
    permissions: list[str] = []


class OTPRequest(BaseModel):
    """OTP verification request."""

    email: EmailStr
    otp: str = Field(..., min_length=4, max_length=10)


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


# ============== Permission Schemas ==============

class PermissionBase(BaseSchema):
    """Permission base schema."""

    name: str
    code: str
    module: str
    description: str | None = None


class PermissionCreate(PermissionBase):
    """Permission create schema."""
    pass


class PermissionUpdate(BaseSchema):
    """Permission update schema."""

    name: str | None = None
    code: str | None = None
    module: str | None = None
    description: str | None = None


class PermissionResponse(PermissionBase, TimestampSchema):
    """Permission response schema."""

    id: int


# ============== Role Schemas ==============

class RoleBase(BaseSchema):
    """Role base schema."""

    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=50)
    description: str | None = None
    scope: str = "global"


class RoleCreate(RoleBase):
    """Role create schema."""

    permission_ids: list[int] = []
    company_id: int | None = None


class RoleUpdate(BaseSchema):
    """Role update schema."""

    name: str | None = None
    description: str | None = None
    permission_ids: list[int] | None = None
    is_active: bool | None = None


class RoleResponse(RoleBase, TimestampSchema):
    """Role response schema."""

    id: int
    is_active: bool
    is_system: bool
    company_id: int | None = None
    permissions: list[PermissionResponse] = []


class RoleListResponse(RoleBase, TimestampSchema):
    """Role list response (without permissions detail)."""

    id: int
    is_active: bool
    is_system: bool
    permission_count: int = 0


# ============== User Schemas ==============

class UserBase(BaseSchema):
    """User base schema."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)


class UserCreate(UserBase):
    """User create schema."""

    password: str = Field(..., min_length=8)
    role_id: int | None = None
    company_id: int | None = None
    branch_id: int | None = None

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseSchema):
    """User update schema."""

    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    avatar: str | None = None
    role_id: int | None = None
    company_id: int | None = None
    branch_id: int | None = None
    is_active: bool | None = None
    password: str | None = None


class UserResponse(UserBase, TimestampSchema):
    """User response schema."""

    id: int
    is_active: bool
    is_verified: bool
    is_2fa_enabled: bool
    avatar: str | None = None
    role_id: int | None = None
    company_id: int | None = None
    branch_id: int | None = None
    employee_id: int | None = None
    last_login: datetime | None = None

    # Nested response (optional)
    role: RoleListResponse | None = None
    permissions: list[str] = []


class UserListResponse(BaseSchema):
    """Minimal user info for lists."""

    id: int
    email: str
    first_name: str
    last_name: str | None = None
    is_active: bool
    role_id: int | None = None

    @property
    def full_name(self) -> str:
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name


class ChangePasswordRequest(BaseModel):
    """Change password request."""

    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class ResetPasswordRequest(BaseModel):
    """Reset password request."""

    email: EmailStr


class SetPasswordRequest(BaseModel):
    """Set new password after reset."""

    token: str
    new_password: str = Field(..., min_length=8)


class Enable2FARequest(BaseModel):
    """Enable 2FA request."""

    password: str


class Verify2FARequest(BaseModel):
    """Verify 2FA code."""

    code: str = Field(..., min_length=4, max_length=10)


# Forward reference update
LoginResponse.model_rebuild()

