"""
Team API routes.
"""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import PermissionChecker
from app.core.exceptions import PermissionDeniedError, ResourceNotFoundError
from app.database import get_db
from app.models.auth import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.team import (
    TeamCreate,
    TeamListResponse,
    TeamMemberCreate,
    TeamMemberResponse,
    TeamResponse,
    TeamUpdate,
)
from app.services.team_service import TeamService

router = APIRouter(tags=["Teams"])


@router.get("", response_model=PaginatedResponse[TeamListResponse])
async def list_teams(
    company_id: int | None = None,
    department_id: int | None = None,
    team_type: str | None = None,
    search: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("team.view")),
    db: Session = Depends(get_db)
):
    """List all teams."""
    service = TeamService(db)

    # Use user's company_id if not provided (typical for multi-tenant)
    # Assuming user model has company_id
    effective_company_id = company_id
    if effective_company_id is None and hasattr(current_user, 'company_id'):
        effective_company_id = current_user.company_id

    if effective_company_id is None:
        # Fallback or error if strictly multi-tenant
        # For now, let's assume it's required or handle in service if allowed
        # But commonly we need a context. Let's return empty if no context.
        return PaginatedResponse.create([], 0, page, page_size)

    teams, total = service.get_all(
        company_id=effective_company_id,
        department_id=department_id,
        team_type=team_type,
        search=search,
        is_active=is_active,
        page=page,
        page_size=page_size
    )

    # Enhance response with member counts and names
    items = []
    for team in teams:
        item = TeamListResponse.model_validate(team)
        item.member_count = service.get_member_count(team.id)
        if team.team_lead:
            item.team_lead_name = f"{team.team_lead.first_name} {team.team_lead.last_name}"
        if team.department:
            item.department_name = team.department.name
        items.append(item)

    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    current_user: User = Depends(PermissionChecker("team.view")),
    db: Session = Depends(get_db)
):
    """Get team by ID."""
    service = TeamService(db)
    team = service.get_by_id(team_id)

    if not team:
        raise ResourceNotFoundError("Team", team_id)

    # Check access (company scope)
    if hasattr(current_user, 'company_id') and team.company_id != current_user.company_id:
        raise PermissionDeniedError("Not authorized to access this team")

    response = TeamResponse.model_validate(team)
    response.member_count = service.get_member_count(team_id)

    if team.team_lead:
        response.team_lead_name = f"{team.team_lead.first_name} {team.team_lead.last_name}"

    if team.department:
        response.department_name = team.department.name

    # Include members list
    members = service.get_members(team_id)
    member_responses = []
    for m in members:
        mr = TeamMemberResponse.model_validate(m)
        if m.employee:
            mr.employee_name = f"{m.employee.first_name} {m.employee.last_name}"
            # Assuming employee has relations to department/designation
            if m.employee.department:
                mr.department_name = m.employee.department.name
            if m.employee.designation:
                mr.designation_name = m.employee.designation.name
            if m.employee.profile_picture:
                mr.avatar = m.employee.profile_picture
        member_responses.append(mr)

    response.members = member_responses

    return response


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    data: TeamCreate,
    current_user: User = Depends(PermissionChecker("team.create")),
    db: Session = Depends(get_db)
):
    """Create a new team."""
    service = TeamService(db)

    # Check if code exists
    if service.get_by_code(data.company_id, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team code already exists"
        )

    team = service.create(data, created_by=current_user.id)
    return TeamResponse.model_validate(team)


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    data: TeamUpdate,
    current_user: User = Depends(PermissionChecker("team.edit")),
    db: Session = Depends(get_db)
):
    """Update a team."""
    service = TeamService(db)

    team = service.update(team_id, data, updated_by=current_user.id)

    if not team:
        raise ResourceNotFoundError("Team", team_id)

    return TeamResponse.model_validate(team)


@router.delete("/{team_id}", response_model=MessageResponse)
async def delete_team(
    team_id: int,
    current_user: User = Depends(PermissionChecker("team.delete")),
    db: Session = Depends(get_db)
):
    """Delete a team."""
    service = TeamService(db)

    if not service.delete(team_id):
        raise ResourceNotFoundError("Team", team_id)

    return MessageResponse(message="Team deleted successfully")


# ==================
# Members Endpoints
# ==================

@router.post("/{team_id}/members", response_model=TeamMemberResponse)
async def add_team_member(
    team_id: int,
    data: TeamMemberCreate,
    current_user: User = Depends(PermissionChecker("team.manage_members")),
    db: Session = Depends(get_db)
):
    """Add a member to a team."""
    service = TeamService(db)

    try:
        member = service.add_member(team_id, data, created_by=current_user.id)

        # Hydrate response
        mr = TeamMemberResponse.model_validate(member)
        if member.employee:
            mr.employee_name = f"{member.employee.first_name} {member.employee.last_name}"
        return mr

    except Exception:
        # Handle duplicate constraint violation usually
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee is already a member of this team or invalid data"
        )


@router.delete("/{team_id}/members/{employee_id}", response_model=MessageResponse)
async def remove_team_member(
    team_id: int,
    employee_id: int,
    current_user: User = Depends(PermissionChecker("team.manage_members")),
    db: Session = Depends(get_db)
):
    """Remove a member from a team."""
    service = TeamService(db)

    if not service.remove_member(team_id, employee_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this team"
        )

    return MessageResponse(message="Member removed successfully")

