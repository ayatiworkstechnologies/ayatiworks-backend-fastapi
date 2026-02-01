"""
Email and Chat models.
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import AuditMixin, BaseModel


class EmailTemplate(BaseModel, AuditMixin):
    """Email template."""

    __tablename__ = "email_templates"

    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)

    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)

    # Type
    template_type = Column(String(50), default="transactional")  # transactional, marketing

    # Variables
    variables = Column(JSON, nullable=True)  # [{name, description}]

    # Status
    is_active = Column(Boolean, default=True)

    # Company specific
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)


class EmailLog(BaseModel):
    """Email send log."""

    __tablename__ = "email_logs"

    # Recipient
    to_email = Column(String(255), nullable=False)
    to_name = Column(String(100), nullable=True)

    # CC/BCC
    cc = Column(JSON, nullable=True)
    bcc = Column(JSON, nullable=True)

    # Content
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)

    # Template
    template_id = Column(Integer, ForeignKey("email_templates.id"), nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, sent, failed, bounced
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Tracking
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)

    # User
    sent_by = Column(Integer, ForeignKey("users.id"), nullable=True)


class ChatRoom(BaseModel, AuditMixin):
    """Chat room for internal messaging."""

    __tablename__ = "chat_rooms"

    name = Column(String(100), nullable=True)

    # Type
    room_type = Column(String(20), default="direct")  # direct, group, channel

    # For channels
    is_private = Column(Boolean, default=True)
    description = Column(Text, nullable=True)

    # Avatar
    avatar = Column(String(500), nullable=True)

    # Last activity
    last_message_at = Column(DateTime, nullable=True)

    # Relationships
    members = relationship("ChatMember", back_populates="room", cascade="all, delete-orphan")
    messages = relationship("ChatMessage", back_populates="room", cascade="all, delete-orphan")


class ChatMember(BaseModel):
    """Chat room member."""

    __tablename__ = "chat_members"

    room_id = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Role
    role = Column(String(20), default="member")  # admin, member

    # Settings
    is_muted = Column(Boolean, default=False)

    # Read status
    last_read_at = Column(DateTime, nullable=True)

    joined_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    room = relationship("ChatRoom", back_populates="members")


class ChatMessage(BaseModel):
    """Chat message."""

    __tablename__ = "chat_messages"

    room_id = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Content
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")  # text, image, file, system

    # Attachments
    attachments = Column(JSON, nullable=True)  # [{filename, url, size}]

    # Reply to
    reply_to_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=True)

    # Edit/Delete
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime, nullable=True)

    # Relationships
    room = relationship("ChatRoom", back_populates="messages")
    sender = relationship("User", backref="chat_messages")


class SMTPSettings(BaseModel, AuditMixin):
    """SMTP configuration per company."""

    __tablename__ = "smtp_settings"

    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, unique=True)

    host = Column(String(255), nullable=False)
    port = Column(Integer, default=587)
    username = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)  # Encrypted

    use_tls = Column(Boolean, default=True)
    use_ssl = Column(Boolean, default=False)

    from_email = Column(String(255), nullable=False)
    from_name = Column(String(100), nullable=True)

    # Reply-to
    reply_to = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

