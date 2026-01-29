"""
Department and Designation schemas.
"""

from typing import Optional, List
from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema, TimestampSchema


# ============== Department Schemas ==============

class DepartmentBase(BaseSchema):
    """Department base schema."""
    
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    """Department create schema."""
    
    company_id: int
    parent_id: Optional[int] = None
    manager_id: Optional[int] = None


class DepartmentUpdate(BaseSchema):
    """Department update schema."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    manager_id: Optional[int] = None
    is_active: Optional[bool] = None


class DepartmentResponse(DepartmentBase, TimestampSchema):
    """Department response schema."""
    
    id: int
    company_id: int
    parent_id: Optional[int] = None
    manager_id: Optional[int] = None
    level: int
    is_active: bool
    
    # Display
    parent_name: Optional[str] = None
    manager_name: Optional[str] = None
    employee_count: int = 0
    children: List["DepartmentResponse"] = []


class DepartmentListResponse(BaseSchema):
    """Minimal department info for lists."""
    
    id: int
    company_id: int
    name: str
    code: str
    parent_id: Optional[int] = None
    level: int
    is_active: bool


class DepartmentTreeResponse(BaseSchema):
    """Department with children for tree view."""
    
    id: int
    name: str
    code: str
    level: int
    children: List["DepartmentTreeResponse"] = []


# ============== Designation Schemas ==============

class DesignationBase(BaseSchema):
    """Designation base schema."""
    
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    level: int = 1
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None


class DesignationCreate(DesignationBase):
    """Designation create schema."""
    
    department_id: Optional[int] = None


class DesignationUpdate(BaseSchema):
    """Designation update schema."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    level: Optional[int] = None
    department_id: Optional[int] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    is_active: Optional[bool] = None


class DesignationResponse(DesignationBase, TimestampSchema):
    """Designation response schema."""
    
    id: int
    department_id: Optional[int] = None
    is_active: bool
    
    # Display
    department_name: Optional[str] = None
    employee_count: int = 0


class DesignationListResponse(BaseSchema):
    """Minimal designation info for lists."""
    
    id: int
    name: str
    code: str
    level: int
    department_id: Optional[int] = None
    is_active: bool


# Forward reference updates
DepartmentResponse.model_rebuild()
DepartmentTreeResponse.model_rebuild()
