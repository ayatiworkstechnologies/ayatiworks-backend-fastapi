"""
Client Modules API routes.
SMTP config, mail templates, dynamic modules, and module records.
Admin-only access — clients cannot login.
"""

import logging
import re
import secrets
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from jinja2 import BaseLoader, Environment
from sqlalchemy.orm import Session

from app.api.deps import PermissionChecker
from app.database import get_db
from app.models.auth import User
from app.models.client import Client
from app.models.client_module import (
    ClientMailTemplate,
    ClientModule,
    ClientModuleRecord,
    ClientSmtpConfig,
)
from app.schemas.client_module import (
    ClientMailTemplateCreate,
    ClientMailTemplateListResponse,
    ClientMailTemplateResponse,
    ClientMailTemplateUpdate,
    ClientModuleCreate,
    ClientModuleListResponse,
    ClientModuleRecordCreate,
    ClientModuleRecordResponse,
    ClientModuleRecordUpdate,
    ClientModuleResponse,
    ClientModuleUpdate,
    ClientSendEmailRequest,
    ClientSmtpConfigCreate,
    ClientSmtpConfigResponse,
    ClientSmtpConfigUpdate,
)
from app.schemas.common import MessageResponse, PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Client Modules"])


def _get_client_or_404(client_id: int, db: Session) -> Client:
    """Get client by ID or raise 404."""
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.is_deleted == False,
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def _slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '_', text)
    return text


# ============== SMTP Config Endpoints ==============

