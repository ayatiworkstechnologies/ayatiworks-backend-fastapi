"""
Public API endpoints (No Authentication).
"""

import os
import shutil
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Body, File, Form, Request, UploadFile, status
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



# =======================
# Dynamic Public API (API Key Protected)
# =======================

from fastapi import Header, HTTPException
from app.models.client import Client
from app.models.client_module import ClientModule, ClientModuleRecord, ClientSmtpConfig, ClientMailTemplate
from app.schemas.client_module import ClientSendEmailRequest, ClientModuleRecordResponse
from app.schemas.common import MessageResponse, PaginatedResponse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import ssl
from jinja2 import Environment, BaseLoader
import logging

logger = logging.getLogger(__name__)

def get_client_by_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> User:  # Returning Client actually
    from app.models.client import Client
    client = db.query(Client).filter(Client.api_key == x_api_key, Client.is_deleted == False).first()
    if not client:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return client


@router.post("/{client_slug}/send-email", response_model=MessageResponse)
async def public_send_email(
    client_slug: str,
    data: ClientSendEmailRequest,
    client: Client = Depends(get_client_by_api_key),
    db: Session = Depends(get_db),
):
    """
    Send email via public API (API Key required).
    Uses Client's SMTP config or System fallback.
    """
    if client.slug != client_slug:
         raise HTTPException(status_code=403, detail="API Key does not match client context")

    # Get client SMTP config
    smtp_config = db.query(ClientSmtpConfig).filter(
        ClientSmtpConfig.client_id == client.id,
        ClientSmtpConfig.is_deleted == False,
    ).first()

    # Resolve subject and body
    subject = data.subject
    html_body = data.html_body

    if data.template_id:
        template = db.query(ClientMailTemplate).filter(
            ClientMailTemplate.id == data.template_id,
            ClientMailTemplate.client_id == client.id,
            ClientMailTemplate.is_deleted == False,
        ).first()
        if not template:
            raise HTTPException(status_code=404, detail="Mail template not found")

        subject = data.subject or template.subject
        html_body = data.html_body or template.html_body

    if not subject or not html_body:
        raise HTTPException(status_code=400, detail="Subject and body are required")

    # Variable substitution using Jinja2
    if data.variables:
        jinja_env = Environment(loader=BaseLoader())
        try:
            subject_tmpl = jinja_env.from_string(subject)
            subject = subject_tmpl.render(**data.variables)

            body_tmpl = jinja_env.from_string(html_body)
            html_body = body_tmpl.render(**data.variables)
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            raise HTTPException(status_code=400, detail=f"Template rendering error: {str(e)}")

    # Use System SMTP if no client config
    if not smtp_config:
        from app.services.email_service import email_service
        try:
            success = email_service.send_email(
                to_email=data.to_email,
                subject=subject,
                html_content=html_body,
                cc=data.cc,
                bcc=data.bcc
            )
            if not success:
               raise Exception("System email service returned failure")

            return MessageResponse(message=f"Email sent successfully via System SMTP to {data.to_email}")
        except Exception as e:
             logger.error(f"System email sending failed for client {client.id}: {e}")
             raise HTTPException(status_code=500, detail=f"Failed to send email via System SMTP: {str(e)}")

    # Use Client Custom SMTP
    try:
        # Wrap in base email template
        from app.services.email_service import email_service
        try:
            wrapped_body = email_service.render_template(
                'email/client_custom.html',
                {'custom_content': html_body, 'title': subject}
            )
        except Exception:
            wrapped_body = html_body

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        from_display = f"{smtp_config.from_name} <{smtp_config.from_email}>" if smtp_config.from_name else smtp_config.from_email
        msg["From"] = from_display
        msg["To"] = data.to_email

        if data.cc:
            msg["Cc"] = ", ".join(data.cc)

        msg.attach(MIMEText(wrapped_body, "html"))

        recipients = [data.to_email]
        if data.cc:
            recipients.extend(data.cc)
        if data.bcc:
            recipients.extend(data.bcc)

        context = ssl.create_default_context()
        if smtp_config.port == 465:
            server = smtplib.SMTP_SSL(smtp_config.host, smtp_config.port, context=context)
        else:
            server = smtplib.SMTP(smtp_config.host, smtp_config.port)
            if smtp_config.use_tls:
                server.starttls(context=context)

        server.login(smtp_config.username, smtp_config.password)
        server.sendmail(smtp_config.from_email, recipients, msg.as_string())
        server.quit()

        return MessageResponse(message=f"Email sent successfully to {data.to_email}")

    except Exception as e:
        logger.error(f"Email sending failed for client {client.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@router.get("/{client_slug}/{module_slug}/records", response_model=PaginatedResponse[ClientModuleRecordResponse])
async def public_list_records(
    client_slug: str,
    module_slug: str,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    client: Client = Depends(get_client_by_api_key),
    db: Session = Depends(get_db),
):
    """List records for a module via public API."""
    if client.slug != client_slug:
         raise HTTPException(status_code=403, detail="API Key does not match client context")

    module = db.query(ClientModule).filter(
        ClientModule.client_id == client.id,
        ClientModule.slug == module_slug,
        ClientModule.is_deleted == False,
    ).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    query = db.query(ClientModuleRecord).filter(
        ClientModuleRecord.module_id == module.id,
        ClientModuleRecord.is_deleted == False,
    )
    # Simple search implementation if needed later

    total = query.count()
    records = query.order_by(ClientModuleRecord.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items = [
        ClientModuleRecordResponse(
            id=r.id,
            module_id=r.module_id,
            data=r.data,
            created_at=r.created_at,
            updated_at=r.updated_at,
            created_by=r.created_by,
            updated_by=r.updated_by
        ) for r in records
    ]

    return PaginatedResponse.create(items, total, page, page_size)


@router.post("/{client_slug}/{module_slug}/records", response_model=ClientModuleRecordResponse, status_code=status.HTTP_201_CREATED)
async def public_create_record(
    client_slug: str,
    module_slug: str,
    payload: dict = Body(...),
    client: Client = Depends(get_client_by_api_key),
    db: Session = Depends(get_db),
):
    """Create a record via public API."""
    if client.slug != client_slug:
         raise HTTPException(status_code=403, detail="API Key does not match client context")

    module = db.query(ClientModule).filter(
        ClientModule.client_id == client.id,
        ClientModule.slug == module_slug,
        ClientModule.is_deleted == False,
    ).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Optional: Validate data against module fields here

    # Determine data structure (support both {"data": {...}} and flat {...})
    if "data" in payload and isinstance(payload["data"], dict) and len(payload) <= 2:
        record_data = payload["data"]
        is_active = payload.get("is_active", True)
    else:
        record_data = payload
        is_active = True

    # Validate required fields
    if module.fields:
        for field in module.fields:
            if field.get('required') and field.get('name') not in record_data:
                raise HTTPException(status_code=400, detail=f"Field '{field.get('label') or field.get('name')}' is required")

    record = ClientModuleRecord(
        module_id=module.id,
        data=record_data,
        is_active=is_active,
        # Created by is None for public API or maybe a system user? 
        # For now leaving it null or we could track it via API key if we wanted.
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Auto-send email if template is assigned
    if module.mail_template_id:
        try:
            # 1. Get Template
            template = db.query(ClientMailTemplate).filter(
                ClientMailTemplate.id == module.mail_template_id,
                ClientMailTemplate.client_id == client.id,
                ClientMailTemplate.is_deleted == False
            ).first()

            if template:
                # 2. Determine Recipient
                to_email = template.to_email
                jinja_env = Environment(loader=BaseLoader())

                # If template has a defined recipient, try to render it (handles {{email}} or static admin@example.com)
                if to_email:
                    try:
                        to_email_tmpl = jinja_env.from_string(to_email)
                        to_email = to_email_tmpl.render(**record.data).strip()
                    except Exception as e:
                        logger.warning(f"Failed to render to_email template '{to_email}': {e}")
                        # If render fails but it looked like a simple email, keep it. 
                        # If it was purely a variable {{x}} that failed, it might be empty now.
                        pass

                # Fallback 1 & 2 REMOVED: Strict adherence to Template Configuration
                # if not to_email: ... (removed)

                if to_email:
                    # 3. Render Content
                    subject = template.subject
                    html_body = template.html_body
                    
                    try:
                        subject_tmpl = jinja_env.from_string(subject)
                        subject = subject_tmpl.render(**record.data)

                        body_tmpl = jinja_env.from_string(html_body)
                        html_body = body_tmpl.render(**record.data)

                        # Append file/image attachments
                        from app.api.v1.client_modules import _build_file_image_html
                        attachments_html = _build_file_image_html(module.fields or [], record.data)
                        if attachments_html:
                            html_body += attachments_html
                    except Exception as e:
                        logger.error(f"Auto-email content rendering failed: {e}")
                        to_email = None # Skip sending if content fails

                    if to_email:
                        # 4. Send Email (Copy of public_send_email logic)
                        # STRICT MODE: Only use Template CC/BCC
                        final_cc = template.cc_email or []
                        final_bcc = template.bcc_email or []

                        # Remove duplicates
                        final_cc = list(set(final_cc))
                        final_bcc = list(set(final_bcc))

                        smtp_config = db.query(ClientSmtpConfig).filter(
                            ClientSmtpConfig.client_id == client.id,
                            ClientSmtpConfig.is_deleted == False
                        ).first()

                        if not smtp_config:
                            # System SMTP
                            from app.services.email_service import email_service
                            email_service.send_email(
                                to_email=to_email,
                                subject=subject,
                                html_content=html_body,
                                cc=final_cc,
                                bcc=final_bcc
                            )
                        else:
                            # Client Custom SMTP
                            # Wrap in base email template
                            from app.services.email_service import email_service
                            try:
                                wrapped_body = email_service.render_template(
                                    'email/client_custom.html',
                                    {'custom_content': html_body, 'title': subject}
                                )
                            except Exception:
                                wrapped_body = html_body

                            msg = MIMEMultipart("alternative")
                            msg["Subject"] = subject
                            from_display = f"{smtp_config.from_name} <{smtp_config.from_email}>" if smtp_config.from_name else smtp_config.from_email
                            msg["From"] = from_display
                            msg["To"] = to_email

                            if final_cc:
                                msg["Cc"] = ", ".join(final_cc)

                            recipients = [to_email]
                            if final_cc:
                                recipients.extend(final_cc)
                            if final_bcc:
                                recipients.extend(final_bcc)

                            msg.attach(MIMEText(wrapped_body, "html"))

                            context = ssl.create_default_context()
                            if smtp_config.port == 465:
                                server = smtplib.SMTP_SSL(smtp_config.host, smtp_config.port, context=context)
                            else:
                                server = smtplib.SMTP(smtp_config.host, smtp_config.port)
                                if smtp_config.use_tls:
                                    server.starttls(context=context)

                            server.login(smtp_config.username, smtp_config.password)
                            server.sendmail(smtp_config.from_email, recipients, msg.as_string())
                            server.quit()

        except Exception as e:
            logger.error(f"Failed to auto-send email for record {record.id}: {e}")
            # Continue without erroring out the response

    return ClientModuleRecordResponse(
        id=record.id,
        module_id=record.module_id,
        data=record.data,
        created_at=record.created_at,
        updated_at=record.updated_at,
        created_by=record.created_by,
        updated_by=record.updated_by
    )
