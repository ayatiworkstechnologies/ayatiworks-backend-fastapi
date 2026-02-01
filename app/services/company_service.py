"""
Company and Branch service.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.company import Branch, Company
from app.models.employee import Employee
from app.schemas.company import BranchCreate, BranchUpdate, CompanyCreate, CompanyUpdate


class CompanyService:
    """Company service class."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, company_id: int) -> Company | None:
        """Get company by ID."""
        return self.db.query(Company).filter(
            Company.id == company_id,
            Company.is_deleted == False
        ).first()

    def get_by_code(self, code: str) -> Company | None:
        """Get company by code."""
        return self.db.query(Company).filter(
            Company.code == code,
            Company.is_deleted == False
        ).first()

    def get_all(
        self,
        search: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[Company], int]:
        """Get all companies with filters."""
        query = self.db.query(Company).filter(Company.is_deleted == False)

        if search:
            query = query.filter(
                Company.name.ilike(f"%{search}%") |
                Company.code.ilike(f"%{search}%")
            )

        if is_active is not None:
            query = query.filter(Company.is_active == is_active)

        total = query.count()

        offset = (page - 1) * page_size
        companies = query.offset(offset).limit(page_size).all()

        return companies, total

    def create(self, data: CompanyCreate, created_by: int = None) -> Company:
        """Create a new company."""
        company = Company(
            **data.model_dump(),
            created_by=created_by
        )

        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)

        return company

    def update(self, company_id: int, data: CompanyUpdate, updated_by: int = None) -> Company | None:
        """Update a company."""
        company = self.get_by_id(company_id)
        if not company:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(company, field, value)

        company.updated_by = updated_by
        company.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(company)

        return company

    def delete(self, company_id: int, deleted_by: int = None) -> bool:
        """Soft delete a company."""
        company = self.get_by_id(company_id)
        if not company:
            return False

        company.soft_delete(deleted_by)
        self.db.commit()

        return True

    def get_branch_count(self, company_id: int) -> int:
        """Get number of branches for a company."""
        return self.db.query(Branch).filter(
            Branch.company_id == company_id,
            Branch.is_deleted == False
        ).count()

    def get_employee_count(self, company_id: int) -> int:
        """Get number of employees for a company."""
        return self.db.query(Employee).filter(
            Employee.company_id == company_id,
            Employee.is_deleted == False
        ).count()


class BranchService:
    """Branch service class."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, branch_id: int) -> Branch | None:
        """Get branch by ID."""
        return self.db.query(Branch).filter(
            Branch.id == branch_id,
            Branch.is_deleted == False
        ).first()

    def get_by_code(self, company_id: int, code: str) -> Branch | None:
        """Get branch by code within a company."""
        return self.db.query(Branch).filter(
            Branch.company_id == company_id,
            Branch.code == code,
            Branch.is_deleted == False
        ).first()

    def get_all(
        self,
        company_id: int | None = None,
        search: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[Branch], int]:
        """Get all branches with filters."""
        query = self.db.query(Branch).filter(Branch.is_deleted == False)

        if company_id:
            query = query.filter(Branch.company_id == company_id)

        if search:
            query = query.filter(
                Branch.name.ilike(f"%{search}%") |
                Branch.code.ilike(f"%{search}%") |
                Branch.city.ilike(f"%{search}%")
            )

        if is_active is not None:
            query = query.filter(Branch.is_active == is_active)

        total = query.count()

        offset = (page - 1) * page_size
        branches = query.offset(offset).limit(page_size).all()

        return branches, total

    def get_by_company(self, company_id: int) -> list[Branch]:
        """Get all branches for a company."""
        return self.db.query(Branch).filter(
            Branch.company_id == company_id,
            Branch.is_deleted == False,
            Branch.is_active == True
        ).all()

    def create(self, data: BranchCreate, created_by: int = None) -> Branch:
        """Create a new branch."""
        branch = Branch(
            **data.model_dump(),
            created_by=created_by
        )

        self.db.add(branch)
        self.db.commit()
        self.db.refresh(branch)

        return branch

    def update(self, branch_id: int, data: BranchUpdate, updated_by: int = None) -> Branch | None:
        """Update a branch."""
        branch = self.get_by_id(branch_id)
        if not branch:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(branch, field, value)

        branch.updated_by = updated_by
        branch.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(branch)

        return branch

    def delete(self, branch_id: int, deleted_by: int = None) -> bool:
        """Soft delete a branch."""
        branch = self.get_by_id(branch_id)
        if not branch:
            return False

        branch.soft_delete(deleted_by)
        self.db.commit()

        return True

    def get_employee_count(self, branch_id: int) -> int:
        """Get number of employees for a branch."""
        return self.db.query(Employee).filter(
            Employee.branch_id == branch_id,
            Employee.is_deleted == False
        ).count()

