"""
Application configuration settings using Pydantic BaseSettings.
Loads from environment variables and .env file.

SECURITY NOTE: Never commit actual secrets to this file.
All sensitive values must be provided via environment variables.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "Enterprise HRMS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database - REQUIRED, no default (must be in .env)
    DATABASE_URL: str = Field(..., description="Database connection URL")
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600

    # JWT Authentication - REQUIRED, no default (must be in .env)
    SECRET_KEY: str = Field(..., min_length=32, description="JWT signing key - must be at least 32 characters")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Email SMTP - REQUIRED for production
    SMTP_HOST: str = Field(default="", description="SMTP server hostname")
    SMTP_PORT: int = 587
    SMTP_USER: str = Field(default="", description="SMTP username")
    SMTP_PASSWORD: str = Field(default="", description="SMTP password")
    SMTP_FROM_EMAIL: str = Field(default="noreply@example.com", description="From email address")
    SMTP_FROM_NAME: str = "Enterprise HRMS"
    SMTP_USE_TLS: bool = True

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate SECRET_KEY is not a placeholder."""
        if 'change-in-production' in v.lower() or 'your-' in v.lower():
            raise ValueError(
                "SECRET_KEY contains placeholder text. "
                "Generate a secure key using: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters for security")
        return v

    # Redis (for caching & Celery)
    REDIS_URL: str | None = Field(default=None, description="Redis connection URL")

    # Sentry (error tracking)
    SENTRY_DSN: str | None = Field(default=None, description="Sentry DSN for error tracking")

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    ALLOWED_EXTENSIONS: list[str] = ["jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "xls", "xlsx"]

    # Employee ID Configuration
    EMPLOYEE_ID_PREFIX: str = "AW"
    EMPLOYEE_ID_LENGTH: int = 4  # Total digits after prefix (AW0001)

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Security
    PASSWORD_MIN_LENGTH: int = 8
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30

    # 2FA
    OTP_EXPIRY_MINUTES: int = 5
    OTP_LENGTH: int = 6

    # Attendance Settings
    ATTENDANCE_GRACE_PERIOD_MINUTES: int = 15  # Grace time for late check-in
    ATTENDANCE_AVG_WORKING_HOURS: float = 9.0  # Average expected hours per day
    ATTENDANCE_MIN_WORKING_HOURS: float = 4.5  # Minimum for half-day
    ATTENDANCE_SHIFT_START_TIME: str = "09:00"  # Default shift start
    ATTENDANCE_SHIFT_END_TIME: str = "18:00"  # Default shift end


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

