"""
Notification and Announcement models.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import AuditMixin, BaseModel


class Notification(BaseModel):
    """
    User notification.
    """

    __tablename__ = "notifications"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Type
    type = Column(String(50), default="info")  # info, success, warning, error
    category = Column(String(50), nullable=True)  # leave, attendance, task, etc.

    # Link
    link = Column(String(500), nullable=True)  # URL to navigate to

    # Related entity
    entity_type = Column(String(50), nullable=True)  # task, leave, project, etc.
    entity_id = Column(Integer, nullable=True)

    # Status
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref="notifications")


class Announcement(BaseModel, AuditMixin):
    """
    Company-wide or targeted announcements.
    """

    __tablename__ = "announcements"

    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    # Targeting
    target_scope = Column(String(20), default="all")  # all, company, branch, department, role
    target_id = Column(Integer, nullable=True)  # ID based on scope
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)

    # Scheduling
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # Priority
    priority = Column(String(20), default="normal")  # low, normal, high, urgent
    is_pinned = Column(Boolean, default=False)

    # Status
    status = Column(String(20), default="draft")  # draft, published, archived
    published_at = Column(DateTime, nullable=True)


class AnnouncementRead(BaseModel):
    """
    Track which users have read announcements.
    """

    __tablename__ = "announcement_reads"

    announcement_id = Column(Integer, ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    read_at = Column(DateTime, default=datetime.utcnow)

