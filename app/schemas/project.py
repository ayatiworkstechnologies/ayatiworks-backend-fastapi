"""
Project and Task schemas.
"""

from datetime import date, datetime

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema, TimestampSchema

# ============== Project Schemas ==============

class ProjectBase(BaseSchema):
    """Project base schema."""

    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=50)
    description: str | None = None


class ProjectCreate(ProjectBase):
    """Project create schema."""

    client_id: int | None = None
    manager_id: int | None = None
    company_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: float | None = None
    currency: str = "USD"
    billing_type: str = "fixed"
    hourly_rate: float | None = None
    tags: list[str] | None = None

    @field_validator('client_id', 'manager_id', 'company_id', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class ProjectUpdate(BaseSchema):
    """Project update schema."""

    name: str | None = None
    description: str | None = None
    client_id: int | None = None
    manager_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: float | None = None
    status: str | None = None
    progress: int | None = None
    tags: list[str] | None = None

    @field_validator('client_id', 'manager_id', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class ProjectResponse(ProjectBase, TimestampSchema):
    """Project response schema."""

    id: int
    client_id: int | None = None
    manager_id: int | None = None
    company_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: float | None = None
    currency: str
    status: str
    progress: int
    billing_type: str
    tags: list[str] | None = None

    # Display
    client_name: str | None = None
    manager_name: str | None = None
    task_count: int = 0


class ProjectListResponse(BaseSchema):
    """Project list item."""

    id: int
    name: str
    code: str
    client_name: str | None = None
    status: str
    progress: int
    start_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None


class ProjectMemberCreate(BaseSchema):
    """Project member create schema."""

    employee_id: int
    role: str = "member"
    hourly_rate: float | None = None


class ProjectMemberResponse(BaseSchema):
    """Project member response schema."""

    id: int
    project_id: int
    employee_id: int
    role: str
    hourly_rate: float | None = None
    joined_at: date

    # Display
    employee_name: str | None = None
    employee_email: str | None = None
    employee_avatar: str | None = None


# ============== Milestone Schemas ==============

class MilestoneCreate(BaseSchema):
    """Milestone create schema."""

    project_id: int
    name: str
    description: str | None = None
    due_date: date | None = None
    amount: float | None = None
    status: str = "pending"


class MilestoneUpdate(BaseSchema):
    """Milestone update schema."""

    name: str | None = None
    description: str | None = None
    due_date: date | None = None
    amount: float | None = None
    status: str | None = None
    is_paid: bool | None = None


class MilestoneResponse(TimestampSchema):
    """Milestone response schema."""

    id: int
    project_id: int
    name: str
    description: str | None = None
    due_date: date | None = None
    completed_date: date | None = None
    status: str
    amount: float | None = None
    is_paid: bool


# ============== Task Schemas ==============

class TaskBase(BaseSchema):
    """Task base schema."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class TaskCreate(TaskBase):
    """Task create schema."""

    project_id: int | None = None
    parent_id: int | None = None
    assignee_id: int | None = None
    priority: str = "medium"
    due_date: date | None = None
    start_date: date | None = None
    estimated_hours: float | None = None
    sprint_id: int | None = None
    milestone_id: int | None = None
    tags: list[str] | None = None


class TaskUpdate(BaseSchema):
    """Task update schema."""

    title: str | None = None
    description: str | None = None
    assignee_id: int | None = None
    status: str | None = None
    priority: str | None = None
    due_date: date | None = None
    start_date: date | None = None
    estimated_hours: float | None = None
    sprint_id: int | None = None
    tags: list[str] | None = None


class TaskResponse(TaskBase, TimestampSchema):
    """Task response schema."""

    id: int
    project_id: int | None = None
    parent_id: int | None = None
    assignee_id: int | None = None
    reporter_id: int | None = None
    status: str
    priority: str
    due_date: date | None = None
    start_date: date | None = None
    completed_at: datetime | None = None
    estimated_hours: float | None = None
    logged_hours: float
    sprint_id: int | None = None
    milestone_id: int | None = None
    tags: list[str] | None = None

    # Display
    project_name: str | None = None
    assignee_name: str | None = None
    subtask_count: int = 0


class TaskListResponse(BaseSchema):
    """Task list item."""

    id: int
    title: str
    project_name: str | None = None
    assignee_name: str | None = None
    status: str
    priority: str
    due_date: date | None = None


# ============== Time Entry Schemas ==============

class TimeEntryCreate(BaseSchema):
    """Time entry create schema."""

    project_id: int | None = None
    task_id: int | None = None
    date: date
    hours: float
    description: str | None = None
    is_billable: bool = True


class TimeEntryResponse(TimestampSchema):
    """Time entry response schema."""

    id: int
    employee_id: int
    project_id: int | None = None
    task_id: int | None = None
    date: date
    hours: float
    description: str | None = None
    is_billable: bool
    hourly_rate: float | None = None
    is_approved: bool

    # Display
    project_name: str | None = None
    task_title: str | None = None

