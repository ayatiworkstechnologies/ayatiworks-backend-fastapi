"""
Employee service.
Handles employee CRUD and employee code generation.
"""

import re
from datetime import date, datetime

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError as SQLAlchemyIntegrityError
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.core.security import generate_random_password, hash_password
from app.models.auth import Role, User
from app.models.employee import Employee, EmployeeDocument
from app.models.organization import Department, Designation
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


class EmployeeService:
    """Employee service class."""

    def __init__(self, db: Session):
        self.db = db

    def generate_employee_code(self, prefix: str = None, skip: int = 0) -> str:
        """
        Generate next employee code in format AW0001, AW0002, etc.
        For clients, pass prefix='AWC' to generate AWC001, AWC002, etc.
        `skip` bumps the number past `skip` additional collisions seen in the
        same request (used by retry loops so repeated calls don't return the
        same code while the prior attempt's row hasn't been committed yet).
        """
        if prefix is None:
            prefix = settings.EMPLOYEE_ID_PREFIX
        length = settings.EMPLOYEE_ID_LENGTH

        # Get all matching codes, then keep only exact prefix+digits matches.
        codes = self.db.query(Employee.employee_code).filter(
            Employee.employee_code.like(f"{prefix}%")
        ).all()

        pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
        max_num = 0
        for (code,) in codes:
            match = pattern.match(code or "")
            if not match:
                continue
            max_num = max(max_num, int(match.group(1)))

        num = max_num + 1 + skip

        # Format with leading zeros
        return f"{prefix}{num:0{length}d}"

    def get_by_id(self, employee_id: int) -> Employee | None:
        """Get employee by ID."""
        return self.db.query(Employee).filter(
            Employee.id == employee_id,
            Employee.is_deleted.is_(False)
        ).first()

    def get_by_user_id(self, user_id: int) -> Employee | None:
        """Get employee by user ID."""
        return self.db.query(Employee).filter(
            Employee.user_id == user_id,
            Employee.is_deleted.is_(False)
        ).first()

    def get_by_code(self, code: str) -> Employee | None:
        """Get employee by employee code."""
        return self.db.query(Employee).filter(
            Employee.employee_code == code,
            Employee.is_deleted.is_(False)
        ).first()

    def get_by_code_flexible(self, code: str) -> Employee | None:
        """Get employee by code, accepting short forms like AW001 for AW0001."""
        for candidate in self.normalize_employee_code_candidates(code):
            if self.is_client_employee_code(candidate):
                continue
            employee = self.get_by_code(candidate)
            if employee:
                return employee
        return None

    def normalize_employee_code_candidates(self, code: str) -> list[str]:
        """Return possible stored employee codes for a user-entered code."""
        normalized = (code or "").strip().upper()
        if not normalized:
            return []

        candidates = [normalized]
        match = re.match(r"^([A-Z]+)(\d+)$", normalized)
        if match:
            prefix, number = match.groups()
            padded = f"{prefix}{int(number):0{settings.EMPLOYEE_ID_LENGTH}d}"
            if padded not in candidates:
                candidates.append(padded)

        return candidates

    def is_client_employee_code(self, code: str | None) -> bool:
        """Return True for client portal codes such as AWC0001."""
        client_prefix = f"{settings.EMPLOYEE_ID_PREFIX}C"
        return bool(code and code.upper().startswith(client_prefix.upper()))

    def staff_employee_code_filters(self) -> tuple:
        """Filters that keep employee endpoints from returning client codes."""
        client_prefix = f"{settings.EMPLOYEE_ID_PREFIX}C"
        return (
            Employee.employee_code.ilike(f"{settings.EMPLOYEE_ID_PREFIX}%"),
            ~Employee.employee_code.ilike(f"{client_prefix}%"),
        )

    def get_stats(self) -> dict[str, int]:
        """Get employee counts, excluding client-role employee records."""
        query = self.db.query(Employee).join(User, Employee.user_id == User.id).outerjoin(
            Role,
            User.role_id == Role.id,
        ).filter(
            Employee.is_deleted.is_(False),
            or_(Role.code.is_(None), Role.code != "CLIENT"),
            *self.staff_employee_code_filters(),
        )

        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)

        total = query.count()
        active = query.filter(Employee.employment_status == "active").count()
        inactive = query.filter(Employee.employment_status == "inactive").count()
        probation = query.filter(Employee.employment_status == "probation").count()
        terminated = query.filter(Employee.employment_status == "terminated").count()
        new_this_month = query.filter(Employee.created_at >= month_start).count()

        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "probation": probation,
            "terminated": terminated,
            "new_this_month": new_this_month,
        }

    def validate_department_designation(
        self,
        department_id: int | None,
        designation_id: int | None,
    ) -> None:
        """Validate that a designation belongs to the selected department."""
        if department_id:
            department = self.db.query(Department).filter(
                Department.id == department_id,
                Department.is_deleted.is_(False),
            ).first()
            if not department:
                raise ValueError("Selected department does not exist.")

        if designation_id:
            designation = self.db.query(Designation).filter(
                Designation.id == designation_id,
                Designation.is_deleted.is_(False),
            ).first()
            if not designation:
                raise ValueError("Selected designation does not exist.")

            if not department_id:
                raise ValueError("Select a department before selecting a designation.")

            if designation.department_id != department_id:
                raise ValueError("Selected designation does not belong to the selected department.")

    def get_all(
        self,
        company_id: int | None = None,
        branch_id: int | None = None,
        department_id: int | None = None,
        designation_id: int | None = None,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[Employee], int]:
        """
        Get all employees with filters and pagination.

        Returns:
            Tuple of (employees list, total count)
        """
        query = self.db.query(Employee).options(
            joinedload(Employee.user),
            joinedload(Employee.department),
            joinedload(Employee.designation)
        ).join(User, Employee.user_id == User.id).outerjoin(
            Role,
            User.role_id == Role.id,
        ).filter(
            Employee.is_deleted.is_(False),
            Employee.employee_code.ilike(f"{settings.EMPLOYEE_ID_PREFIX}%"),
            ~Employee.employee_code.ilike(f"{settings.EMPLOYEE_ID_PREFIX}C%"),
            or_(Role.code.is_(None), Role.code.notin_(["CLIENT", "SUPER_ADMIN", "ADMIN"])),
        )

        if company_id:
            query = query.filter(Employee.company_id == company_id)

        if branch_id:
            query = query.filter(Employee.branch_id == branch_id)

        if department_id:
            query = query.filter(Employee.department_id == department_id)

        if designation_id:
            query = query.filter(Employee.designation_id == designation_id)

        if status:
            query = query.filter(Employee.employment_status == status)

        if search:
            query = query.filter(
                or_(
                    Employee.employee_code.ilike(f"%{search}%"),
                    User.first_name.ilike(f"%{search}%"),
                    User.last_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%")
                )
            )

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        employees = query.offset(offset).limit(page_size).all()

        return employees, total

    def create(self, employee_data: EmployeeCreate, created_by: int = None) -> Employee:
        """
        Create a new employee.
        If user_id not provided, creates a new user account.
        Employee codes are always generated by the backend to preserve sequence integrity.
        """
        user_id = employee_data.user_id

        # Helper to convert 0 to None for foreign key fields
        def normalize_fk(val):
            return None if val == 0 or val == '' else val

        department_id = normalize_fk(employee_data.department_id)
        designation_id = normalize_fk(employee_data.designation_id)
        self.validate_department_designation(department_id, designation_id)

        for attempt in range(5):
            try:
                current_user_id = user_id

                # Create user if not provided
                if not current_user_id:
                    if not employee_data.email or not employee_data.first_name:
                        raise ValueError("Email and first_name required to create user")

                    # Generate password if not provided
                    password = employee_data.password or generate_random_password()

                    user = User(
                        email=employee_data.email,
                        password_hash=hash_password(password),
                        first_name=employee_data.first_name,
                        last_name=employee_data.last_name,
                        company_id=normalize_fk(employee_data.company_id),
                        branch_id=normalize_fk(employee_data.branch_id),
                        role_id=normalize_fk(employee_data.role_id),
                        created_by=created_by
                    )

                    self.db.add(user)
                    self.db.flush()
                    current_user_id = user.id

                # Use provided employee code or generate one automatically
                if employee_data.employee_code:
                    employee_code = employee_data.employee_code
                else:
                    employee_code = self.generate_employee_code(skip=attempt)

                # Create employee with normalized FK values
                employee = Employee(
                    user_id=current_user_id,
                    employee_code=employee_code,
                    company_id=normalize_fk(employee_data.company_id),
                    branch_id=normalize_fk(employee_data.branch_id),
                    department_id=department_id,
                    designation_id=designation_id,
                    manager_id=normalize_fk(employee_data.manager_id),
                    joining_date=employee_data.joining_date,
                    employment_type=employee_data.employment_type,
                    work_mode=employee_data.work_mode,
                    shift_id=normalize_fk(employee_data.shift_id),
                    date_of_birth=employee_data.date_of_birth,
                    gender=employee_data.gender,
                    blood_group=employee_data.blood_group,
                    marital_status=employee_data.marital_status,
                    nationality=employee_data.nationality,
                    personal_email=employee_data.personal_email,
                    personal_phone=employee_data.personal_phone,
                    emergency_contact_name=employee_data.emergency_contact_name,
                    emergency_contact_phone=employee_data.emergency_contact_phone,
                    emergency_contact_relation=employee_data.emergency_contact_relation,
                    current_address=employee_data.current_address,
                    permanent_address=employee_data.permanent_address,
                    city=employee_data.city,
                    state=employee_data.state,
                    country=employee_data.country,
                    postal_code=employee_data.postal_code,
                    bank_name=employee_data.bank_name,
                    bank_account_number=employee_data.bank_account_number,
                    bank_ifsc_code=employee_data.bank_ifsc_code,
                    pan_number=employee_data.pan_number,
                    aadhar_number=employee_data.aadhar_number,
                    created_by=created_by
                )

                self.db.add(employee)
                self.db.commit()
                self.db.refresh(employee)
                return employee
            except SQLAlchemyIntegrityError as exc:
                self.db.rollback()
                if employee_data.employee_code and "employee_code" in str(exc).lower():
                    raise ValueError(f"Employee code '{employee_data.employee_code}' already exists")
                if "employee_code" not in str(exc).lower() or attempt == 4:
                    raise

        raise ValueError("Failed to generate a unique employee code")

    def update(self, employee_id: int, employee_data: EmployeeUpdate, updated_by: int = None) -> Employee | None:
        """Update an employee."""
        employee = self.get_by_id(employee_id)

        if not employee:
            return None

        # FK fields that need normalization (convert 0 to None)
        fk_fields = {'department_id', 'designation_id', 'manager_id', 'shift_id', 'branch_id', 'company_id'}

        # Update only provided fields
        update_data = employee_data.model_dump(exclude_unset=True)

        next_department_id = update_data.get('department_id', employee.department_id)
        next_designation_id = update_data.get('designation_id', employee.designation_id)
        if next_department_id == 0 or next_department_id == '':
            next_department_id = None
        if next_designation_id == 0 or next_designation_id == '':
            next_designation_id = None
        self.validate_department_designation(next_department_id, next_designation_id)

        for field, value in update_data.items():
            # Convert 0 to None for FK fields
            if field in fk_fields and (value == 0 or value == ''):
                value = None
            setattr(employee, field, value)

        employee.updated_by = updated_by
        employee.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(employee)

        return employee

    def delete(self, employee_id: int, deleted_by: int = None) -> bool:
        """Soft delete an employee."""
        employee = self.get_by_id(employee_id)

        if not employee:
            return False

        employee.soft_delete(deleted_by)
        self.db.commit()

        return True

    def get_team_members(self, manager_id: int) -> list[Employee]:
        """Get all employees under a manager."""
        return self.db.query(Employee).filter(
            Employee.manager_id == manager_id,
            Employee.is_deleted.is_(False),
            Employee.is_active.is_(True)
        ).all()

    def get_department_employees(self, department_id: int) -> list[Employee]:
        """Get all employees in a department."""
        return self.db.query(Employee).filter(
            Employee.department_id == department_id,
            Employee.is_deleted.is_(False),
            Employee.is_active.is_(True)
        ).all()

    # Document methods
    def add_document(
        self,
        employee_id: int,
        document_type: str,
        document_name: str,
        file_path: str,
        file_size: int = None,
        mime_type: str = None,
        expiry_date: date = None,
        created_by: int = None
    ) -> EmployeeDocument:
        """Add a document to employee."""
        document = EmployeeDocument(
            employee_id=employee_id,
            document_type=document_type,
            document_name=document_name,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            expiry_date=expiry_date,
            created_by=created_by
        )

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        return document

    def get_documents(self, employee_id: int) -> list[EmployeeDocument]:
        """Get all documents for an employee."""
        return self.db.query(EmployeeDocument).filter(
            EmployeeDocument.employee_id == employee_id,
            EmployeeDocument.is_deleted.is_(False)
        ).all()

    def verify_document(self, document_id: int, verified_by: int) -> EmployeeDocument | None:
        """Mark a document as verified."""
        document = self.db.query(EmployeeDocument).filter(
            EmployeeDocument.id == document_id
        ).first()

        if document:
            document.is_verified = True
            document.verified_by = verified_by
            document.verified_at = date.today()
            self.db.commit()
            self.db.refresh(document)

        return document

