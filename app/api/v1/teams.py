"""
Team API routes.
"""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError as SQLAlchemyIntegrityError
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
from app.services.email_service import email_service
from app.services.team_service import TeamService

router = APIRouter(tags=["Teams"])


def _user_display_name(user: User | None) -> str | None:
    """Return a user's display name without leaking a literal None last name."""
    if not user:
        return None
    return user.full_name


def _employee_display_name(employee) -> str:
    """Return an employee's display name from the linked user profile."""
    if not employee:
        return ""
    if employee.user:
        return employee.user.full_name
    return employee.employee_code


def _employee_avatar(employee) -> str | None:
    """Return an employee avatar from the linked user profile."""
    if employee and employee.user:
        return employee.user.avatar
    return None


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
            item.team_lead_name = _user_display_name(team.team_lead)
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
    if getattr(current_user, "company_id", None) and team.company_id != current_user.company_id:
        raise PermissionDeniedError("Not authorized to access this team")

    response = TeamResponse.model_validate(team)
    response.member_count = service.get_member_count(team_id)

    if team.team_lead:
        response.team_lead_name = _user_display_name(team.team_lead)

    if team.department:
        response.department_name = team.department.name

    # Include members list
    members = service.get_members(team_id)
    member_responses = []
    for m in members:
        mr = TeamMemberResponse.model_validate(m)
        if m.employee:
            mr.employee_name = _employee_display_name(m.employee)
            # Assuming employee has relations to department/designation
            if m.employee.department:
                mr.department_name = m.employee.department.name
            if m.employee.designation:
                mr.designation_name = m.employee.designation.name
            mr.avatar = _employee_avatar(m.employee)
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

    try:
        team = service.create(data, created_by=current_user.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc
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

    try:
        team = service.update(team_id, data, updated_by=current_user.id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc

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

    if not service.delete(team_id, deleted_by=current_user.id):
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

        # Send notification to new member
        try:
            # Re-fetch or ensure relationships are loaded to get email
            # member.employee might be loaded, but let's be safe
            if member.employee and member.employee.user:
                team = service.get_by_id(team_id)
                team_lead_name = "N/A"
                if team.team_lead:
                    team_lead_name = _user_display_name(team.team_lead) or "N/A"

                email_service.send_team_addition_email(
                    to_email=member.employee.user.email,
                    employee_name=_employee_display_name(member.employee),
                    team_name=team.name,
                    department_name=team.department.name if team.department else "N/A",
                    team_lead_name=team_lead_name,
                    role=data.role,
                    team_id=team_id
                )
        except Exception as e:
            import logging
            logging.error(f"Failed to send team addition email: {e}")

        # Hydrate response
        mr = TeamMemberResponse.model_validate(member)
        if member.employee:
            mr.employee_name = _employee_display_name(member.employee)
            if member.employee.department:
                mr.department_name = member.employee.department.name
            if member.employee.designation:
                mr.designation_name = member.employee.designation.name
            mr.avatar = _employee_avatar(member.employee)
        return mr

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        ) from exc
    except SQLAlchemyIntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee is already a member of this team"
        ) from exc


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

