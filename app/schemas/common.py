"""
Common schema utilities and base classes.
"""

from datetime import datetime
from typing import Generic, TypeVar

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

    created_at: datetime | None = None
    updated_at: datetime | None = None


class AuditSchema(TimestampSchema):
    """Schema with audit fields."""

    created_by: int | None = None
    updated_by: int | None = None



class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema."""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def create(cls, items: list[T], total: int, page: int, page_size: int):
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
    detail: str | None = None
    code: str | None = None


class BulkOperationResponse(BaseModel):
    """Response for bulk operations."""

    success_count: int
    failed_count: int
    errors: list[dict] | None = None

