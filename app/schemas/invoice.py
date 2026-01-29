"""
Invoice schemas.
"""

from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema, TimestampSchema


class InvoiceItemCreate(BaseSchema):
    """Invoice item create schema."""
    
    description: str
    quantity: float = 1
    rate: Decimal
    hours: Optional[float] = None


class InvoiceItemResponse(BaseSchema):
    """Invoice item response schema."""
    
    id: int
    description: str
    quantity: float
    rate: Decimal
    amount: Decimal
    hours: Optional[float] = None


class InvoiceCreate(BaseSchema):
    """Invoice create schema."""
    
    client_id: int
    project_id: Optional[int] = None
    reference: Optional[str] = None
    issue_date: date
    due_date: date
    discount: Decimal = 0
    discount_type: str = "fixed"
    tax_rate: float = 0
    currency: str = "USD"
    notes: Optional[str] = None
    terms: Optional[str] = None
    items: List[InvoiceItemCreate]


class InvoiceUpdate(BaseSchema):
    """Invoice update schema."""
    
    reference: Optional[str] = None
    due_date: Optional[date] = None
    discount: Optional[Decimal] = None
    tax_rate: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class InvoiceResponse(TimestampSchema):
    """Invoice response schema."""
    
    id: int
    client_id: int
    project_id: Optional[int] = None
    invoice_number: str
    reference: Optional[str] = None
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
    client_name: Optional[str] = None
    items: List[InvoiceItemResponse] = []


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
    payment_method: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None


class PaymentResponse(TimestampSchema):
    """Payment response schema."""
    
    id: int
    invoice_id: int
    amount: Decimal
    currency: str
    payment_date: date
    payment_method: Optional[str] = None
    reference: Optional[str] = None
