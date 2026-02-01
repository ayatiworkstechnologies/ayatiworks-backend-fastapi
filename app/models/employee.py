"""
Employee model with auto-generated employee ID.
Supports AW0001 format employee codes.
"""

import enum
from datetime import date

from sqlalchemy import JSON, Boolean, Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import AuditMixin, BaseModel


class WorkMode(enum.Enum):
    """Work mode enum."""
    OFFICE = "office"
    WFH = "wfh"
    REMOTE = "remote"
    HYBRID = "hybrid"


class EmploymentType(enum.Enum):
    """Employment type enum."""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERN = "intern"
    FREELANCE = "freelance"


class EmploymentStatus(enum.Enum):
    """Employment status enum."""
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    PROBATION = "probation"
    NOTICE_PERIOD = "notice_period"
    TERMINATED = "terminated"
    RESIGNED = "resigned"


class Employee(BaseModel, AuditMixin):
    """
    Employee model with comprehensive employee information.
    Employee ID follows format: AW0001, AW0002, etc.
    """

    __tablename__ = "employees"

    # Link to user account
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Employee Identification - Auto-generated like AW0001
    employee_code = Column(String(20), unique=True, nullable=False, index=True)

    # Personal Information
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(10), nullable=True)
    blood_group = Column(String(5), nullable=True)
    marital_status = Column(String(20), nullable=True)
    nationality = Column(String(50), nullable=True)

    # Contact
    personal_email = Column(String(255), nullable=True)
    personal_phone = Column(String(20), nullable=True)
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    emergency_contact_relation = Column(String(50), nullable=True)

    # Address
    current_address = Column(Text, nullable=True)
    permanent_address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)

    # Organization
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    designation_id = Column(Integer, ForeignKey("designations.id"), nullable=True)
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    # Employment Details
    joining_date = Column(Date, nullable=False, default=date.today)
    probation_end_date = Column(Date, nullable=True)
    confirmation_date = Column(Date, nullable=True)
    resignation_date = Column(Date, nullable=True)
    last_working_date = Column(Date, nullable=True)

    employment_type = Column(String(20), default=EmploymentType.FULL_TIME.value)
    employment_status = Column(String(20), default=EmploymentStatus.ACTIVE.value)
    work_mode = Column(String(20), default=WorkMode.OFFICE.value)

    # Shift
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True)

    # Bank Details
    bank_name = Column(String(100), nullable=True)
    bank_account_number = Column(String(50), nullable=True)
    bank_ifsc_code = Column(String(20), nullable=True)
    bank_branch = Column(String(100), nullable=True)

    # Documents
    pan_number = Column(String(20), nullable=True)
    aadhar_number = Column(String(20), nullable=True)
    passport_number = Column(String(20), nullable=True)
    passport_expiry = Column(Date, nullable=True)

    # Additional Info
    skills = Column(JSON, nullable=True)  # List of skills
    certifications = Column(JSON, nullable=True)  # List of certifications
    notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="employee")
    department = relationship("Department", back_populates="employees")
    designation = relationship("Designation", back_populates="employees")
    manager = relationship("Employee", remote_side="Employee.id", backref="team_members")
    documents = relationship("EmployeeDocument", back_populates="employee", cascade="all, delete-orphan")
    team_memberships = relationship("TeamMember", back_populates="employee")

    @classmethod
    def generate_employee_code(cls, db, prefix: str = "AW") -> str:
        """Generate next employee code like AW0001, AW0002, etc."""
        from sqlalchemy import func

        # Get the last employee code
        result = db.query(func.max(cls.employee_code)).filter(
            cls.employee_code.like(f"{prefix}%")
        ).scalar()

        if result:
            # Extract number and increment
            num = int(result.replace(prefix, "")) + 1
        else:
            num = 1

        # Format with leading zeros (4 digits)
        return f"{prefix}{num:04d}"


class EmployeeDocument(BaseModel, AuditMixin):
    """
    Employee documents storage.
    """

    __tablename__ = "employee_documents"

    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    document_type = Column(String(50), nullable=False)  # id_proof, address_proof, offer_letter, etc.
    document_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    expiry_date = Column(Date, nullable=True)
    is_verified = Column(Boolean, default=False)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    employee = relationship("Employee", back_populates="documents")

