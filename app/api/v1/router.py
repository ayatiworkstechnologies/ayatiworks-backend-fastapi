"""
API v1 Router.
Aggregates all API route modules.
"""

from fastapi import APIRouter

from app.api.v1 import (
    auth, 
    employees, 
    attendance,
    companies,
    organizations,
    teams,
    shifts,
    leaves,
    user_management,
    settings,
    projects,
    clients,
    invoices,
    blogs,
    notifications,
    reports,
    permissions,
    roles,
    dashboard,
    public,
    leads,
    meta,
    uploads
)

# Create main v1 router
router = APIRouter(prefix="/api/v1")

# ============== Public Endpoints ==============
router.include_router(public.router)

# ============== Authentication & Users ==============
router.include_router(auth.router)
router.include_router(user_management.router)

# ============== Organization ==============
router.include_router(companies.router)
router.include_router(organizations.router, prefix="/organizations")
router.include_router(teams.router, prefix="/teams")

# ============== HR & Employee Management ==============
router.include_router(employees.router)
router.include_router(attendance.router)
router.include_router(shifts.router)
router.include_router(leaves.router)

# ============== Project Management ==============
router.include_router(projects.router)

# ============== CRM & Business ==============
router.include_router(clients.router)
router.include_router(invoices.router)
router.include_router(leads.router, prefix="/leads")
router.include_router(meta.router)

# ============== Content & CMS ==============
router.include_router(blogs.router)
router.include_router(uploads.router)

# ============== Communication ==============
router.include_router(notifications.router)

# ============== Reports & Dashboard ==============
router.include_router(reports.router)
router.include_router(dashboard.router)

# ============== Settings ==============
router.include_router(settings.router)

# ============== Access Control ==============
router.include_router(permissions.router, prefix="/permissions", tags=["permissions"])
router.include_router(roles.router, prefix="/roles", tags=["roles"])

