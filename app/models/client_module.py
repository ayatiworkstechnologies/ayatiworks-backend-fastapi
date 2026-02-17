"""
Client Module models.
Dynamic modules, SMTP config, and mail templates per client.
"""

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship

from app.models.base import AuditMixin, BaseModel


class ClientSmtpConfig(BaseModel, AuditMixin):
    """
    Per-client SMTP configuration.
    When sending emails in a client context, use this instead of global SMTP.
    """

    __tablename__ = "client_smtp_configs"

    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, unique=True)

    host = Column(String(255), nullable=False)
    port = Column(Integer, default=587)
    username = Column(String(255), nullable=False)
    password = Column(String(500), nullable=False)
    from_email = Column(String(255), nullable=False)
    from_name = Column(String(255), nullable=True)
    use_tls = Column(Boolean, default=True)

    # Relationships
    client = relationship("Client", backref="smtp_config", uselist=False)


class ClientMailTemplate(BaseModel, AuditMixin):
    """
    Reusable email template per client.
    Supports variable substitution via {{variable_name}} syntax.
    """

    __tablename__ = "client_mail_templates"

    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    html_body = Column(Text, nullable=False)
    
    # Optional overrides
    from_email = Column(String(255), nullable=True)
    cc_email = Column(JSON, nullable=True, default=list) # List of strings
    bcc_email = Column(JSON, nullable=True, default=list) # List of strings

    # JSON array of variable names used in the template, e.g. ["name", "email", "company"]
    variables = Column(JSON, nullable=True, default=list)

    # Relationships
    client = relationship("Client", backref="mail_templates")


class ClientModule(BaseModel, AuditMixin):
    """
    Dynamic module definition per client.
    Defines custom fields that auto-generate CRUD APIs.
    """

    __tablename__ = "client_modules"

    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True, default="HiOutlineCollection")

    # JSON array of field definitions:
    # [{"name": "full_name", "label": "Full Name", "type": "text", "required": true},
    #  {"name": "age", "label": "Age", "type": "number", "required": false},
    #  {"name": "status", "label": "Status", "type": "select", "options": ["active", "inactive"]}]
    # Supported types: text, number, email, date, textarea, select, checkbox
    fields = Column(JSON, nullable=False, default=list)

    # Optional: Link to an email template for auto-responders
    mail_template_id = Column(Integer, ForeignKey("client_mail_templates.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    records = relationship("ClientModuleRecord", back_populates="module", cascade="all, delete-orphan")
    client = relationship("Client", backref="modules")
    mail_template = relationship("ClientMailTemplate", backref="assigned_modules")


class ClientModuleRecord(BaseModel, AuditMixin):
    """
    Data record for a dynamic client module.
    Stores all field values as JSON.
    """

    __tablename__ = "client_module_records"

    module_id = Column(Integer, ForeignKey("client_modules.id", ondelete="CASCADE"), nullable=False)

    # JSON object: {"full_name": "John Doe", "age": 30, "status": "active"}
    data = Column(JSON, nullable=False, default=dict)

    # Relationships
    module = relationship("ClientModule", back_populates="records")
