"""
Department and Designation models.
Organizational structure management.
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import AuditMixin, BaseModel


class Department(BaseModel, AuditMixin):
    """
    Department model with hierarchical structure support.
    """

    __tablename__ = "departments"

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Hierarchy
    parent_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    level = Column(Integer, default=0)
    path = Column(String(255), nullable=True)  # Materialized path: "1/5/12"

    # Manager
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    company = relationship("Company", back_populates="departments")
    parent = relationship("Department", remote_side="Department.id", backref="children")
    designations = relationship("Designation", back_populates="department")
    employees = relationship("Employee", back_populates="department")


class Designation(BaseModel, AuditMixin):
    """
    Designation/Job Title model.
    """

    __tablename__ = "designations"

    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Organization
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    level = Column(Integer, default=1)  # Seniority level (1=Junior, 5=Senior, 10=Executive)

    # Compensation Range (optional)
    min_salary = Column(Integer, nullable=True)
    max_salary = Column(Integer, nullable=True)

    # Relationships
    department = relationship("Department", back_populates="designations")
    employees = relationship("Employee", back_populates="designation")

