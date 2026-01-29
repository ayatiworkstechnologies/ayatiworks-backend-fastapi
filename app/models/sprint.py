"""
Sprint and Time Tracking models.
Agile sprint management and time entry tracking.
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, JSON, Date, Float, DateTime
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel, AuditMixin


class SprintStatus(enum.Enum):
    """Sprint status enum."""
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Sprint(BaseModel, AuditMixin):
    """
    Sprint for agile project management.
    """
    
    __tablename__ = "sprints"
    
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(100), nullable=False)
    goal = Column(Text, nullable=True)
    
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    status = Column(String(20), default=SprintStatus.PLANNED.value)
    
    # Velocity
    planned_points = Column(Integer, default=0)
    completed_points = Column(Integer, default=0)
    
    # Retrospective
    retrospective = Column(JSON, nullable=True)  # {went_well, to_improve, action_items}
    
    # Relationships
    project = relationship("Project", backref="sprints")
    tasks = relationship("Task", backref="sprint")


class Backlog(BaseModel, AuditMixin):
    """
    Product backlog item.
    """
    
    __tablename__ = "backlogs"
    
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # User story format
    as_a = Column(String(100), nullable=True)  # As a [role]
    i_want = Column(Text, nullable=True)  # I want [feature]
    so_that = Column(Text, nullable=True)  # So that [benefit]
    
    # Estimation
    story_points = Column(Integer, nullable=True)
    priority = Column(Integer, default=0)  # Higher = more important
    
    # Status
    status = Column(String(20), default="new")  # new, ready, in_sprint, done
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=True)
    
    # Acceptance criteria
    acceptance_criteria = Column(JSON, nullable=True)
    
    order = Column(Integer, default=0)
    
    # Relationships
    project = relationship("Project", backref="backlogs")


class TimeEntry(BaseModel, AuditMixin):
    """
    Time tracking entry.
    """
    
    __tablename__ = "time_entries"
    
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    
    # Related to
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    
    # Time
    date = Column(Date, nullable=False, index=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    hours = Column(Float, nullable=False)
    
    # Description
    description = Column(Text, nullable=True)
    
    # Billable
    is_billable = Column(Boolean, default=True)
    hourly_rate = Column(Float, nullable=True)
    
    # Status
    is_approved = Column(Boolean, default=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Invoice
    is_invoiced = Column(Boolean, default=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    
    # Relationships
    employee = relationship("Employee", backref="time_entries")
    project = relationship("Project", backref="time_entries")
    task = relationship("Task", backref="time_entries")


class Timer(BaseModel):
    """
    Active timer for time tracking.
    """
    
    __tablename__ = "timers"
    
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    
    description = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_running = Column(Boolean, default=True)
    
    # Relationships
    employee = relationship("Employee", backref="active_timers")