@router.get("/clients/{client_id}/smtp", response_model=ClientSmtpConfigResponse | None)
async def get_smtp_config(
    client_id: int,
    current_user: User = Depends(PermissionChecker("mail.view")),
    db: Session = Depends(get_db),
):
    """Get SMTP configuration for a client."""
    _get_client_or_404(client_id, db)
    config = db.query(ClientSmtpConfig).filter(
        ClientSmtpConfig.client_id == client_id,
        ClientSmtpConfig.is_deleted == False,
    ).first()
    if not config:
        return None

    return ClientSmtpConfigResponse(
        id=config.id,
        client_id=config.client_id,
        host=config.host,
        port=config.port,
        username=config.username,
        password_set=bool(config.password),
        from_email=config.from_email,
        from_name=config.from_name,
        use_tls=config.use_tls,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.post("/clients/{client_id}/smtp", response_model=ClientSmtpConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_smtp_config(
    client_id: int,
    data: ClientSmtpConfigCreate,
    current_user: User = Depends(PermissionChecker("mail.manage")),
    db: Session = Depends(get_db),
):
    """Create or update SMTP configuration for a client."""
    _get_client_or_404(client_id, db)

    config = db.query(ClientSmtpConfig).filter(
        ClientSmtpConfig.client_id == client_id,
        ClientSmtpConfig.is_deleted == False,
    ).first()

    if config:
        # Update existing
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(config, field, value)
        config.updated_by = current_user.id
    else:
        # Create new
        config = ClientSmtpConfig(
            client_id=client_id,
            **data.model_dump(),
            created_by=current_user.id,
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    return ClientSmtpConfigResponse(
        id=config.id,
        client_id=config.client_id,
        host=config.host,
        port=config.port,
        username=config.username,
        password_set=bool(config.password),
        from_email=config.from_email,
        from_name=config.from_name,
        use_tls=config.use_tls,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )



@router.post("/clients/{client_id}/smtp/test", response_model=MessageResponse)
async def test_smtp_config(
    client_id: int,
    data: ClientSmtpConfigCreate,
    current_user: User = Depends(PermissionChecker("mail.manage")),
    db: Session = Depends(get_db),
):
    """Test SMTP configuration by attempting to connect and login."""
    _get_client_or_404(client_id, db)

    try:
        # Create SSL context (ignore cert errors for broader compatibility if needed, or default)
        context = ssl.create_default_context()
        
        server = None
        try:
            if data.port == 465:
                server = smtplib.SMTP_SSL(data.host, data.port, context=context)
            else:
                server = smtplib.SMTP(data.host, data.port)
                if data.use_tls:
                    server.starttls(context=context)
            
            # Login
            server.login(data.username, data.password)
        finally:
            if server:
                server.quit()
        
        return MessageResponse(message="SMTP connection successful!")

    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=400, detail="Authentication failed. Check username and password.")
    except smtplib.SMTPConnectError:
        raise HTTPException(status_code=400, detail="Could not connect to the server. Check host and port.")
    except Exception as e:
        logger.error(f"SMTP Test Error: {e}")
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")


@router.delete("/clients/{client_id}/smtp", response_model=MessageResponse)
async def delete_smtp_config(
    client_id: int,
    current_user: User = Depends(PermissionChecker("mail.manage")),
    db: Session = Depends(get_db),
):
    """Delete a client's SMTP configuration (revert to system default)."""
    _get_client_or_404(client_id, db)
    config = db.query(ClientSmtpConfig).filter(
        ClientSmtpConfig.client_id == client_id,
        ClientSmtpConfig.is_deleted == False,
    ).first()
    
    if config:
        config.soft_delete(current_user.id)
        db.commit()
    
    return MessageResponse(message="SMTP configuration removed. Reverted to System SMTP.")


# ============== Mail Template Endpoints ==============

@router.get("/clients/{client_id}/mail-templates", response_model=PaginatedResponse[ClientMailTemplateListResponse])
async def list_mail_templates(
    client_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("mail.view")),
    db: Session = Depends(get_db),
):
    """List mail templates for a client."""
    _get_client_or_404(client_id, db)

    query = db.query(ClientMailTemplate).filter(
        ClientMailTemplate.client_id == client_id,
        ClientMailTemplate.is_deleted == False,
    )
    total = query.count()
    templates = query.order_by(ClientMailTemplate.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    items = [
        ClientMailTemplateListResponse(
            id=t.id,
            client_id=t.client_id,
            name=t.name,
            subject=t.subject,
            variables=t.variables,
        )
        for t in templates
    ]
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/clients/{client_id}/mail-templates/{template_id}", response_model=ClientMailTemplateResponse)
async def get_mail_template(
    client_id: int,
    template_id: int,
    current_user: User = Depends(PermissionChecker("mail.view")),
    db: Session = Depends(get_db),
):
    """Get a specific mail template."""
    _get_client_or_404(client_id, db)
    template = db.query(ClientMailTemplate).filter(
        ClientMailTemplate.id == template_id,
        ClientMailTemplate.client_id == client_id,
        ClientMailTemplate.is_deleted == False,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Mail template not found")

    return ClientMailTemplateResponse(
        id=template.id,
        client_id=template.client_id,
        name=template.name,
        subject=template.subject,
        html_body=template.html_body,
        to_email=template.to_email,
        from_email=template.from_email,
        cc_email=template.cc_email,
        bcc_email=template.bcc_email,
        variables=template.variables,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.post("/clients/{client_id}/mail-templates", response_model=ClientMailTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_mail_template(
    client_id: int,
    data: ClientMailTemplateCreate,
    current_user: User = Depends(PermissionChecker("mail.manage")),
    db: Session = Depends(get_db),
):
    """Create a new mail template."""
    _get_client_or_404(client_id, db)

    template = ClientMailTemplate(
        client_id=client_id,
        **data.model_dump(),
        created_by=current_user.id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    return ClientMailTemplateResponse(
        id=template.id,
        client_id=template.client_id,
        name=template.name,
        subject=template.subject,
        html_body=template.html_body,
        to_email=template.to_email,
        from_email=template.from_email,
        cc_email=template.cc_email,
        bcc_email=template.bcc_email,
        variables=template.variables,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.put("/clients/{client_id}/mail-templates/{template_id}", response_model=ClientMailTemplateResponse)
async def update_mail_template(
    client_id: int,
    template_id: int,
    data: ClientMailTemplateUpdate,
    current_user: User = Depends(PermissionChecker("mail.manage")),
    db: Session = Depends(get_db),
):
    """Update a mail template."""
    _get_client_or_404(client_id, db)
    template = db.query(ClientMailTemplate).filter(
        ClientMailTemplate.id == template_id,
        ClientMailTemplate.client_id == client_id,
        ClientMailTemplate.is_deleted == False,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Mail template not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    template.updated_by = current_user.id

    db.commit()
    db.refresh(template)

    return ClientMailTemplateResponse(
        id=template.id,
        client_id=template.client_id,
        name=template.name,
        subject=template.subject,
        html_body=template.html_body,
        to_email=template.to_email,
        from_email=template.from_email,
        cc_email=template.cc_email,
        bcc_email=template.bcc_email,
        variables=template.variables,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.delete("/clients/{client_id}/mail-templates/{template_id}", response_model=MessageResponse)
async def delete_mail_template(
    client_id: int,
    template_id: int,
    current_user: User = Depends(PermissionChecker("mail.manage")),
    db: Session = Depends(get_db),
):
    """Delete a mail template."""
    _get_client_or_404(client_id, db)
    template = db.query(ClientMailTemplate).filter(
        ClientMailTemplate.id == template_id,
        ClientMailTemplate.client_id == client_id,
        ClientMailTemplate.is_deleted == False,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Mail template not found")

    template.soft_delete(current_user.id)
    db.commit()
    return MessageResponse(message="Mail template deleted successfully")


# ============== Send Email Endpoint ==============

@router.post("/clients/{client_id}/send-email", response_model=MessageResponse)
async def send_client_email(
    client_id: int,
    data: ClientSendEmailRequest,
    current_user: User = Depends(PermissionChecker("mail.send")),
    db: Session = Depends(get_db),
):
    """Send email using client's SMTP config and optional template."""
    client = _get_client_or_404(client_id, db)

    # Get client SMTP config
    smtp_config = db.query(ClientSmtpConfig).filter(
        ClientSmtpConfig.client_id == client_id,
        ClientSmtpConfig.is_deleted == False,
    ).first()

    # Resolve subject and body
    subject = data.subject
    html_body = data.html_body

    if data.template_id:
        template = db.query(ClientMailTemplate).filter(
            ClientMailTemplate.id == data.template_id,
            ClientMailTemplate.client_id == client_id,
            ClientMailTemplate.is_deleted == False,
        ).first()
        if not template:
            raise HTTPException(status_code=404, detail="Mail template not found")

        subject = data.subject or template.subject
        html_body = data.html_body or template.html_body
        template_from_email = template.from_email  # Capture template sender
    else:
        template_from_email = None

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
            # Send using system (dashboard) credentials
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
             logger.error(f"System email sending failed for client {client_id}: {e}")
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
        
        # Determine sender: SMTP Config only (User requested "never from mail")
        # effective_from = data.from_email or template_from_email
        # if effective_from:
        #     msg["From"] = effective_from
        # else:
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

        logger.info(f"Client email sent successfully to {data.to_email} from client {client_id}")
        return MessageResponse(message=f"Email sent successfully to {data.to_email}")

    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=400, detail="SMTP authentication failed. Please verify SMTP credentials.")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
    except Exception as e:
        logger.error(f"Email sending failed for client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


# ============== Module Definition Endpoints ==============

@router.get("/clients/{client_id}/modules", response_model=PaginatedResponse[ClientModuleListResponse])
async def list_modules(
    client_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("module.view")),
    db: Session = Depends(get_db),
):
    """List dynamic modules for a client."""
    _get_client_or_404(client_id, db)

    query = db.query(ClientModule).filter(
        ClientModule.client_id == client_id,
        ClientModule.is_deleted == False,
    )
    total = query.count()
    modules = query.order_by(ClientModule.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    # Batch count records instead of N+1
    module_ids = [m.id for m in modules]
    from sqlalchemy import func
    record_counts = {}
    if module_ids:
        counts = db.query(
            ClientModuleRecord.module_id,
            func.count(ClientModuleRecord.id)
        ).filter(
            ClientModuleRecord.module_id.in_(module_ids),
            ClientModuleRecord.is_deleted == False,
        ).group_by(ClientModuleRecord.module_id).all()
        record_counts = {mid: cnt for mid, cnt in counts}

    items = [
        ClientModuleListResponse(
            id=m.id,
            client_id=m.client_id,
            name=m.name,
            slug=m.slug,
            description=m.description,
            icon=m.icon,
            field_count=len(m.fields) if m.fields else 0,
            record_count=record_counts.get(m.id, 0),
        )
        for m in modules
    ]

    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/clients/{client_id}/modules/{module_id}", response_model=ClientModuleResponse)
async def get_module(
    client_id: int,
    module_id: int,
    current_user: User = Depends(PermissionChecker("module.view")),
    db: Session = Depends(get_db),
):
    """Get a specific module definition."""
    _get_client_or_404(client_id, db)
    module = db.query(ClientModule).filter(
        ClientModule.id == module_id,
        ClientModule.client_id == client_id,
        ClientModule.is_deleted == False,
    ).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    record_count = db.query(ClientModuleRecord).filter(
        ClientModuleRecord.module_id == module.id,
        ClientModuleRecord.is_deleted == False,
    ).count()

    return ClientModuleResponse(
        id=module.id,
        client_id=module.client_id,
        name=module.name,
        slug=module.slug,
        description=module.description,
        icon=module.icon,
        fields=module.fields or [],
        record_count=record_count,
        created_at=module.created_at,
        updated_at=module.updated_at,
    )


@router.post("/clients/{client_id}/modules", response_model=ClientModuleResponse, status_code=status.HTTP_201_CREATED)
async def create_module(
    client_id: int,
    data: ClientModuleCreate,
    current_user: User = Depends(PermissionChecker("module.create")),
    db: Session = Depends(get_db),
):
    """Create a new dynamic module with field definitions."""
    _get_client_or_404(client_id, db)

    slug = _slugify(data.name)

    # Check for duplicate slug
    existing = db.query(ClientModule).filter(
        ClientModule.client_id == client_id,
        ClientModule.slug == slug,
        ClientModule.is_deleted == False,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Module '{data.name}' already exists for this client")

    module = ClientModule(
        client_id=client_id,
        name=data.name,
        slug=slug,
        description=data.description,
        icon=data.icon,
        fields=[f.model_dump() for f in data.fields],
        mail_template_id=data.mail_template_id,
        created_by=current_user.id,
    )
    db.add(module)
    db.commit()
    db.refresh(module)

    return ClientModuleResponse(
        id=module.id,
        client_id=module.client_id,
        name=module.name,
        slug=module.slug,
        description=module.description,
        icon=module.icon,
        fields=module.fields or [],
        mail_template_id=module.mail_template_id,
        record_count=0,
        created_at=module.created_at,
        updated_at=module.updated_at,
    )


@router.post("/admin/quick-module", response_model=ClientModuleResponse, status_code=status.HTTP_201_CREATED)
async def quick_create_module(
    client_name: str,
    module_name: str,
    description: str | None = None,
    current_user: User = Depends(PermissionChecker("module.create")),
    db: Session = Depends(get_db),
):
    """
    Quickly create a module by providing Client Name and Module Name.
    Automatically finds the client and sets up default fields.
    """
    # 1. Find Client
    client = db.query(Client).filter(
        Client.name.ilike(f"%{client_name}%"),
        Client.is_deleted == False,
    ).first()

    if not client:
        # Try slug
        client = db.query(Client).filter(
            Client.slug == client_name,
            Client.is_deleted == False,
        ).first()

    if not client:
        raise HTTPException(status_code=404, detail=f"Client '{client_name}' not found")

    # 2. Duplicate Check
    slug = _slugify(module_name)
    existing = db.query(ClientModule).filter(
        ClientModule.client_id == client.id,
        ClientModule.slug == slug,
        ClientModule.is_deleted == False,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Module '{module_name}' already exists for client '{client.name}'")

    # 3. Default Fields
    default_fields = [
        {"name": "name", "label": "Name", "type": "text", "required": True, "placeholder": "Record name"},
        {"name": "status", "label": "Status", "type": "select", "options": ["New", "In Progress", "Done"], "required": True}
    ]

    # 4. Create Module
    module = ClientModule(
        client_id=client.id,
        name=module_name,
        slug=slug,
        description=description,
        icon="HiOutlineCollection",
        fields=default_fields,
        mail_template_id=None,
        created_by=current_user.id,
    )
    db.add(module)
    db.commit()
    db.refresh(module)

    return ClientModuleResponse(
        id=module.id,
        client_id=module.client_id,
        name=module.name,
        slug=module.slug,
        description=module.description,
        icon=module.icon,
        fields=module.fields or [],
        mail_template_id=module.mail_template_id,
        record_count=0,
        created_at=module.created_at,
        updated_at=module.updated_at,
    )


@router.put("/clients/{client_id}/modules/{module_id}", response_model=ClientModuleResponse)
async def update_module(
    client_id: int,
    module_id: int,
    data: ClientModuleUpdate,
    current_user: User = Depends(PermissionChecker("module.edit")),
    db: Session = Depends(get_db),
):
    """Update a module definition."""
    _get_client_or_404(client_id, db)
    module = db.query(ClientModule).filter(
        ClientModule.id == module_id,
        ClientModule.client_id == client_id,
        ClientModule.is_deleted == False,
    ).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    update_data = data.model_dump(exclude_unset=True)

    if 'name' in update_data:
        module.name = update_data['name']
        module.slug = _slugify(update_data['name'])

    if 'description' in update_data:
        module.description = update_data['description']

    if 'icon' in update_data:
        module.icon = update_data['icon']

    if 'fields' in update_data and data.fields is not None:
        module.fields = [f.model_dump() for f in data.fields]

    if 'mail_template_id' in update_data:
        module.mail_template_id = update_data['mail_template_id']

    module.updated_by = current_user.id
    db.commit()
    db.refresh(module)

    record_count = db.query(ClientModuleRecord).filter(
        ClientModuleRecord.module_id == module.id,
        ClientModuleRecord.is_deleted == False,
    ).count()

    return ClientModuleResponse(
        id=module.id,
        client_id=module.client_id,
        name=module.name,
        slug=module.slug,
        description=module.description,
        icon=module.icon,
        fields=module.fields or [],
        mail_template_id=module.mail_template_id,
        record_count=record_count,
        created_at=module.created_at,
        updated_at=module.updated_at,
    )


@router.delete("/clients/{client_id}/modules/{module_id}", response_model=MessageResponse)
async def delete_module(
    client_id: int,
    module_id: int,
    current_user: User = Depends(PermissionChecker("module.delete")),
    db: Session = Depends(get_db),
):
    """Delete a module and all its records."""
    _get_client_or_404(client_id, db)
    module = db.query(ClientModule).filter(
        ClientModule.id == module_id,
        ClientModule.client_id == client_id,
        ClientModule.is_deleted == False,
    ).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    module.soft_delete(current_user.id)
    # Batch soft-delete all records
    from datetime import datetime
    db.query(ClientModuleRecord).filter(
        ClientModuleRecord.module_id == module_id,
        ClientModuleRecord.is_deleted == False,
    ).update(
        {
            ClientModuleRecord.is_deleted: True,
            ClientModuleRecord.deleted_at: datetime.utcnow(),
            ClientModuleRecord.deleted_by: current_user.id,
        },
        synchronize_session="fetch"
    )

    db.commit()
    return MessageResponse(message="Module deleted successfully")


# ============== Module Record Endpoints (Auto API) ==============

@router.get("/clients/{client_id}/modules/{module_id}/records", response_model=PaginatedResponse[ClientModuleRecordResponse])
async def list_module_records(
    client_id: int,
    module_id: int,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("module.view")),
    db: Session = Depends(get_db),
):
    """List records for a module (auto-generated API)."""
    _get_client_or_404(client_id, db)

    module = db.query(ClientModule).filter(
        ClientModule.id == module_id,
        ClientModule.client_id == client_id,
        ClientModule.is_deleted == False,
    ).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    query = db.query(ClientModuleRecord).filter(
        ClientModuleRecord.module_id == module_id,
        ClientModuleRecord.is_deleted == False,
    )

    total = query.count()
    records = query.order_by(ClientModuleRecord.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    items = [
        ClientModuleRecordResponse(
            id=r.id,
            module_id=r.module_id,
            data=r.data or {},
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in records
    ]
    return PaginatedResponse.create(items, total, page, page_size)


@router.post("/clients/{client_id}/modules/{module_id}/records", response_model=ClientModuleRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_module_record(
    client_id: int,
    module_id: int,
    data: ClientModuleRecordCreate,
    current_user: User = Depends(PermissionChecker("module.create")),
    db: Session = Depends(get_db),
):
    """Create a record in a module (auto-generated API)."""
    _get_client_or_404(client_id, db)

    module = db.query(ClientModule).filter(
        ClientModule.id == module_id,
        ClientModule.client_id == client_id,
        ClientModule.is_deleted == False,
    ).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Validate required fields
    fields = module.fields or []
    for field_def in fields:
        if field_def.get('required') and field_def.get('name') not in data.data:
            raise HTTPException(
                status_code=400,
                detail=f"Field '{field_def.get('label', field_def.get('name'))}' is required"
            )

    record = ClientModuleRecord(
        module_id=module_id,
        data=data.data,
        created_by=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return ClientModuleRecordResponse(
        id=record.id,
        module_id=record.module_id,
        data=record.data or {},
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.put("/clients/{client_id}/modules/{module_id}/records/{record_id}", response_model=ClientModuleRecordResponse)
async def update_module_record(
    client_id: int,
    module_id: int,
    record_id: int,
    data: ClientModuleRecordUpdate,
    current_user: User = Depends(PermissionChecker("module.edit")),
    db: Session = Depends(get_db),
):
    """Update a module record."""
    _get_client_or_404(client_id, db)

    record = db.query(ClientModuleRecord).filter(
        ClientModuleRecord.id == record_id,
        ClientModuleRecord.module_id == module_id,
        ClientModuleRecord.is_deleted == False,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    record.data = data.data
    record.updated_by = current_user.id

    db.commit()
    db.refresh(record)

    return ClientModuleRecordResponse(
        id=record.id,
        module_id=record.module_id,
        data=record.data or {},
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.delete("/clients/{client_id}/modules/{module_id}/records/{record_id}", response_model=MessageResponse)
async def delete_module_record(
    client_id: int,
    module_id: int,
    record_id: int,
    current_user: User = Depends(PermissionChecker("module.delete")),
    db: Session = Depends(get_db),
):
    """Delete a module record."""
    _get_client_or_404(client_id, db)

    record = db.query(ClientModuleRecord).filter(
        ClientModuleRecord.id == record_id,
        ClientModuleRecord.module_id == module_id,
        ClientModuleRecord.is_deleted == False,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    record.soft_delete(current_user.id)
    db.commit()
    return MessageResponse(message="Record deleted successfully")


# ============== API Key Management ==============

def _get_client_by_api_key(api_key: str, db: Session) -> Client:
    """Validate API key and return client."""
    if not api_key:
        raise HTTPException(status_code=401, detail="API key is required")
    client = db.query(Client).filter(
        Client.api_key == api_key,
        Client.is_deleted == False,
    ).first()
    if not client:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return client


@router.post("/clients/{client_id}/api-key", response_model=dict)
async def generate_api_key(
    client_id: int,
    current_user: User = Depends(PermissionChecker("module.edit")),
    db: Session = Depends(get_db),
):
    """Generate or regenerate an API key for a client."""
    client = _get_client_or_404(client_id, db)
    # Generate a secure random API key
    client.api_key = secrets.token_hex(32)  # 64 char hex string
    client.updated_by = current_user.id
    db.commit()
    db.refresh(client)
    return {
        "api_key": client.api_key,
        "message": "API key generated successfully. Store it safely — it won't be shown again."
    }


@router.get("/clients/{client_id}/api-key", response_model=dict)
async def get_api_key_status(
    client_id: int,
    current_user: User = Depends(PermissionChecker("module.view")),
    db: Session = Depends(get_db),
):
    """Check if an API key exists for a client (does not reveal the key)."""
    client = _get_client_or_404(client_id, db)
    return {
        "has_api_key": bool(client.api_key),
        "api_key_preview": f"{client.api_key[:8]}...{client.api_key[-4:]}" if client.api_key else None,
    }


@router.delete("/clients/{client_id}/api-key", response_model=MessageResponse)
async def revoke_api_key(
    client_id: int,
    current_user: User = Depends(PermissionChecker("module.edit")),
    db: Session = Depends(get_db),
):
    """Revoke (delete) the API key for a client."""
    client = _get_client_or_404(client_id, db)
    client.api_key = None
    client.updated_by = current_user.id
    db.commit()
    return MessageResponse(message="API key revoked successfully")


# ============== Public API Endpoints (API Key Auth) ==============
# URL format: /public/modules, /public/{module_slug}/records
# Also supports: /public/{client_slug}/modules, /public/{client_slug}/{module_slug}/records
# These endpoints require X-API-Key header instead of JWT token


def _get_client_by_slug_and_key(client_slug: str, api_key: str, db: Session) -> Client:
    """Validate client slug and API key match."""
    if not api_key:
        raise HTTPException(status_code=401, detail="API key is required")
    client = db.query(Client).filter(
        Client.slug == client_slug,
        Client.is_deleted == False,
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if client.api_key != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return client


# --- Simplified Routes (No Slug) ---

@router.get("/public/modules")
async def public_list_modules_simple(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """List all modules (Simplified URL)."""
    return await _public_list_modules_impl(None, x_api_key, db)


@router.get("/public/{module_slug}/records")
async def public_list_records_simple(
    module_slug: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """List records (Simplified URL)."""
    return await _public_list_records_impl(None, module_slug, page, page_size, x_api_key, db)


@router.post("/public/{module_slug}/records", status_code=status.HTTP_201_CREATED)
async def public_create_record_simple(
    module_slug: str,
    data: ClientModuleRecordCreate,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """Create record (Simplified URL)."""
    return await _public_create_record_impl(None, module_slug, data, x_api_key, db)


# --- Slug Routes (With Client Slug) ---

@router.get("/public/{client_slug}/modules")
async def public_list_modules_slug(
    client_slug: str,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """List all modules (Slug URL)."""
    return await _public_list_modules_impl(client_slug, x_api_key, db)


@router.get("/public/{client_slug}/{module_slug}/records")
async def public_list_records_slug(
    client_slug: str,
    module_slug: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """List records (Slug URL)."""
    return await _public_list_records_impl(client_slug, module_slug, page, page_size, x_api_key, db)


@router.post("/public/{client_slug}/{module_slug}/records", status_code=status.HTTP_201_CREATED)
async def public_create_record_slug(
    client_slug: str,
    module_slug: str,
    data: ClientModuleRecordCreate,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """Create record (Slug URL)."""
    return await _public_create_record_impl(client_slug, module_slug, data, x_api_key, db)


# --- Implementations ---

async def _public_list_modules_impl(client_slug: str | None, api_key: str, db: Session):
    if client_slug:
        client = _get_client_by_slug_and_key(client_slug, api_key, db)
    else:
        client = _get_client_by_api_key(api_key, db)

    modules = db.query(ClientModule).filter(
        ClientModule.client_id == client.id,
        ClientModule.is_deleted == False,
    ).order_by(ClientModule.created_at.desc()).all()

    return {
        "client": {"id": client.id, "name": client.name, "slug": client.slug},
        "modules": [
            {
                "id": m.id,
                "name": m.name,
                "slug": m.slug,
                "description": m.description,
                "fields": m.fields or [],
            }
            for m in modules
        ]
    }


async def _public_list_records_impl(client_slug: str | None, module_slug: str, page: int, page_size: int, api_key: str, db: Session):
    if client_slug:
        client = _get_client_by_slug_and_key(client_slug, api_key, db)
    else:
        client = _get_client_by_api_key(api_key, db)

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
    total = query.count()
    records = query.order_by(ClientModuleRecord.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return {
        "client": {"id": client.id, "name": client.name, "slug": client.slug},
        "module": {"id": module.id, "name": module.name, "slug": module.slug},
        "total": total,
        "page": page,
        "page_size": page_size,
        "records": [
            {
                "id": r.id,
                "data": r.data or {},
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
    }


async def _public_create_record_impl(client_slug: str | None, module_slug: str, data: ClientModuleRecordCreate, api_key: str, db: Session):
    if client_slug:
        client = _get_client_by_slug_and_key(client_slug, api_key, db)
    else:
        client = _get_client_by_api_key(api_key, db)

    module = db.query(ClientModule).filter(
        ClientModule.client_id == client.id,
        ClientModule.slug == module_slug,
        ClientModule.is_deleted == False,
    ).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Validate required fields
    fields = module.fields or []
    for field_def in fields:
        if field_def.get('required') and field_def.get('name') not in data.data:
            raise HTTPException(
                status_code=400,
                detail=f"Field '{field_def.get('label', field_def.get('name'))}' is required"
            )

    record = ClientModuleRecord(
        module_id=module.id,
        data=data.data,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "module": module.name,
        "data": record.data,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "message": "Record created successfully",
    }
