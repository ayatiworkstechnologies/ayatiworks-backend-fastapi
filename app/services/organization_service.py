"""
Department and Designation service.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.organization import Department, Designation
from app.schemas.organization import (
    DepartmentCreate,
    DepartmentUpdate,
    DesignationCreate,
    DesignationUpdate,
)


class DepartmentService:
    """Department service class."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, department_id: int) -> Department | None:
        """Get department by ID."""
        return self.db.query(Department).filter(
            Department.id == department_id,
            Department.is_deleted == False
        ).first()

    def get_by_code(self, company_id: int, code: str) -> Department | None:
        """Get department by code within a company."""
        return self.db.query(Department).filter(
            Department.company_id == company_id,
            Department.code == code,
            Department.is_deleted == False
        ).first()

    def get_all(
        self,
        company_id: int | None = None,
        parent_id: int | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[Department], int]:
        """Get all departments with filters."""
        query = self.db.query(Department).filter(Department.is_deleted == False)

        if company_id:
            query = query.filter(Department.company_id == company_id)

        if parent_id is not None:
            query = query.filter(Department.parent_id == parent_id)

        if search:
            query = query.filter(
                Department.name.ilike(f"%{search}%") |
                Department.code.ilike(f"%{search}%")
            )

        total = query.count()

        offset = (page - 1) * page_size
        departments = query.order_by(Department.level, Department.name).offset(offset).limit(page_size).all()

        return departments, total

    def get_tree(self, company_id: int) -> list[Department]:
        """Get department tree (root departments with children)."""
        return self.db.query(Department).filter(
            Department.company_id == company_id,
            Department.parent_id is None,
            Department.is_deleted == False
        ).all()

    def create(self, data: DepartmentCreate, created_by: int = None) -> Department:
        """Create a new department."""
        # Calculate level based on parent
        level = 0
        path = ""
        if data.parent_id:
            parent = self.get_by_id(data.parent_id)
            if parent:
                level = parent.level + 1
                path = f"{parent.path}/{parent.id}" if parent.path else str(parent.id)

        department = Department(
            company_id=data.company_id,
            name=data.name,
            code=data.code,
            description=data.description,
            parent_id=data.parent_id,
            manager_id=data.manager_id,
            level=level,
            path=path,
            created_by=created_by
        )

        self.db.add(department)
        self.db.commit()
        self.db.refresh(department)

        return department

    def update(self, department_id: int, data: DepartmentUpdate, updated_by: int = None) -> Department | None:
        """Update a department."""
        department = self.get_by_id(department_id)
        if not department:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Recalculate level if parent changed
        if 'parent_id' in update_data:
            new_parent_id = update_data['parent_id']
            if new_parent_id:
                parent = self.get_by_id(new_parent_id)
                if parent:
                    department.level = parent.level + 1
                    department.path = f"{parent.path}/{parent.id}" if parent.path else str(parent.id)
            else:
                department.level = 0
                department.path = ""

        for field, value in update_data.items():
            setattr(department, field, value)

        department.updated_by = updated_by
        department.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(department)

        return department

    def delete(self, department_id: int, deleted_by: int = None) -> bool:
        """Soft delete a department."""
        department = self.get_by_id(department_id)
        if not department:
            return False

        department.soft_delete(deleted_by)
        self.db.commit()

        return True

    def get_employee_count(self, department_id: int) -> int:
        """Get number of employees in a department."""
        return self.db.query(Employee).filter(
            Employee.department_id == department_id,
            Employee.is_deleted == False
        ).count()


class DesignationService:
    """Designation service class."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, designation_id: int) -> Designation | None:
        """Get designation by ID."""
        return self.db.query(Designation).filter(
            Designation.id == designation_id,
            Designation.is_deleted == False
        ).first()

    def get_by_code(self, code: str) -> Designation | None:
        """Get designation by code."""
        return self.db.query(Designation).filter(
            Designation.code == code,
            Designation.is_deleted == False
        ).first()

    def get_all(
        self,
        department_id: int | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[Designation], int]:
        """Get all designations with filters."""
        query = self.db.query(Designation).filter(Designation.is_deleted == False)

        if department_id:
            query = query.filter(Designation.department_id == department_id)

        if search:
            query = query.filter(
                Designation.name.ilike(f"%{search}%") |
                Designation.code.ilike(f"%{search}%")
            )

        total = query.count()

        offset = (page - 1) * page_size
        designations = query.order_by(Designation.level.desc(), Designation.name).offset(offset).limit(page_size).all()

        return designations, total

    def create(self, data: DesignationCreate, created_by: int = None) -> Designation:
        """Create a new designation."""
        designation = Designation(
            **data.model_dump(),
            created_by=created_by
        )

        self.db.add(designation)
        self.db.commit()
        self.db.refresh(designation)

        return designation

    def update(self, designation_id: int, data: DesignationUpdate, updated_by: int = None) -> Designation | None:
        """Update a designation."""
        designation = self.get_by_id(designation_id)
        if not designation:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(designation, field, value)

        designation.updated_by = updated_by
        designation.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(designation)

        return designation

    def delete(self, designation_id: int, deleted_by: int = None) -> bool:
        """Soft delete a designation."""
        designation = self.get_by_id(designation_id)
        if not designation:
            return False

        designation.soft_delete(deleted_by)
        self.db.commit()

        return True

    def get_employee_count(self, designation_id: int) -> int:
        """Get number of employees with a designation."""
        return self.db.query(Employee).filter(
            Employee.designation_id == designation_id,
            Employee.is_deleted == False
        ).count()

