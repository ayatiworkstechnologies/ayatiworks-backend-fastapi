from fastapi import APIRouter
from .employees import router as employees_router
from .attendance import router as attendance_router
from .leaves import router as leaves_router
from .organizations import router as organizations_router
from .clients import router as clients_router
from .projects import router as projects_router
from .invoices import router as invoices_router
from .shifts import router as shifts_router
from .reports import router as reports_router
from .notifications import router as notifications_router
from .settings import router as settings_router
from .roles import router as roles_router
from .permissions import router as permissions_router
from .user_management import router as user_management_router
from .public import router as public_router
from .leads import router as leads_router

router = APIRouter()

router.include_router(employees_router, prefix="/employees", tags=["Employees"])
router.include_router(attendance_router, prefix="/attendance", tags=["Attendance"])
router.include_router(leaves_router, prefix="/leaves", tags=["Leaves"])
router.include_router(organizations_router, prefix="/organizations", tags=["Organizations"])
router.include_router(clients_router, prefix="/clients", tags=["Clients"])
router.include_router(projects_router, prefix="/projects", tags=["Projects"])
router.include_router(invoices_router, prefix="/invoices", tags=["Invoices"])
router.include_router(shifts_router, prefix="/shifts", tags=["Shifts"])
router.include_router(reports_router, prefix="/reports", tags=["Reports"])
router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
router.include_router(settings_router, prefix="/settings", tags=["Settings"])
router.include_router(roles_router, prefix="/roles", tags=["Roles"])
router.include_router(permissions_router, prefix="/permissions", tags=["Permissions"])
router.include_router(user_management_router, tags=["User Management"])
router.include_router(public_router)  # Prefix is defined in the router itself (/public)
