"""
Invoice and Billing API routes.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import PermissionChecker
from app.core.exceptions import ResourceNotFoundError
from app.database import get_db
from app.models.auth import User
from app.models.invoice import Invoice, InvoiceItem, InvoiceStatus, Payment
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
    PaymentCreate,
    PaymentResponse,
)

router = APIRouter(prefix="/invoices", tags=["Invoices"])


def generate_invoice_number(db: Session) -> str:
    """Generate next invoice number."""
    year = date.today().year
    prefix = f"INV-{year}-"

    last = db.query(func.max(Invoice.invoice_number)).filter(
        Invoice.invoice_number.like(f"{prefix}%")
    ).scalar()

    if last:
        try:
            num = int(last.replace(prefix, "")) + 1
        except ValueError:
            num = 1
    else:
        num = 1

    return f"{prefix}{num:04d}"


@router.get("", response_model=PaginatedResponse[InvoiceListResponse])
async def list_invoices(
    client_id: int | None = None,
    status: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("invoice.view")),
    db: Session = Depends(get_db)
):
    """List all invoices."""
    query = db.query(Invoice).filter(Invoice.is_deleted == False)

    if client_id:
        query = query.filter(Invoice.client_id == client_id)

    if status:
        query = query.filter(Invoice.status == status)

    if from_date:
        query = query.filter(Invoice.issue_date >= from_date)

    if to_date:
        query = query.filter(Invoice.issue_date <= to_date)

    total = query.count()

    offset = (page - 1) * page_size
    invoices = query.order_by(Invoice.issue_date.desc()).offset(offset).limit(page_size).all()

    items = []
    for inv in invoices:
        items.append(InvoiceListResponse(
            id=inv.id,
            invoice_number=inv.invoice_number,
            client_name=inv.client.name if inv.client else "",
            issue_date=inv.issue_date,
            due_date=inv.due_date,
            total=inv.total,
            amount_due=inv.amount_due,
            status=inv.status
        ))

    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    current_user: User = Depends(PermissionChecker("invoice.view")),
    db: Session = Depends(get_db)
):
    """Get invoice by ID."""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.is_deleted == False
    ).first()

    if not invoice:
        raise ResourceNotFoundError("Invoice", invoice_id)

    response = InvoiceResponse.model_validate(invoice)
    response.client_name = invoice.client.name if invoice.client else None

    return response


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    data: InvoiceCreate,
    current_user: User = Depends(PermissionChecker("invoice.create")),
    db: Session = Depends(get_db)
):
    """Create a new invoice."""
    invoice_number = generate_invoice_number(db)

    # Calculate totals
    subtotal = Decimal(0)
    for item in data.items:
        subtotal += item.rate * Decimal(str(item.quantity))

    discount = data.discount
    if data.discount_type == "percentage":
        discount = subtotal * (data.discount / 100)

    tax = (subtotal - discount) * Decimal(str(data.tax_rate / 100))
    total = subtotal - discount + tax

    invoice = Invoice(
        invoice_number=invoice_number,
        client_id=data.client_id,
        project_id=data.project_id,
        reference=data.reference,
        issue_date=data.issue_date,
        due_date=data.due_date,
        subtotal=subtotal,
        discount=discount,
        discount_type=data.discount_type,
        tax=tax,
        tax_rate=data.tax_rate,
        total=total,
        amount_due=total,
        currency=data.currency,
        notes=data.notes,
        terms=data.terms,
        created_by=current_user.id
    )

    db.add(invoice)
    db.flush()

    # Add invoice items
    for i, item_data in enumerate(data.items):
        item = InvoiceItem(
            invoice_id=invoice.id,
            description=item_data.description,
            quantity=item_data.quantity,
            rate=item_data.rate,
            amount=item_data.rate * Decimal(str(item_data.quantity)),
            hours=item_data.hours,
            order=i
        )
        db.add(item)

    db.commit()
    db.refresh(invoice)

    return InvoiceResponse.model_validate(invoice)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    data: InvoiceUpdate,
    current_user: User = Depends(PermissionChecker("invoice.edit")),
    db: Session = Depends(get_db)
):
    """Update an invoice."""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.is_deleted == False
    ).first()

    if not invoice:
        raise ResourceNotFoundError("Invoice", invoice_id)

    # Don't allow editing paid invoices
    if invoice.status == InvoiceStatus.PAID.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit a paid invoice"
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(invoice, field) and field not in ['items']:
            setattr(invoice, field, value)

    db.commit()
    db.refresh(invoice)

    return InvoiceResponse.model_validate(invoice)


@router.delete("/{invoice_id}", response_model=MessageResponse)
async def delete_invoice(
    invoice_id: int,
    current_user: User = Depends(PermissionChecker("invoice.delete")),
    db: Session = Depends(get_db)
):
    """Delete an invoice (soft delete)."""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.is_deleted == False
    ).first()

    if not invoice:
        raise ResourceNotFoundError("Invoice", invoice_id)

    # Don't allow deleting paid invoices
    if invoice.status == InvoiceStatus.PAID.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a paid invoice"
        )

    invoice.is_deleted = True
    db.commit()

    return MessageResponse(message="Invoice deleted successfully")


@router.post("/{invoice_id}/send", response_model=MessageResponse)
async def send_invoice(
    invoice_id: int,
    current_user: User = Depends(PermissionChecker("invoice.edit")),
    db: Session = Depends(get_db)
):
    """Mark invoice as sent."""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.is_deleted == False
    ).first()

    if not invoice:
        raise ResourceNotFoundError("Invoice", invoice_id)

    from datetime import datetime
    invoice.status = InvoiceStatus.SENT.value
    invoice.sent_at = datetime.utcnow()

    db.commit()

    # TODO: Send email to client

    return MessageResponse(message="Invoice sent successfully")


@router.post("/{invoice_id}/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def record_payment(
    invoice_id: int,
    data: PaymentCreate,
    current_user: User = Depends(PermissionChecker("invoice.edit")),
    db: Session = Depends(get_db)
):
    """Record a payment for an invoice."""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.is_deleted == False
    ).first()

    if not invoice:
        raise ResourceNotFoundError("Invoice", invoice_id)

    payment = Payment(
        invoice_id=invoice_id,
        amount=data.amount,
        currency=invoice.currency,
        payment_date=data.payment_date,
        payment_method=data.payment_method,
        reference=data.reference,
        notes=data.notes,
        created_by=current_user.id
    )

    db.add(payment)

    # Update invoice
    invoice.amount_paid += data.amount
    invoice.amount_due -= data.amount

    if invoice.amount_due <= 0:
        invoice.status = InvoiceStatus.PAID.value
    else:
        invoice.status = InvoiceStatus.PARTIAL.value

    db.commit()
    db.refresh(payment)

    return PaymentResponse.model_validate(payment)


@router.get("/{invoice_id}/payments", response_model=list[PaymentResponse])
async def get_invoice_payments(
    invoice_id: int,
    current_user: User = Depends(PermissionChecker("invoice.view")),
    db: Session = Depends(get_db)
):
    """Get all payments for an invoice."""
    payments = db.query(Payment).filter(
        Payment.invoice_id == invoice_id,
        Payment.is_deleted == False
    ).order_by(Payment.payment_date).all()

    return [PaymentResponse.model_validate(p) for p in payments]

