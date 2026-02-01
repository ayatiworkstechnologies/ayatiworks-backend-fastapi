"""
Invoice schemas.
"""

from datetime import date
from decimal import Decimal

from app.schemas.common import BaseSchema, TimestampSchema


class InvoiceItemCreate(BaseSchema):
    """Invoice item create schema."""

    description: str
    quantity: float = 1
    rate: Decimal
    hours: float | None = None


class InvoiceItemResponse(BaseSchema):
    """Invoice item response schema."""

    id: int
    description: str
    quantity: float
    rate: Decimal
    amount: Decimal
    hours: float | None = None


class InvoiceCreate(BaseSchema):
    """Invoice create schema."""

    client_id: int
    project_id: int | None = None
    reference: str | None = None
    issue_date: date
    due_date: date
    discount: Decimal = 0
    discount_type: str = "fixed"
    tax_rate: float = 0
    currency: str = "USD"
    notes: str | None = None
    terms: str | None = None
    items: list[InvoiceItemCreate]


class InvoiceUpdate(BaseSchema):
    """Invoice update schema."""

    reference: str | None = None
    due_date: date | None = None
    discount: Decimal | None = None
    tax_rate: float | None = None
    notes: str | None = None
    status: str | None = None


class InvoiceResponse(TimestampSchema):
    """Invoice response schema."""

    id: int
    client_id: int
    project_id: int | None = None
    invoice_number: str
    reference: str | None = None
    issue_date: date
    due_date: date
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    currency: str
    status: str

    # Display
    client_name: str | None = None
    items: list[InvoiceItemResponse] = []


class InvoiceListResponse(BaseSchema):
    """Invoice list item."""

    id: int
    invoice_number: str
    client_name: str
    issue_date: date
    due_date: date
    total: Decimal
    amount_due: Decimal
    status: str


class PaymentCreate(BaseSchema):
    """Payment create schema."""

    invoice_id: int
    amount: Decimal
    payment_date: date
    payment_method: str | None = None
    reference: str | None = None
    notes: str | None = None


class PaymentResponse(TimestampSchema):
    """Payment response schema."""

    id: int
    invoice_id: int
    amount: Decimal
    currency: str
    payment_date: date
    payment_method: str | None = None
    reference: str | None = None

