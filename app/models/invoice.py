"""
Invoice and Billing models.
"""

import enum
from datetime import date

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.models.base import AuditMixin, BaseModel


class InvoiceStatus(enum.Enum):
    """Invoice status enum."""
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Invoice(BaseModel, AuditMixin):
    """
    Invoice model.
    """

    __tablename__ = "invoices"

    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)

    # Invoice Details
    invoice_number = Column(String(50), unique=True, nullable=False)
    reference = Column(String(100), nullable=True)

    # Dates
    issue_date = Column(Date, nullable=False, default=date.today)
    due_date = Column(Date, nullable=False)

    # Amounts
    subtotal = Column(Numeric(12, 2), default=0)
    discount = Column(Numeric(12, 2), default=0)
    discount_type = Column(String(20), default="fixed")  # fixed, percentage
    tax = Column(Numeric(12, 2), default=0)
    tax_rate = Column(Float, default=0)
    total = Column(Numeric(12, 2), default=0)
    amount_paid = Column(Numeric(12, 2), default=0)
    amount_due = Column(Numeric(12, 2), default=0)

    currency = Column(String(3), default="USD")

    # Status
    status = Column(String(20), default=InvoiceStatus.DRAFT.value)

    # Notes
    notes = Column(Text, nullable=True)
    terms = Column(Text, nullable=True)

    # Sent
    sent_at = Column(DateTime, nullable=True)
    viewed_at = Column(DateTime, nullable=True)

    # Relationships
    client = relationship("Client", backref="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(BaseModel):
    """
    Invoice line item.
    """

    __tablename__ = "invoice_items"

    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)

    description = Column(Text, nullable=False)
    quantity = Column(Float, default=1)
    rate = Column(Numeric(12, 2), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)

    # For time-based billing
    hours = Column(Float, nullable=True)

    order = Column(Integer, default=0)

    # Relationships
    invoice = relationship("Invoice", back_populates="items")


class Payment(BaseModel, AuditMixin):
    """
    Payment record.
    """

    __tablename__ = "payments"

    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)

    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD")

    payment_date = Column(Date, nullable=False)
    payment_method = Column(String(50), nullable=True)  # bank, cash, cheque, online

    reference = Column(String(100), nullable=True)
    transaction_id = Column(String(100), nullable=True)

    notes = Column(Text, nullable=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="payments")

