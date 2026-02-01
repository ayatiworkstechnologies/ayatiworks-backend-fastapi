"""
Public API endpoints (No Authentication).
"""

import os
import shutil
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, File, Form, Request, UploadFile, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import Depends, RoleChecker
from app.config import settings
from app.core.exceptions import ResourceNotFoundError, ValidationError
from app.database import get_db
from app.models.auth import User
from app.models.public import CareerApplication, ContactEnquiry
from app.schemas.public import (
    CareerListResponse,
    CareerResponse,
    CareerUpdate,
    ContactCreate,
    ContactListResponse,
    ContactResponse,
    ContactUpdate,
)
from app.services.email_service import email_service

router = APIRouter(prefix="/public", tags=["Public"])


@router.post("/contact", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    request: Request,
    data: ContactCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Submit a contact enquiry.
    """
    # Create record
    enquiry = ContactEnquiry(
        name=data.name,
        email=data.email,
        phone=data.phone,
        subject=data.subject,
        message=data.message,
        ip_address=request.client.host if request.client else None
    )

    db.add(enquiry)
    db.commit()
    db.refresh(enquiry)

    # Send emails in background
    email_data = {
        "id": enquiry.id,
        "name": enquiry.name,
        "email": enquiry.email,
        "phone": enquiry.phone,
        "subject": enquiry.subject,
        "message": enquiry.message,
        "ip_address": enquiry.ip_address
    }
    background_tasks.add_task(email_service.send_contact_emails, email_data)

    return enquiry


# =======================
# Contact Admin Endpoints
# =======================

@router.get("/contact", response_model=ContactListResponse)
async def list_contacts(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    current_user: User = Depends(RoleChecker(["Super Admin", "Admin", "HR", "Manager"])),
    db: Session = Depends(get_db)
):
    """List contact enquiries (Admin)."""
    # Create base query
    query = db.query(ContactEnquiry)

    # Apply filters
    if status:
        query = query.filter(ContactEnquiry.status == status)

    # Get total count
    total = query.count()

    # Get paginated data
    items = query.order_by(desc(ContactEnquiry.id))\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()

    return ContactListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/contact/{id}", response_model=ContactResponse)
async def get_contact(
    id: int,
    current_user: User = Depends(RoleChecker(["Super Admin", "Admin", "HR", "Manager"])),
    db: Session = Depends(get_db)
):
    """Get contact enquiry details (Admin)."""
    enquiry = db.query(ContactEnquiry).filter(ContactEnquiry.id == id).first()
    if not enquiry:
        raise ResourceNotFoundError("Contact enquiry", id)
    return enquiry


@router.put("/contact/{id}", response_model=ContactResponse)
async def update_contact(
    id: int,
    data: ContactUpdate,
    current_user: User = Depends(RoleChecker(["Super Admin", "Admin", "HR", "Manager"])),
    db: Session = Depends(get_db)
):
    """Update contact enquiry status (Admin)."""
    enquiry = db.query(ContactEnquiry).filter(ContactEnquiry.id == id).first()
    if not enquiry:
        raise ResourceNotFoundError("Contact enquiry", id)

    enquiry.status = data.status
    # Note: 'notes' field would need to be added to model if we want to store it
    # Currently just updating status based on model definition

    enquiry.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(enquiry)
    return enquiry


@router.delete("/contact/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    id: int,
    current_user: User = Depends(RoleChecker(["Super Admin", "Admin", "HR", "Manager"])),
    db: Session = Depends(get_db)
):
    """Delete contact enquiry (Admin)."""
    enquiry = db.query(ContactEnquiry).filter(ContactEnquiry.id == id).first()
    if not enquiry:
        raise ResourceNotFoundError("Contact enquiry", id)

    db.delete(enquiry)
    db.commit()


# =======================
# Careers Public Endpoint
# =======================

@router.post("/careers", response_model=CareerResponse, status_code=status.HTTP_201_CREATED)
async def submit_application(
    background_tasks: BackgroundTasks,
    first_name: str = Form(..., min_length=2),
    last_name: str = Form(..., min_length=2),
    email: str = Form(..., min_length=5),
    phone: str = Form(..., min_length=10),
    position_applied: str = Form(..., min_length=2),
    experience_years: int | None = Form(None),
    current_company: str | None = Form(None),
    linkedin_url: str | None = Form(None),
    portfolio_url: str | None = Form(None),
    cover_letter: str | None = Form(None),
    resume: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """
    Submit a job application.
    Supports file upload for resume.
    """
    resume_path = None

    # Handle resume upload
    if resume:
        # Validate file type
        allowed_types = ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
        if resume.content_type not in allowed_types:
            raise ValidationError("Invalid file type. Only PDF and Word documents are allowed.", field="resume")

        # Create directory
        upload_dir = os.path.join(settings.UPLOAD_DIR, "resumes")
        os.makedirs(upload_dir, exist_ok=True)

        # Generate generic filename to look clean but avoid collisions
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_name = f"{first_name}_{last_name}_{timestamp}_{resume.filename}".replace(" ", "_")
        file_path = os.path.join(upload_dir, safe_name)

        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(resume.file, buffer)

            # Use relative path or full URL depending on storage strategy
            # Here assuming local storage, we'll store relative path
            resume_path = f"/uploads/resumes/{safe_name}"

        except Exception as e:
            raise ValidationError(f"Failed to upload resume: {str(e)}", field="resume")

    # Create record
    application = CareerApplication(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        position_applied=position_applied,
        experience_years=experience_years,
        current_company=current_company,
        linkedin_url=linkedin_url,
        portfolio_url=portfolio_url,
        cover_letter=cover_letter,
        resume_url=resume_path
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    # Send emails in background
    email_data = {
        "id": application.id,
        "first_name": application.first_name,
        "last_name": application.last_name,
        "email": application.email,
        "phone": application.phone,
        "position_applied": application.position_applied,
        "experience_years": application.experience_years,
        "current_company": application.current_company,
        "linkedin_url": application.linkedin_url,
        "portfolio_url": application.portfolio_url,
        "resume_url": resume_path, # In production, convert to full URL
        "cover_letter": application.cover_letter
    }
    background_tasks.add_task(email_service.send_career_emails, email_data)

    return application


# =======================
# Careers Admin Endpoints
# =======================

@router.get("/careers", response_model=CareerListResponse)
async def list_applications(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    position: str | None = None,
    current_user: User = Depends(RoleChecker(["Super Admin", "Admin", "HR", "Manager"])),
    db: Session = Depends(get_db)
):
    """List job applications (Admin)."""
    query = db.query(CareerApplication)

    if status:
        query = query.filter(CareerApplication.status == status)
    if position:
        query = query.filter(CareerApplication.position_applied.ilike(f"%{position}%"))

    total = query.count()
    items = query.order_by(desc(CareerApplication.id))\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()

    return CareerListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/careers/{id}", response_model=CareerResponse)
async def get_application(
    id: int,
    current_user: User = Depends(RoleChecker(["Super Admin", "Admin", "HR", "Manager"])),
    db: Session = Depends(get_db)
):
    """Get job application details (Admin)."""
    application = db.query(CareerApplication).filter(CareerApplication.id == id).first()
    if not application:
        raise ResourceNotFoundError("Job application", id)
    return application


@router.put("/careers/{id}", response_model=CareerResponse)
async def update_application(
    id: int,
    data: CareerUpdate,
    current_user: User = Depends(RoleChecker(["Super Admin", "Admin", "HR", "Manager"])),
    db: Session = Depends(get_db)
):
    """Update job application status (Admin)."""
    application = db.query(CareerApplication).filter(CareerApplication.id == id).first()
    if not application:
        raise ResourceNotFoundError("Job application", id)

    application.status = data.status
    # Notes field would need to be added to model to store notes

    application.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(application)
    return application


@router.delete("/careers/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    id: int,
    current_user: User = Depends(RoleChecker(["Super Admin", "Admin", "HR", "Manager"])),
    db: Session = Depends(get_db)
):
    """Delete job application (Admin)."""
    application = db.query(CareerApplication).filter(CareerApplication.id == id).first()
    if not application:
        raise ResourceNotFoundError("Job application", id)

    db.delete(application)
    db.commit()

