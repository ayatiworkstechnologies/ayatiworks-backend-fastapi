"""
Security and Compliance models.
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.models.base import AuditMixin, BaseModel


class SecurityPolicy(BaseModel, AuditMixin):
    """Security policy configuration."""

    __tablename__ = "security_policies"

    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, unique=True)

    # Password policy
    min_password_length = Column(Integer, default=8)
    require_uppercase = Column(Boolean, default=True)
    require_lowercase = Column(Boolean, default=True)
    require_numbers = Column(Boolean, default=True)
    require_special_chars = Column(Boolean, default=True)
    password_expiry_days = Column(Integer, default=90)
    password_history_count = Column(Integer, default=5)

    # Login policy
    max_login_attempts = Column(Integer, default=5)
    lockout_duration_minutes = Column(Integer, default=30)
    session_timeout_minutes = Column(Integer, default=480)  # 8 hours

    # Two-Factor
    require_2fa = Column(Boolean, default=False)
    require_2fa_for_roles = Column(JSON, nullable=True)  # Array of role IDs

    # IP restrictions
    allowed_ips = Column(JSON, nullable=True)
    blocked_ips = Column(JSON, nullable=True)

    # Device limits
    max_devices_per_user = Column(Integer, default=5)


class LoginAttempt(BaseModel):
    """Login attempt log."""

    __tablename__ = "login_attempts"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    email = Column(String(255), nullable=True)

    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)

    # Result
    success = Column(Boolean, default=False)
    failure_reason = Column(String(100), nullable=True)

    attempted_at = Column(DateTime, default=datetime.utcnow)


class APIKey(BaseModel, AuditMixin):
    """API key for external integrations."""

    __tablename__ = "api_keys"

    name = Column(String(100), nullable=False)
    key = Column(String(255), unique=True, nullable=False, index=True)

    # Owner
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)

    # Permissions
    permissions = Column(JSON, nullable=True)  # Array of permission codes

    # Scopes
    scopes = Column(JSON, nullable=True)  # API scopes allowed

    # Limits
    rate_limit = Column(Integer, default=1000)  # Requests per hour

    # Expiry
    expires_at = Column(DateTime, nullable=True)

    # Usage
    last_used_at = Column(DateTime, nullable=True)
    total_requests = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)


class Backup(BaseModel, AuditMixin):
    """Backup history."""

    __tablename__ = "backups"

    name = Column(String(255), nullable=False)

    # Type
    backup_type = Column(String(20), nullable=False)  # full, incremental, database

    # File
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, in_progress, completed, failed
    error_message = Column(Text, nullable=True)

    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Retention
    expires_at = Column(DateTime, nullable=True)

    # Restored
    is_restored = Column(Boolean, default=False)
    restored_at = Column(DateTime, nullable=True)
    restored_by = Column(Integer, ForeignKey("users.id"), nullable=True)


class ComplianceLog(BaseModel):
    """Compliance and regulatory log."""

    __tablename__ = "compliance_logs"

    # Type
    compliance_type = Column(String(50), nullable=False)  # GDPR, data_access, data_deletion

    # Subject
    subject_type = Column(String(50), nullable=True)  # user, employee, client
    subject_id = Column(Integer, nullable=True)

    # Action
    action = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Request info
    request_id = Column(String(100), nullable=True)
    requested_by = Column(String(255), nullable=True)
    requested_at = Column(DateTime, nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, in_progress, completed
    completed_at = Column(DateTime, nullable=True)
    completed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Evidence
    evidence_path = Column(String(500), nullable=True)

    performed_at = Column(DateTime, default=datetime.utcnow)

