"""
Department and Designation schemas.
"""


from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema

# ============== Department Schemas ==============

class DepartmentBase(BaseSchema):
    """Department base schema."""

    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=50)
    description: str | None = None


class DepartmentCreate(DepartmentBase):
    """Department create schema."""

    company_id: int
    parent_id: int | None = None
    manager_id: int | None = None


class DepartmentUpdate(BaseSchema):
    """Department update schema."""

    name: str | None = None
    description: str | None = None
    parent_id: int | None = None
    manager_id: int | None = None
    is_active: bool | None = None


class DepartmentResponse(DepartmentBase, TimestampSchema):
    """Department response schema."""

    id: int
    company_id: int
    parent_id: int | None = None
    manager_id: int | None = None
    level: int
    is_active: bool

    # Display
    parent_name: str | None = None
    manager_name: str | None = None
    employee_count: int = 0
    children: list["DepartmentResponse"] = []


class DepartmentListResponse(BaseSchema):
    """Minimal department info for lists."""

    id: int
    company_id: int
    name: str
    code: str
    parent_id: int | None = None
    level: int
    is_active: bool


class DepartmentTreeResponse(BaseSchema):
    """Department with children for tree view."""

    id: int
    name: str
    code: str
    level: int
    children: list["DepartmentTreeResponse"] = []


# ============== Designation Schemas ==============

class DesignationBase(BaseSchema):
    """Designation base schema."""

    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=50)
    description: str | None = None
    level: int = 1
    min_salary: int | None = None
    max_salary: int | None = None


class DesignationCreate(DesignationBase):
    """Designation create schema."""

    department_id: int | None = None


class DesignationUpdate(BaseSchema):
    """Designation update schema."""

    name: str | None = None
    description: str | None = None
    level: int | None = None
    department_id: int | None = None
    min_salary: int | None = None
    max_salary: int | None = None
    is_active: bool | None = None


class DesignationResponse(DesignationBase, TimestampSchema):
    """Designation response schema."""

    id: int
    department_id: int | None = None
    is_active: bool

    # Display
    department_name: str | None = None
    employee_count: int = 0


class DesignationListResponse(BaseSchema):
    """Minimal designation info for lists."""

    id: int
    name: str
    code: str
    level: int
    department_id: int | None = None
    is_active: bool


# Forward reference updates
DepartmentResponse.model_rebuild()
DepartmentTreeResponse.model_rebuild()

