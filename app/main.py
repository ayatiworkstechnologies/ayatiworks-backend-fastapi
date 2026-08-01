"""
FastAPI Application Entry Point.
Ayatiworks Tech/CRM/PMS Backend.
Optimized for fast request/response performance.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from fastapi.responses import ORJSONResponse
    DEFAULT_RESPONSE_CLASS = ORJSONResponse
except ImportError:
    DEFAULT_RESPONSE_CLASS = JSONResponse

from app.api.v1.router import router as api_v1_router
from app.config import settings
from app.core.rate_limit import limiter
from app.database import init_db

# Configure structured logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("app")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS - only in production
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing and request ID."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Add request ID to state for access in endpoints
        request.state.request_id = request_id

        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log request (skip health checks and static files to reduce noise)
        path = request.url.path
        if not path.startswith(("/health", "/uploads")):
            level = logging.WARNING if duration > 1.0 else logging.INFO
            logger.log(
                level,
                f"[{request_id}] {request.method} {path} "
                f"-> {response.status_code} ({duration:.3f}s)"
            )

        # Add performance headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("🚀 Starting Ayatiworks Tech Backend v%s", settings.APP_VERSION)
    logger.info("📦 Environment: %s | Debug: %s", settings.ENVIRONMENT, settings.DEBUG)

    # Initialize database tables
    auto_created = init_db()
    if not auto_created:
        logger.info("Database auto-creation skipped; expecting Alembic-managed schema.")
    logger.info("✅ Database initialized (pool_size=%d, max_overflow=%d)",
                settings.DB_POOL_SIZE, settings.DB_MAX_OVERFLOW)

    yield

    # Shutdown
    logger.info("👋 Shutting down...")


# Disable docs in production for security
_is_production = settings.ENVIRONMENT == "production"

# Create FastAPI application with ORJSONResponse for ~3x faster serialization
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    Ayatiworks Tech/CRM/PMS Backend API

    ## Features
    - 🔐 Authentication & Authorization
    - 👥 Employee Management (Employee ID: AW0001 format)
    - ⏰ Attendance Tracking (Office/WFH/Remote)
    - 📅 Leave Management
    - 💼 Payroll & HR
    - 📊 Project Management
    - 🤝 Client Management (CRM)
    - 📈 Reporting & Analytics
    """,
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
    lifespan=lifespan,
    default_response_class=DEFAULT_RESPONSE_CLASS,
)

# Add rate limiter to app state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ============================================================
# MIDDLEWARE ORDER MATTERS! Added in REVERSE order of execution.
# Execution order: CORS -> GZip -> Security -> Logging
# So we add them: Logging -> Security -> GZip -> CORS
# ============================================================

# 4. Request logging (innermost)
app.add_middleware(RequestLoggingMiddleware)

# 3. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 2. GZip compression for responses > 500 bytes
app.add_middleware(GZipMiddleware, minimum_size=500)

# 1. CORS (outermost - must process first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=(None if _is_production else r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register custom exception handlers
from app.core.error_handler import register_exception_handlers

register_exception_handlers(app)


# Keep validation error handler for Pydantic validation
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    request_id = getattr(request.state, 'request_id', 'unknown')

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "error_code": "VALIDATION_ERROR",
            "status_code": 422,
            "details": {"fields": errors},
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "path": str(request.url.path)
        }
    )


# Include API routers
app.include_router(api_v1_router)

# Serve uploaded files statically
import os

from fastapi.staticfiles import StaticFiles

uploads_dir = settings.UPLOAD_DIR
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


# Health check endpoints
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION
    }


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Readiness probe - checks if app can serve traffic."""
    from app.database import SessionLocal

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not ready", "database": "disconnected", "error": str(e)}
        )


@app.get("/health/live", tags=["Health"])
async def liveness_check():
    """Liveness probe - checks if app is alive."""
    return {"status": "alive"}


@app.get("/health/db", tags=["Health"])
async def database_health():
    """Database connectivity check."""
    from app.database import SessionLocal

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "disconnected", "error": str(e)}
        )


# Development server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
