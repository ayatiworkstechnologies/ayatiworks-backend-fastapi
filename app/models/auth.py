"""
Authentication and authorization models.
User, Role, Permission, and Session management.
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import AuditMixin, BaseModel


class Permission(BaseModel):
    """
    Permission model representing individual access rights.
    """

    __tablename__ = "permissions"

    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(100), nullable=False, unique=True, index=True)
    module = Column(String(50), nullable=False, index=True)
    description = Column(String(255), nullable=True)

    # Relationships
    roles = relationship("RolePermission", back_populates="permission")


class Role(BaseModel, AuditMixin):
    """
    Role model for grouping permissions.
    Supports scoping to global, company, or branch level.
    """

    __tablename__ = "roles"

    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    scope = Column(String(20), default="global")  # global, company, branch
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    is_system = Column(Boolean, default=False)  # System roles cannot be deleted

    # Relationships
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    users = relationship("User", back_populates="role")


class RolePermission(BaseModel):
    """
    Many-to-many relationship between Roles and Permissions.
    """

    __tablename__ = "role_permissions"

    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")


class User(BaseModel, AuditMixin):
    """
    User model for authentication and profile.
    """

    __tablename__ = "users"

    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    avatar = Column(String(255), nullable=True)

    # Organization
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)

    # Security
    is_verified = Column(Boolean, default=False)
    is_2fa_enabled = Column(Boolean, default=False)
    two_fa_secret = Column(String(100), nullable=True)
    last_login = Column(DateTime, nullable=True)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)

    # Relationships
    role = relationship("Role", back_populates="users")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    employee = relationship("Employee", back_populates="user", uselist=False)

    @property
    def full_name(self) -> str:
        """Return user's full name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    def is_locked(self) -> bool:
        """Check if user account is locked."""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False

    @property
    def employee_id(self) -> int | None:
        """Return associated employee ID."""
        return self.employee.id if self.employee else None


class UserSession(BaseModel):
    """
    User session for tracking active logins.
    """

    __tablename__ = "user_sessions"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    access_token = Column(String(500), nullable=False, index=True)
    refresh_token = Column(String(500), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    device_info = Column(JSON, nullable=True)
    is_valid = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="sessions")


class OTPCode(BaseModel):
    """
    One-Time Password codes for 2FA verification.
    """

    __tablename__ = "otp_codes"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(10), nullable=False)
    purpose = Column(String(50), nullable=False)  # login, reset_password, verify_email
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime, nullable=True)

    def is_valid(self) -> bool:
        """Check if OTP is still valid."""
        return not self.is_used and self.expires_at > datetime.utcnow()

