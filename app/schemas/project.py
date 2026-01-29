"""
Project and Task schemas.
"""

from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator

from app.schemas.common import BaseSchema, TimestampSchema


# ============== Project Schemas ==============

class ProjectBase(BaseSchema):
    """Project base schema."""
    
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Project create schema."""
    
    client_id: Optional[int] = None
    manager_id: Optional[int] = None
    company_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None
    currency: str = "USD"
    billing_type: str = "fixed"
    hourly_rate: Optional[float] = None
    tags: Optional[List[str]] = None
    
    @field_validator('client_id', 'manager_id', 'company_id', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class ProjectUpdate(BaseSchema):
    """Project update schema."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    client_id: Optional[int] = None
    manager_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None
    status: Optional[str] = None
    progress: Optional[int] = None
    tags: Optional[List[str]] = None
    
    @field_validator('client_id', 'manager_id', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class ProjectResponse(ProjectBase, TimestampSchema):
    """Project response schema."""
    
    id: int
    client_id: Optional[int] = None
    manager_id: Optional[int] = None
    company_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None
    currency: str
    status: str
    progress: int
    billing_type: str
    tags: Optional[List[str]] = None
    
    # Display
    client_name: Optional[str] = None
    manager_name: Optional[str] = None
    task_count: int = 0


class ProjectListResponse(BaseSchema):
    """Project list item."""
    
    id: int
    name: str
    code: str
    client_name: Optional[str] = None
    status: str
    progress: int
    start_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ProjectMemberCreate(BaseSchema):
    """Project member create schema."""
    
    employee_id: int
    role: str = "member"
    hourly_rate: Optional[float] = None


class ProjectMemberResponse(BaseSchema):
    """Project member response schema."""
    
    id: int
    project_id: int
    employee_id: int
    role: str
    hourly_rate: Optional[float] = None
    joined_at: date
    
    # Display
    employee_name: Optional[str] = None
    employee_email: Optional[str] = None
    employee_avatar: Optional[str] = None


# ============== Milestone Schemas ==============

class MilestoneCreate(BaseSchema):
    """Milestone create schema."""
    
    project_id: int
    name: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    amount: Optional[float] = None
    status: str = "pending"


class MilestoneUpdate(BaseSchema):
    """Milestone update schema."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    amount: Optional[float] = None
    status: Optional[str] = None
    is_paid: Optional[bool] = None


class MilestoneResponse(TimestampSchema):
    """Milestone response schema."""
    
    id: int
    project_id: int
    name: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    completed_date: Optional[date] = None
    status: str
    amount: Optional[float] = None
    is_paid: bool


# ============== Task Schemas ==============

class TaskBase(BaseSchema):
    """Task base schema."""
    
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class TaskCreate(TaskBase):
    """Task create schema."""
    
    project_id: Optional[int] = None
    parent_id: Optional[int] = None
    assignee_id: Optional[int] = None
    priority: str = "medium"
    due_date: Optional[date] = None
    start_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    sprint_id: Optional[int] = None
    milestone_id: Optional[int] = None
    tags: Optional[List[str]] = None


class TaskUpdate(BaseSchema):
    """Task update schema."""
    
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None
    start_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    sprint_id: Optional[int] = None
    tags: Optional[List[str]] = None


class TaskResponse(TaskBase, TimestampSchema):
    """Task response schema."""
    
    id: int
    project_id: Optional[int] = None
    parent_id: Optional[int] = None
    assignee_id: Optional[int] = None
    reporter_id: Optional[int] = None
    status: str
    priority: str
    due_date: Optional[date] = None
    start_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    logged_hours: float
    sprint_id: Optional[int] = None
    milestone_id: Optional[int] = None
    tags: Optional[List[str]] = None
    
    # Display
    project_name: Optional[str] = None
    assignee_name: Optional[str] = None
    subtask_count: int = 0


class TaskListResponse(BaseSchema):
    """Task list item."""
    
    id: int
    title: str
    project_name: Optional[str] = None
    assignee_name: Optional[str] = None
    status: str
    priority: str
    due_date: Optional[date] = None


# ============== Time Entry Schemas ==============

class TimeEntryCreate(BaseSchema):
    """Time entry create schema."""
    
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    date: date
    hours: float
    description: Optional[str] = None
    is_billable: bool = True


class TimeEntryResponse(TimestampSchema):
    """Time entry response schema."""
    
    id: int
    employee_id: int
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    date: date
    hours: float
    description: Optional[str] = None
    is_billable: bool
    hourly_rate: Optional[float] = None
    is_approved: bool
    
    # Display
    project_name: Optional[str] = None
    task_title: Optional[str] = None
