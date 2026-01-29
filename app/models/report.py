"""
Reporting and Analytics models.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, JSON, DateTime
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, AuditMixin


class Report(BaseModel, AuditMixin):
    """Saved report definition."""
    
    __tablename__ = "reports"
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Type
    report_type = Column(String(50), nullable=False)  # attendance, leave, payroll, project, custom
    
    # Configuration
    config = Column(JSON, nullable=False)  # {filters, columns, grouping, sorting}
    
    # Visualization
    chart_type = Column(String(50), nullable=True)  # bar, line, pie, table
    chart_config = Column(JSON, nullable=True)
    
    # Scheduling
    is_scheduled = Column(Boolean, default=False)
    schedule = Column(String(100), nullable=True)  # Cron expression
    last_run_at = Column(DateTime, nullable=True)
    
    # Recipients for scheduled reports
    recipients = Column(JSON, nullable=True)  # Array of email addresses
    
    # Access
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False)
    shared_with = Column(JSON, nullable=True)  # Array of user IDs
    
    # Company
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)


class ReportExport(BaseModel):
    """Report export history."""
    
    __tablename__ = "report_exports"
    
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=True)
    
    # Export info
    export_type = Column(String(20), nullable=False)  # pdf, excel, csv
    file_path = Column(String(500), nullable=True)
    
    # Filters used
    filters = Column(JSON, nullable=True)
    
    # Status
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    # User
    exported_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    exported_at = Column(DateTime, default=datetime.utcnow)


class Dashboard(BaseModel, AuditMixin):
    """Custom dashboard."""
    
    __tablename__ = "dashboards"
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Layout
    layout = Column(JSON, nullable=True)  # Grid layout configuration
    
    # Widgets
    widgets = Column(JSON, nullable=True)  # [{type, config, position}]
    
    # Owner
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Access
    is_default = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)
    
    # Role-based
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)


class AnalyticsEvent(BaseModel):
    """Analytics event tracking."""
    
    __tablename__ = "analytics_events"
    
    # User
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(String(100), nullable=True)
    
    # Event
    event_name = Column(String(100), nullable=False, index=True)
    event_category = Column(String(50), nullable=True)
    
    # Properties
    properties = Column(JSON, nullable=True)
    
    # Context
    page_url = Column(String(500), nullable=True)
    referrer = Column(String(500), nullable=True)
    
    # Device
    device_type = Column(String(20), nullable=True)
    browser = Column(String(50), nullable=True)
    os = Column(String(50), nullable=True)
    ip_address = Column(String(50), nullable=True)
    
    # Timestamp
    occurred_at = Column(DateTime, default=datetime.utcnow, index=True)
