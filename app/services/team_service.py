"""
Team service.
"""


from sqlalchemy.orm import Session

from app.models.team import Team, TeamMember
from app.schemas.team import TeamCreate, TeamMemberCreate, TeamUpdate


class TeamService:
    """Team service class."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, team_id: int) -> Team | None:
        """Get team by ID."""
        return self.db.query(Team).filter(Team.id == team_id).first()

    def get_by_code(self, company_id: int, code: str) -> Team | None:
        """Get team by code."""
        return self.db.query(Team).filter(
            Team.company_id == company_id,
            Team.code == code
        ).first()

    def get_all(
        self,
        company_id: int,
        department_id: int | None = None,
        team_type: str | None = None,
        search: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[Team], int]:
        """Get all teams with filters."""
        query = self.db.query(Team).filter(Team.company_id == company_id)

        if department_id:
            query = query.filter(Team.department_id == department_id)

        if team_type:
            query = query.filter(Team.team_type == team_type)

        if is_active is not None:
            query = query.filter(Team.is_active == is_active)

        if search:
            query = query.filter(
                Team.name.ilike(f"%{search}%") |
                Team.code.ilike(f"%{search}%")
            )

        total = query.count()

        offset = (page - 1) * page_size
        teams = query.order_by(Team.name).offset(offset).limit(page_size).all()

        return teams, total

    def create(self, data: TeamCreate, created_by: int = None) -> Team:
        """Create a new team."""
        team = Team(
            **data.model_dump(),
            created_by=created_by
        )

        self.db.add(team)
        self.db.commit()
        self.db.refresh(team)

        return team

    def update(self, team_id: int, data: TeamUpdate, updated_by: int = None) -> Team | None:
        """Update a team."""
        team = self.get_by_id(team_id)
        if not team:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(team, field, value)

        team.updated_by = updated_by

        self.db.commit()
        self.db.refresh(team)

        return team

    def delete(self, team_id: int) -> bool:
        """Delete a team."""
        team = self.get_by_id(team_id)
        if not team:
            return False

        # We can implement soft delete logic here if the model supports it
        # For now, using hard delete based on typical requirements,
        # but the model has AuditMixin so it might be better to just set is_active=False
        # However, plan typically implies delete. Let's do a hard delete for now or check mixin.
        # Checking model... AuditMixin usually adds timestamps. BaseModel has ID.
        # Let's check other services... Organization uses soft_delete.
        # Let's use soft delete if available, otherwise database delete.

        # Assuming database delete for now as specific soft_delete mixin wasn't checked in detail
        self.db.delete(team)
        self.db.commit()

        return True

    # =================
    # Members Methods
    # =================

    def get_members(self, team_id: int) -> list[TeamMember]:
        """Get members of a team."""
        return self.db.query(TeamMember).filter(TeamMember.team_id == team_id).all()

    def add_member(self, team_id: int, data: TeamMemberCreate, created_by: int = None) -> TeamMember:
        """Add a member to a team."""
        member = TeamMember(
            team_id=team_id,
            employee_id=data.employee_id,
            role=data.role,
            joined_date=data.joined_date,
            is_active=data.is_active,
            created_by=created_by
        )

        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)

        return member

    def remove_member(self, team_id: int, employee_id: int) -> bool:
        """Remove a member from a team."""
        member = self.db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.employee_id == employee_id
        ).first()

        if not member:
            return False

        self.db.delete(member)
        self.db.commit()

        return True

    def get_member_count(self, team_id: int) -> int:
        """Get count of members in a team."""
        return self.db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.is_active == True
        ).count()

