"""
Team service.
"""

from datetime import date

from sqlalchemy.orm import Session, joinedload

from app.models.auth import User
from app.models.employee import Employee
from app.models.organization import Department
from app.models.team import Team, TeamMember
from app.schemas.team import TeamCreate, TeamMemberCreate, TeamUpdate


class TeamService:
    """Team service class."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, team_id: int) -> Team | None:
        """Get team by ID."""
        return self.db.query(Team).options(
            joinedload(Team.department),
            joinedload(Team.team_lead),
        ).filter(
            Team.id == team_id,
            Team.is_deleted.is_(False)
        ).first()

    def get_by_code(self, company_id: int, code: str) -> Team | None:
        """Get team by code."""
        return self.db.query(Team).filter(
            Team.company_id == company_id,
            Team.code == code,
            Team.is_deleted.is_(False)
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
        query = self.db.query(Team).filter(
            Team.company_id == company_id,
            Team.is_deleted.is_(False)
        )

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
        self.validate_team_data(
            company_id=data.company_id,
            code=data.code,
            department_id=data.department_id,
            team_lead_id=data.team_lead_id,
        )
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
        self.validate_team_data(
            company_id=team.company_id,
            code=update_data.get("code", team.code),
            department_id=update_data.get("department_id", team.department_id),
            team_lead_id=update_data.get("team_lead_id", team.team_lead_id),
            exclude_team_id=team_id,
        )
        for field, value in update_data.items():
            setattr(team, field, value)

        team.updated_by = updated_by

        self.db.commit()
        self.db.refresh(team)

        return team

    def validate_team_data(
        self,
        *,
        company_id: int,
        code: str,
        department_id: int | None = None,
        team_lead_id: int | None = None,
        exclude_team_id: int | None = None,
    ) -> None:
        """Validate team code and foreign key references before saving."""
        code_query = self.db.query(Team).filter(
            Team.company_id == company_id,
            Team.code == code,
            Team.is_deleted.is_(False),
        )
        if exclude_team_id:
            code_query = code_query.filter(Team.id != exclude_team_id)
        if code_query.first():
            raise ValueError("Team code already exists")

        if department_id:
            department = self.db.query(Department).filter(
                Department.id == department_id,
                Department.company_id == company_id,
                Department.is_deleted.is_(False),
            ).first()
            if not department:
                raise ValueError("Selected department does not exist for this company")

        if team_lead_id:
            user = self.db.query(User).filter(
                User.id == team_lead_id,
                User.is_deleted.is_(False),
                User.is_active.is_(True),
            ).first()
            if not user:
                raise ValueError("Selected team lead does not exist or is inactive")

    def delete(self, team_id: int, deleted_by: int = None) -> bool:
        """Soft delete a team."""
        team = self.get_by_id(team_id)
        if not team:
            return False

        team.soft_delete(deleted_by)
        self.db.commit()

        return True

    # =================
    # Members Methods
    # =================

    def get_members(self, team_id: int) -> list[TeamMember]:
        """Get members of a team."""
        return self.db.query(TeamMember).options(
            joinedload(TeamMember.employee).joinedload(Employee.user),
            joinedload(TeamMember.employee).joinedload(Employee.department),
            joinedload(TeamMember.employee).joinedload(Employee.designation),
        ).filter(
            TeamMember.team_id == team_id,
            TeamMember.is_deleted.is_(False)
        ).all()

    def get_member(self, team_id: int, employee_id: int) -> TeamMember | None:
        """Get an active team membership."""
        return self.db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.employee_id == employee_id,
            TeamMember.is_deleted.is_(False),
        ).first()

    def get_deleted_member(self, team_id: int, employee_id: int) -> TeamMember | None:
        """Get a soft-deleted team membership that can be restored."""
        return self.db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.employee_id == employee_id,
            TeamMember.is_deleted.is_(True),
        ).first()

    def add_member(self, team_id: int, data: TeamMemberCreate, created_by: int = None) -> TeamMember:
        """Add a member to a team."""
        team = self.get_by_id(team_id)
        if not team:
            raise ValueError("Team not found")

        employee = self.db.query(Employee).filter(
            Employee.id == data.employee_id,
            Employee.is_deleted.is_(False),
            Employee.is_active.is_(True),
        ).first()
        if not employee:
            raise ValueError("Employee not found or inactive")

        existing = self.get_member(team_id, data.employee_id)
        if existing:
            raise ValueError("Employee is already a member of this team")

        deleted_member = self.get_deleted_member(team_id, data.employee_id)
        if deleted_member:
            deleted_member.role = data.role
            deleted_member.joined_date = data.joined_date or date.today()
            deleted_member.is_active = data.is_active
            deleted_member.is_deleted = False
            deleted_member.deleted_at = None
            deleted_member.deleted_by = None
            deleted_member.updated_by = created_by
            self.db.commit()
            self.db.refresh(deleted_member)
            return deleted_member

        member = TeamMember(
            team_id=team_id,
            employee_id=data.employee_id,
            role=data.role,
            joined_date=data.joined_date or date.today(),
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
            TeamMember.employee_id == employee_id,
            TeamMember.is_deleted.is_(False)
        ).first()

        if not member:
            return False

        member.soft_delete()
        self.db.commit()

        return True

    def get_member_count(self, team_id: int) -> int:
        """Get count of members in a team."""
        return self.db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.is_active.is_(True),
            TeamMember.is_deleted.is_(False)
        ).count()

