"""
Audit log model.
Tracks all user actions for compliance and debugging.
"""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class AuditLog(BaseModel):
    """
    Audit log for tracking user actions.
    """

    __tablename__ = "audit_logs"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Action
    action = Column(String(50), nullable=False)  # create, update, delete, login, logout, etc.
    module = Column(String(50), nullable=False)  # employee, attendance, leave, etc.

    # Entity
    entity_type = Column(String(50), nullable=True)  # Model name
    entity_id = Column(Integer, nullable=True)

    # Changes
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)

    # Description
    description = Column(Text, nullable=True)

    # Request info
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    request_path = Column(String(255), nullable=True)
    request_method = Column(String(10), nullable=True)

    # Timestamp
    performed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="audit_logs")

