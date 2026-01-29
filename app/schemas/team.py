"""
Team schemas.
"""

from typing import Optional, List
from datetime import date
from pydantic import BaseModel, ConfigDict

from app.schemas.common import AuditSchema


# =======================
# Team Member Schemas
# =======================

class TeamMemberBase(BaseModel):
    employee_id: int
    role: Optional[str] = None
    is_active: bool = True

class TeamMemberCreate(TeamMemberBase):
    joined_date: Optional[date] = None

class TeamMemberUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    joined_date: Optional[date] = None

class TeamMemberResponse(TeamMemberBase, AuditSchema):
    id: int
    team_id: int
    joined_date: date
    employee_name: Optional[str] = None
    department_name: Optional[str] = None
    designation_name: Optional[str] = None
    avatar: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# =======================
# Team Schemas
# =======================

class TeamBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    team_type: Optional[str] = None
    department_id: Optional[int] = None
    team_lead_id: Optional[int] = None
    max_members: Optional[int] = None
    is_active: bool = True

class TeamCreate(TeamBase):
    company_id: int

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    team_type: Optional[str] = None
    department_id: Optional[int] = None
    team_lead_id: Optional[int] = None
    max_members: Optional[int] = None
    is_active: Optional[bool] = None

class TeamResponse(TeamBase, AuditSchema):
    id: int
    company_id: int
    member_count: Optional[int] = 0
    team_lead_name: Optional[str] = None
    department_name: Optional[str] = None
    
    # We might want to include members summary or list in detailed view
    members: Optional[List[TeamMemberResponse]] = None

    model_config = ConfigDict(from_attributes=True)

class TeamListResponse(BaseModel):
    id: int
    name: str
    code: str
    team_type: Optional[str] = None
    member_count: int = 0
    team_lead_name: Optional[str] = None
    department_name: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
