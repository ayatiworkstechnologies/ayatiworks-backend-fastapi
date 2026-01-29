"""
Common schema utilities and base classes.
"""

from typing import Optional, List, Any, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, ConfigDict


# Generic type for pagination
T = TypeVar('T')


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True
    )



class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditSchema(TimestampSchema):
    """Schema with audit fields."""
    
    created_by: Optional[int] = None
    updated_by: Optional[int] = None



class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema."""
    
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, page_size: int):
        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )


class MessageResponse(BaseModel):
    """Simple message response."""
    
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response schema."""
    
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class BulkOperationResponse(BaseModel):
    """Response for bulk operations."""
    
    success_count: int
    failed_count: int
    errors: Optional[List[dict]] = None
