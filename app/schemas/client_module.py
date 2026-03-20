"""
Schemas for Client Modules, SMTP Config, and Mail Templates.
"""

from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema, TimestampSchema


# ============== SMTP Config Schemas ==============

class ClientSmtpConfigCreate(BaseSchema):
    """Create SMTP config for a client."""
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(default=587, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=500)
    from_email: EmailStr
    from_name: str | None = None
    use_tls: bool = True


class ClientSmtpConfigUpdate(BaseSchema):
    """Update SMTP config."""
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    from_email: EmailStr | None = None
    from_name: str | None = None
    use_tls: bool | None = None


class ClientSmtpConfigResponse(TimestampSchema):
    """SMTP config response (password masked)."""
    id: int
    client_id: int
    host: str
    port: int
    username: str
    password_set: bool = True  # Never expose actual password
    from_email: str
    from_name: str | None = None
    use_tls: bool


# ============== Mail Template Schemas ==============

class ClientMailTemplateCreate(BaseSchema):
    """Create a mail template."""
    name: str = Field(..., min_length=1, max_length=255)
    subject: str = Field(..., min_length=1, max_length=500)
    html_body: str = Field(..., min_length=1)
    to_email: str | None = None
    from_email: EmailStr | None = None
    cc_email: list[EmailStr] | None = None
    bcc_email: list[EmailStr] | None = None
    variables: list[str] | None = None


class ClientMailTemplateUpdate(BaseSchema):
    """Update a mail template."""
    name: str | None = None
    subject: str | None = None
    html_body: str | None = None
    to_email: str | None = None
    from_email: EmailStr | None = None
    cc_email: list[EmailStr] | None = None
    bcc_email: list[EmailStr] | None = None
    variables: list[str] | None = None


class ClientMailTemplateResponse(TimestampSchema):
    """Mail template response."""
    id: int
    client_id: int
    name: str
    subject: str
    html_body: str
    to_email: str | None = None
    from_email: str | None = None
    cc_email: list[str] | None = None
    bcc_email: list[str] | None = None
    variables: list[str] | None = None


class ClientMailTemplateListResponse(BaseSchema):
    """Mail template list item."""
    id: int
    client_id: int
    name: str
    subject: str
    variables: list[str] | None = None


# ============== Send Email Schema ==============

class ClientSendEmailRequest(BaseSchema):
    """Send email using client SMTP + template."""
    template_id: int | None = None  # Use a saved template
    to_email: EmailStr
    subject: str | None = None  # Override template subject
    html_body: str | None = None  # Override template body (for custom emails)
    variables: dict[str, str] | None = None  # Variable substitution
    from_email: EmailStr | None = None
    cc: list[EmailStr] | None = None
    bcc: list[EmailStr] | None = None


# ============== Module Definition Schemas ==============

class ModuleFieldDef(BaseSchema):
    """A single field definition within a module."""
    name: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern="^(text|number|email|date|textarea|select|checkbox|file|image|phone|url|color|time|datetime|radio|password)$")
    required: bool = False
    options: list[str] | None = None  # For select type
    placeholder: str | None = None
    default_value: str | None = None


class ClientModuleCreate(BaseSchema):
    """Create a dynamic module."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    icon: str | None = "HiOutlineCollection"
    fields: list[ModuleFieldDef] = Field(..., min_length=1)
    mail_template_id: int | None = None


class ClientModuleUpdate(BaseSchema):
    """Update a module definition."""
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    fields: list[ModuleFieldDef] | None = None
    mail_template_id: int | None = None


class ClientModuleResponse(TimestampSchema):
    """Module definition response."""
    id: int
    client_id: int
    name: str
    slug: str
    description: str | None = None
    icon: str | None = None
    fields: list[dict] = []
    mail_template_id: int | None = None
    record_count: int = 0


class ClientModuleListResponse(BaseSchema):
    """Module list item."""
    id: int
    client_id: int
    name: str
    slug: str
    description: str | None = None
    icon: str | None = None
    mail_template_id: int | None = None
    field_count: int = 0
    record_count: int = 0


# ============== Module Record Schemas ==============

class ClientModuleRecordCreate(BaseSchema):
    """Create a record in a module."""
    data: dict = Field(..., min_length=1)


class ClientModuleRecordUpdate(BaseSchema):
    """Update a record."""
    data: dict = Field(..., min_length=1)


class ClientModuleRecordResponse(TimestampSchema):
    """Record response."""
    id: int
    module_id: int
    data: dict = {}
    email_sent: bool = False
