"""
Team schemas.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.schemas.common import AuditSchema

# =======================
# Team Member Schemas
# =======================

class TeamMemberBase(BaseModel):
    employee_id: int
    role: str | None = None
    is_active: bool = True

class TeamMemberCreate(TeamMemberBase):
    joined_date: date | None = None

class TeamMemberUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    joined_date: date | None = None

class TeamMemberResponse(TeamMemberBase, AuditSchema):
    id: int
    team_id: int
    joined_date: date
    employee_name: str | None = None
    department_name: str | None = None
    designation_name: str | None = None
    avatar: str | None = None

    model_config = ConfigDict(from_attributes=True)


# =======================
# Team Schemas
# =======================

class TeamBase(BaseModel):
    name: str
    code: str
    description: str | None = None
    team_type: str | None = None
    department_id: int | None = None
    team_lead_id: int | None = None
    max_members: int | None = None
    is_active: bool = True

class TeamCreate(TeamBase):
    company_id: int

class TeamUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None
    team_type: str | None = None
    department_id: int | None = None
    team_lead_id: int | None = None
    max_members: int | None = None
    is_active: bool | None = None

class TeamResponse(TeamBase, AuditSchema):
    id: int
    company_id: int
    member_count: int | None = 0
    team_lead_name: str | None = None
    department_name: str | None = None

    # We might want to include members summary or list in detailed view
    members: list[TeamMemberResponse] | None = None

    model_config = ConfigDict(from_attributes=True)

class TeamListResponse(BaseModel):
    id: int
    name: str
    code: str
    team_type: str | None = None
    member_count: int = 0
    team_lead_name: str | None = None
    department_name: str | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

