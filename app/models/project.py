"""
Project and Task models.
Project management with milestones, tasks, and team members.
"""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, JSON, Date, Float, DateTime
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel, AuditMixin


class ProjectStatus(enum.Enum):
    """Project status enum."""
    DRAFT = "draft"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskStatus(enum.Enum):
    """Task status enum."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(enum.Enum):
    """Task priority enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Project(BaseModel, AuditMixin):
    """
    Project model.
    """
    
    __tablename__ = "projects"
    
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Client
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    
    # Team
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    
    # Timeline
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    
    # Budget
    budget = Column(Float, nullable=True)
    currency = Column(String(3), default="USD")
    
    # Status
    status = Column(String(20), default=ProjectStatus.DRAFT.value)
    progress = Column(Integer, default=0)  # 0-100 percentage
    
    # Settings
    billing_type = Column(String(20), default="fixed")  # fixed, hourly, milestone
    hourly_rate = Column(Float, nullable=True)
    
    # Tags and metadata
    tags = Column(JSON, nullable=True)
    settings = Column(JSON, nullable=True)
    
    # Relationships
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")


class Milestone(BaseModel, AuditMixin):
    """
    Project milestone.
    """
    
    __tablename__ = "milestones"
    
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    due_date = Column(Date, nullable=True)
    completed_date = Column(Date, nullable=True)
    
    status = Column(String(20), default="pending")  # pending, in_progress, completed
    
    # Payment milestone
    amount = Column(Float, nullable=True)
    is_paid = Column(Boolean, default=False)
    
    order = Column(Integer, default=0)
    
    # Relationships
    project = relationship("Project", back_populates="milestones")


class ProjectMember(BaseModel):
    """
    Project team member.
    """
    
    __tablename__ = "project_members"
    
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    
    role = Column(String(50), default="member")  # manager, lead, member, viewer
    hourly_rate = Column(Float, nullable=True)  # Override rate for this project
    
    joined_at = Column(Date, default=date.today)
    left_at = Column(Date, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="members")
    employee = relationship("Employee", backref="project_memberships")


class Task(BaseModel, AuditMixin):
    """
    Task model.
    """
    
    __tablename__ = "tasks"
    
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    parent_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)  # For subtasks
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Assignment
    assignee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    reporter_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    
    # Status
    status = Column(String(20), default=TaskStatus.TODO.value)
    priority = Column(String(20), default=TaskPriority.MEDIUM.value)
    
    # Timeline
    due_date = Column(Date, nullable=True)
    start_date = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Time tracking
    estimated_hours = Column(Float, nullable=True)
    logged_hours = Column(Float, default=0)
    
    # Sprint
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=True)
    
    # Milestone
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=True)
    
    # Tags and labels
    tags = Column(JSON, nullable=True)
    labels = Column(JSON, nullable=True)
    
    order = Column(Integer, default=0)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    parent = relationship("Task", remote_side="Task.id", backref="subtasks")
    assignee = relationship("Employee", foreign_keys=[assignee_id], backref="assigned_tasks")
    reporter = relationship("Employee", foreign_keys=[reporter_id], backref="reported_tasks")
    comments = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")
    attachments = relationship("TaskAttachment", back_populates="task", cascade="all, delete-orphan")


class TaskComment(BaseModel, AuditMixin):
    """
    Task comment.
    """
    
    __tablename__ = "task_comments"
    
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    content = Column(Text, nullable=False)
    
    # For replies
    parent_id = Column(Integer, ForeignKey("task_comments.id"), nullable=True)
    
    # Relationships
    task = relationship("Task", back_populates="comments")


class TaskAttachment(BaseModel):
    """
    Task file attachment.
    """
    
    __tablename__ = "task_attachments"
    
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    
    # Relationships
    task = relationship("Task", back_populates="attachments")
