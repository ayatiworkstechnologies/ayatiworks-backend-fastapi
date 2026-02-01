"""
Ticket/Support system models.
"""

import enum

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import AuditMixin, BaseModel


class TicketPriority(enum.Enum):
    """Ticket priority enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(enum.Enum):
    """Ticket status enum."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Ticket(BaseModel, AuditMixin):
    """
    Support ticket.
    """

    __tablename__ = "tickets"

    # Requester
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_name = Column(String(100), nullable=True)

    # Details
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=True)

    # Status
    priority = Column(String(20), default=TicketPriority.MEDIUM.value)
    status = Column(String(20), default=TicketStatus.OPEN.value)

    # Assignment
    assigned_to = Column(Integer, ForeignKey("employees.id"), nullable=True)

    # SLA
    sla_due_at = Column(DateTime, nullable=True)
    first_response_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    client = relationship("Client", backref="tickets")
    responses = relationship("TicketResponse", back_populates="ticket", cascade="all, delete-orphan")


class TicketResponse(BaseModel, AuditMixin):
    """
    Ticket response/reply.
    """

    __tablename__ = "ticket_responses"

    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    content = Column(Text, nullable=False)

    # Internal note (not visible to client)
    is_internal = Column(Boolean, default=False)

    # Attachments
    attachments = Column(JSON, nullable=True)

    # Relationships
    ticket = relationship("Ticket", back_populates="responses")

