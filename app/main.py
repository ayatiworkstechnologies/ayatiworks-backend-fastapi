"""
FastAPI Application Entry Point.
Enterprise HRMS/CRM/PMS Backend.
"""

import time
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.config import settings
from app.database import init_db
from app.api.v1.router import router as api_v1_router

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
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
        
        # Log request (only if not health check to reduce noise)
        if not request.url.path.startswith("/health"):
            print(
                f"[{request_id}] {request.method} {request.url.path} "
                f"-> {response.status_code} ({duration:.3f}s)"
            )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("🚀 Starting Enterprise HRMS Backend...")
    print(f"📦 Environment: {settings.ENVIRONMENT}")
    print(f"🔧 Debug Mode: {settings.DEBUG}")
    
    # Initialize database tables
    init_db()
    print("✅ Database initialized")
    
    yield
    
    # Shutdown
    print("👋 Shutting down...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    Enterprise HRMS/CRM/PMS Backend API
    
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
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add rate limiter to app state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Add GZip compression for responses > 1KB
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

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
    
    # Get request ID
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

# CORS Middleware - Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        db.execute(text("SELECT 1"))  # Fixed: use text() for raw SQL
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
        db.execute(text("SELECT 1"))  # Fixed: use text() for raw SQL
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

