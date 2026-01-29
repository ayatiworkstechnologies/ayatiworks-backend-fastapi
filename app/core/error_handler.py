"""
Error handling middleware and exception handlers.
Converts custom exceptions to structured JSON responses.
"""

import traceback
import logging
from datetime import datetime
from typing import Union
from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError as SQLAlchemyIntegrityError, OperationalError

from app.core.exceptions import (
    AppException,
    DatabaseError,
    IntegrityError,
)

logger = logging.getLogger(__name__)


def create_error_response(
    request: Request,
    error_message: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    error_code: str = "INTERNAL_ERROR",
    details: dict = None
) -> JSONResponse:
    """
    Create standardized error response.
    
    Args:
        request: FastAPI request object
        error_message: Human-readable error message
        status_code: HTTP status code
        error_code: Machine-readable error code
        details: Additional error context
    
    Returns:
        JSONResponse with standardized error format
    """
    # Get request ID if available
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    error_response = {
        "error": error_message,
        "error_code": error_code,
        "status_code": status_code,
        "details": details or {},
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "path": str(request.url.path)
    }
    
    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle custom application exceptions.
    
    Converts AppException and its subclasses to structured JSON responses.
    """
    # Log the error
    logger.warning(
        f"Application error: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details
        }
    )
    
    return create_error_response(
        request=request,
        error_message=exc.message,
        status_code=exc.status_code,
        error_code=exc.error_code,
        details=exc.details
    )


async def database_exception_handler(
    request: Request,
    exc: Union[SQLAlchemyIntegrityError, OperationalError]
) -> JSONResponse:
    """
    Handle database exceptions.
    
    Converts SQLAlchemy exceptions to user-friendly responses.
    """
    logger.error(
        f"Database error: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__
        },
        exc_info=True
    )
    
    # Check for common integrity errors
    error_str = str(exc).lower()
    
    if "unique constraint" in error_str or "duplicate" in error_str:
        # Extract field name if possible
        field = "field"
        if "email" in error_str:
            field = "email"
        elif "code" in error_str:
            field = "code"
        
        return create_error_response(
            request=request,
            error_message=f"A record with this {field} already exists",
            status_code=status.HTTP_409_CONFLICT,
            error_code="DUPLICATE_ENTRY",
            details={"field": field}
        )
    
    elif "foreign key constraint" in error_str:
        return create_error_response(
            request=request,
            error_message="Cannot perform operation: referenced resource does not exist or is in use",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="FOREIGN_KEY_VIOLATION"
        )
    
    # Generic database error
    return create_error_response(
        request=request,
        error_message="Database operation failed",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="DATABASE_ERROR"
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.
    
    Catch-all handler for exceptions that weren't caught by specific handlers.
    """
    # Log full stack trace for debugging
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__
        },
        exc_info=True
    )
    
    # In production, don't expose internal error details
    from app.config import settings
    
    if settings.DEBUG:
        error_message = f"{type(exc).__name__}: {str(exc)}"
        details = {
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc()
        }
    else:
        error_message = "An unexpected error occurred. Please try again later."
        details = {
            "exception_type": type(exc).__name__
        }
    
    return create_error_response(
        request=request,
        error_message=error_message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_ERROR",
        details=details
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    from sqlalchemy.exc import IntegrityError as SQLAlchemyIntegrityError, OperationalError
    
    # Custom application exceptions
    app.add_exception_handler(AppException, app_exception_handler)
    
    # Database exceptions
    app.add_exception_handler(SQLAlchemyIntegrityError, database_exception_handler)
    app.add_exception_handler(OperationalError, database_exception_handler)
    
    # Catch-all for unexpected exceptions
    app.add_exception_handler(Exception, unhandled_exception_handler)


def log_error_with_context(
    error: Exception,
    context: dict = None,
    user_id: int = None
):
    """
    Log error with additional context for debugging.
    
    Args:
        error: Exception instance
        context: Additional context dictionary
        user_id: Optional user ID
    """
    log_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        **(context or {})
    }
    
    if user_id:
        log_data["user_id"] = user_id
    
    logger.error(
        f"Error occurred: {type(error).__name__}",
        extra=log_data,
        exc_info=True
    )
