"""
Custom exception classes for the application.
Provides specific exception types for different error scenarios.
"""

from typing import Any

from fastapi import status


class AppException(Exception):
    """
    Base application exception.
    All custom exceptions should inherit from this.
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str | None = None,
        details: dict[str, Any] | None = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


# Authentication & Authorization Exceptions

class AuthenticationError(AppException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            **kwargs
        )


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid."""

    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message=message, error_code="INVALID_CREDENTIALS")


class AccountLockedError(AuthenticationError):
    """Raised when account is locked due to too many failed attempts."""

    def __init__(self, lockout_minutes: int = 30):
        super().__init__(
            message=f"Account locked due to too many failed attempts. Try again in {lockout_minutes} minutes.",
            error_code="ACCOUNT_LOCKED",
            details={"lockout_minutes": lockout_minutes}
        )


class TokenExpiredError(AuthenticationError):
    """Raised when token has expired."""

    def __init__(self):
        super().__init__(
            message="Token has expired",
            error_code="TOKEN_EXPIRED"
        )


class InvalidTokenError(AuthenticationError):
    """Raised when token is invalid."""

    def __init__(self):
        super().__init__(
            message="Invalid token",
            error_code="INVALID_TOKEN"
        )


class PermissionDeniedError(AppException):
    """Raised when user lacks required permissions."""

    def __init__(self, permission: str | None = None):
        message = f"Permission denied: {permission}" if permission else "Permission denied"
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="PERMISSION_DENIED",
            details={"required_permission": permission} if permission else {}
        )


# Resource Exceptions

class ResourceNotFoundError(AppException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource_type: str, resource_id: Any = None):
        message = f"{resource_type} not found"
        if resource_id:
            message += f": {resource_id}"

        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


class ResourceAlreadyExistsError(AppException):
    """Raised when attempting to create a resource that already exists."""

    def __init__(self, resource_type: str, field: str, value: Any):
        super().__init__(
            message=f"{resource_type} with {field}='{value}' already exists",
            status_code=status.HTTP_409_CONFLICT,
            error_code="RESOURCE_ALREADY_EXISTS",
            details={"resource_type": resource_type, "field": field, "value": value}
        )


class ResourceConflictError(AppException):
    """Raised when there's a conflict with resource state."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="RESOURCE_CONFLICT",
            **kwargs
        )


# Validation Exceptions

class ValidationError(AppException):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str | None = None, **kwargs):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field

        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details
        )


class InvalidInputError(ValidationError):
    """Raised when input is invalid."""

    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"Invalid {field}: {message}",
            field=field
        )


class MissingRequiredFieldError(ValidationError):
    """Raised when a required field is missing."""

    def __init__(self, field: str):
        super().__init__(
            message=f"Required field missing: {field}",
            field=field,
            error_code="MISSING_REQUIRED_FIELD"
        )


# Business Logic Exceptions

class BusinessLogicError(AppException):
    """Raised when business logic validation fails."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BUSINESS_LOGIC_ERROR",
            **kwargs
        )


class InsufficientBalanceError(BusinessLogicError):
    """Raised when leave balance is insufficient."""

    def __init__(self, leave_type: str, required: float, available: float):
        super().__init__(
            message=f"Insufficient {leave_type} balance",
            details={
                "leave_type": leave_type,
                "required": required,
                "available": available,
                "shortage": required - available
            }
        )


class InvalidStatusTransitionError(BusinessLogicError):
    """Raised when attempting an invalid status transition."""

    def __init__(self, entity: str, current_status: str, target_status: str):
        super().__init__(
            message=f"Cannot transition {entity} from {current_status} to {target_status}",
            details={
                "entity": entity,
                "current_status": current_status,
                "target_status": target_status
            }
        )


# Database Exceptions

class DatabaseError(AppException):
    """Raised when database operation fails."""

    def __init__(self, message: str = "Database error occurred", **kwargs):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            **kwargs
        )


class IntegrityError(DatabaseError):
    """Raised when database integrity constraint is violated."""

    def __init__(self, message: str = "Data integrity violation"):
        super().__init__(
            message=message,
            error_code="INTEGRITY_ERROR"
        )


# Service Exceptions

class ServiceUnavailableError(AppException):
    """Raised when external service is unavailable."""

    def __init__(self, service: str):
        super().__init__(
            message=f"Service unavailable: {service}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
            details={"service": service}
        )


class RateLimitExceededError(AppException):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after}
        )

