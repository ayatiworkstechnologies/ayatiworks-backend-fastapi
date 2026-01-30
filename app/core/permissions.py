"""
Permission checking utilities and decorators.
"""

from enum import Enum
from functools import wraps
from typing import List, Optional, Callable

from fastapi import HTTPException, status


class PermissionCode(str, Enum):
    """All permission codes in the system."""
    
    # Super Admin
    SUPER_ADMIN = "super_admin"
    
    # Dashboard
    DASHBOARD_VIEW = "dashboard.view"
    
    # User Management
    USER_VIEW = "user.view"
    USER_CREATE = "user.create"
    USER_EDIT = "user.edit"
    USER_DELETE = "user.delete"
    
    # Role Management
    ROLE_VIEW = "role.view"
    ROLE_CREATE = "role.create"
    ROLE_EDIT = "role.edit"
    ROLE_DELETE = "role.delete"
    
    # Settings
    SETTINGS_VIEW = "settings.view"
    SETTINGS_EDIT = "settings.edit"
    FEATURE_MANAGE = "feature.manage"
    
    # Company
    COMPANY_VIEW = "company.view"
    COMPANY_CREATE = "company.create"
    COMPANY_EDIT = "company.edit"
    COMPANY_DELETE = "company.delete"
    
    # Branch
    BRANCH_VIEW = "branch.view"
    BRANCH_CREATE = "branch.create"
    BRANCH_EDIT = "branch.edit"
    BRANCH_DELETE = "branch.delete"
    
    # Department
    DEPARTMENT_VIEW = "department.view"
    DEPARTMENT_CREATE = "department.create"
    DEPARTMENT_EDIT = "department.edit"
    DEPARTMENT_DELETE = "department.delete"
    
    # Designation
    DESIGNATION_VIEW = "designation.view"
    DESIGNATION_CREATE = "designation.create"
    DESIGNATION_EDIT = "designation.edit"
    DESIGNATION_DELETE = "designation.delete"
    
    # Employee
    EMPLOYEE_VIEW = "employee.view"
    EMPLOYEE_VIEW_ALL = "employee.view_all"
    EMPLOYEE_CREATE = "employee.create"
    EMPLOYEE_EDIT = "employee.edit"
    EMPLOYEE_DELETE = "employee.delete"
    
    # Attendance
    ATTENDANCE_VIEW = "attendance.view"
    ATTENDANCE_VIEW_ALL = "attendance.view_all"
    ATTENDANCE_MARK = "attendance.mark"
    ATTENDANCE_EDIT = "attendance.edit"
    ATTENDANCE_APPROVE = "attendance.approve"
    
    # Leave
    LEAVE_VIEW = "leave.view"
    LEAVE_VIEW_ALL = "leave.view_all"
    LEAVE_APPLY = "leave.apply"
    LEAVE_APPROVE = "leave.approve"
    LEAVE_CANCEL = "leave.cancel"
    
    # Holiday
    HOLIDAY_VIEW = "holiday.view"
    HOLIDAY_MANAGE = "holiday.manage"
    
    # Shift
    SHIFT_VIEW = "shift.view"
    SHIFT_MANAGE = "shift.manage"
    
    # Payroll
    PAYROLL_VIEW = "payroll.view"
    PAYROLL_VIEW_ALL = "payroll.view_all"
    PAYROLL_MANAGE = "payroll.manage"
    
    # Salary
    SALARY_VIEW = "salary.view"
    SALARY_VIEW_ALL = "salary.view_all"
    SALARY_CREATE = "salary.create"
    SALARY_EDIT = "salary.edit"
    SALARY_DELETE = "salary.delete"
    SALARY_APPROVE = "salary.approve"
    
    # Project
    PROJECT_VIEW = "project.view"
    PROJECT_VIEW_ALL = "project.view_all"
    PROJECT_VIEW_OWN = "project.view_own"
    PROJECT_CREATE = "project.create"
    PROJECT_EDIT = "project.edit"
    PROJECT_DELETE = "project.delete"
    
    # Task
    TASK_VIEW = "task.view"
    TASK_VIEW_ALL = "task.view_all"
    TASK_CREATE = "task.create"
    TASK_EDIT = "task.edit"
    TASK_DELETE = "task.delete"
    TASK_ASSIGN = "task.assign"
    
    # Team
    TEAM_VIEW = "team.view"
    TEAM_CREATE = "team.create"
    TEAM_EDIT = "team.edit"
    TEAM_DELETE = "team.delete"
    TEAM_MANAGE_MEMBERS = "team.manage_members"
    
    # Client
    CLIENT_VIEW = "client.view"
    CLIENT_VIEW_OWN = "client.view_own"
    CLIENT_CREATE = "client.create"
    CLIENT_EDIT = "client.edit"
    CLIENT_DELETE = "client.delete"
    
    # Lead
    LEAD_VIEW = "lead.view"
    LEAD_CREATE = "lead.create"
    LEAD_EDIT = "lead.edit"
    LEAD_DELETE = "lead.delete"
    
    # Deal
    DEAL_VIEW = "deal.view"
    DEAL_CREATE = "deal.create"
    DEAL_EDIT = "deal.edit"
    DEAL_DELETE = "deal.delete"
    
    # Invoice
    INVOICE_VIEW = "invoice.view"
    INVOICE_VIEW_OWN = "invoice.view_own"
    INVOICE_CREATE = "invoice.create"
    INVOICE_EDIT = "invoice.edit"
    INVOICE_DELETE = "invoice.delete"
    
    # Timesheet
    TIMESHEET_VIEW = "timesheet.view"
    TIMESHEET_VIEW_ALL = "timesheet.view_all"
    TIMESHEET_CREATE = "timesheet.create"
    TIMESHEET_APPROVE = "timesheet.approve"
    
    # Report
    REPORT_VIEW = "report.view"
    REPORT_EXPORT = "report.export"
    REPORT_CREATE = "report.create"
    
    # Audit
    AUDIT_VIEW = "audit.view"

    # Meta Ads
    META_VIEW = "meta.view"
    META_MANAGE = "meta.manage" # Sync, Edit Config

    # Blog
    BLOG_VIEW = "blog.view"
    BLOG_CREATE = "blog.create"
    BLOG_EDIT = "blog.edit"
    BLOG_DELETE = "blog.delete"


def get_all_permissions() -> List[dict]:
    """Get all permissions with metadata."""
    permissions = [
        # Dashboard
        {"code": "dashboard.view", "name": "View Dashboard", "module": "dashboard"},

        # Users
        {"code": "user.view", "name": "View Users", "module": "users"},
        {"code": "user.create", "name": "Create Users", "module": "users"},
        {"code": "user.edit", "name": "Edit Users", "module": "users"},
        {"code": "user.delete", "name": "Delete Users", "module": "users"},
        
        # Roles
        {"code": "role.view", "name": "View Roles", "module": "roles"},
        {"code": "role.create", "name": "Create Roles", "module": "roles"},
        {"code": "role.edit", "name": "Edit Roles", "module": "roles"},
        {"code": "role.delete", "name": "Delete Roles", "module": "roles"},
        
        # Settings
        {"code": "settings.view", "name": "View Settings", "module": "settings"},
        {"code": "settings.edit", "name": "Edit Settings", "module": "settings"},
        {"code": "feature.manage", "name": "Manage Features", "module": "settings"},
        
        # Company
        {"code": "company.view", "name": "View Companies", "module": "company"},
        {"code": "company.create", "name": "Create Companies", "module": "company"},
        {"code": "company.edit", "name": "Edit Companies", "module": "company"},
        {"code": "company.delete", "name": "Delete Companies", "module": "company"},
        
        # Branch
        {"code": "branch.view", "name": "View Branches", "module": "branch"},
        {"code": "branch.create", "name": "Create Branches", "module": "branch"},
        {"code": "branch.edit", "name": "Edit Branches", "module": "branch"},
        {"code": "branch.delete", "name": "Delete Branches", "module": "branch"},
        
        # Department
        {"code": "department.view", "name": "View Departments", "module": "department"},
        {"code": "department.create", "name": "Create Departments", "module": "department"},
        {"code": "department.edit", "name": "Edit Departments", "module": "department"},
        {"code": "department.delete", "name": "Delete Departments", "module": "department"},
        
        # Designation
        {"code": "designation.view", "name": "View Designations", "module": "designation"},
        {"code": "designation.create", "name": "Create Designations", "module": "designation"},
        {"code": "designation.edit", "name": "Edit Designations", "module": "designation"},
        {"code": "designation.delete", "name": "Delete Designations", "module": "designation"},
        
        # Employee
        {"code": "employee.view", "name": "View Own Profile", "module": "employee"},
        {"code": "employee.view_all", "name": "View All Employees", "module": "employee"},
        {"code": "employee.create", "name": "Create Employees", "module": "employee"},
        {"code": "employee.edit", "name": "Edit Employees", "module": "employee"},
        {"code": "employee.delete", "name": "Delete Employees", "module": "employee"},
        
        # Attendance
        {"code": "attendance.view", "name": "View Own Attendance", "module": "attendance"},
        {"code": "attendance.view_all", "name": "View All Attendance", "module": "attendance"},
        {"code": "attendance.mark", "name": "Mark Attendance", "module": "attendance"},
        {"code": "attendance.edit", "name": "Edit Attendance", "module": "attendance"},
        {"code": "attendance.approve", "name": "Approve Attendance", "module": "attendance"},
        
        # Leave
        {"code": "leave.view", "name": "View Own Leaves", "module": "leave"},
        {"code": "leave.view_all", "name": "View All Leaves", "module": "leave"},
        {"code": "leave.apply", "name": "Apply Leave", "module": "leave"},
        {"code": "leave.approve", "name": "Approve Leave", "module": "leave"},
        {"code": "leave.cancel", "name": "Cancel Leave", "module": "leave"},
        
        # Holiday
        {"code": "holiday.view", "name": "View Holidays", "module": "holiday"},
        {"code": "holiday.manage", "name": "Manage Holidays", "module": "holiday"},
        
        # Shift
        {"code": "shift.view", "name": "View Shifts", "module": "shift"},
        {"code": "shift.manage", "name": "Manage Shifts", "module": "shift"},
        
        # Payroll
        {"code": "payroll.view", "name": "View Own Payslip", "module": "payroll"},
        {"code": "payroll.view_all", "name": "View All Payroll", "module": "payroll"},
        {"code": "payroll.manage", "name": "Manage Payroll", "module": "payroll"},
        
        # Salary
        {"code": "salary.view", "name": "View Own Salary", "module": "salary"},
        {"code": "salary.view_all", "name": "View All Salaries", "module": "salary"},
        {"code": "salary.create", "name": "Create Salary Structure", "module": "salary"},
        {"code": "salary.edit", "name": "Edit Salary Structure", "module": "salary"},
        {"code": "salary.delete", "name": "Delete Salary Structure", "module": "salary"},
        {"code": "salary.approve", "name": "Approve Salary/Payslip", "module": "salary"},
        
        # Project
        {"code": "project.view", "name": "View Own Projects", "module": "project"},
        {"code": "project.view_all", "name": "View All Projects", "module": "project"},
        {"code": "project.view_own", "name": "View Assigned Projects (Client)", "module": "project"},
        {"code": "project.create", "name": "Create Projects", "module": "project"},
        {"code": "project.edit", "name": "Edit Projects", "module": "project"},
        {"code": "project.delete", "name": "Delete Projects", "module": "project"},
        
        # Task
        {"code": "task.view", "name": "View Own Tasks", "module": "task"},
        {"code": "task.view_all", "name": "View All Tasks", "module": "task"},
        {"code": "task.create", "name": "Create Tasks", "module": "task"},
        {"code": "task.edit", "name": "Edit Tasks", "module": "task"},
        {"code": "task.delete", "name": "Delete Tasks", "module": "task"},
        {"code": "task.assign", "name": "Assign Tasks", "module": "task"},
        
        # Team
        {"code": "team.view", "name": "View Teams", "module": "team"},
        {"code": "team.create", "name": "Create Teams", "module": "team"},
        {"code": "team.edit", "name": "Edit Teams", "module": "team"},
        {"code": "team.delete", "name": "Delete Teams", "module": "team"},
        {"code": "team.manage_members", "name": "Manage Team Members", "module": "team"},
        
        # Client
        {"code": "client.view", "name": "View Clients", "module": "client"},
        {"code": "client.view_own", "name": "View Own Client Profile", "module": "client"},
        {"code": "client.create", "name": "Create Clients", "module": "client"},
        {"code": "client.edit", "name": "Edit Clients", "module": "client"},
        {"code": "client.delete", "name": "Delete Clients", "module": "client"},
        
        # Invoice
        {"code": "invoice.view", "name": "View Invoices", "module": "invoice"},
        {"code": "invoice.view_own", "name": "View Own Invoices", "module": "invoice"},
        {"code": "invoice.create", "name": "Create Invoices", "module": "invoice"},
        {"code": "invoice.edit", "name": "Edit Invoices", "module": "invoice"},
        {"code": "invoice.delete", "name": "Delete Invoices", "module": "invoice"},
        
        # Report
        {"code": "report.view", "name": "View Reports", "module": "report"},
        {"code": "report.export", "name": "Export Reports", "module": "report"},
        {"code": "report.create", "name": "Create Reports", "module": "report"},
        
        # Audit
        {"code": "audit.view", "name": "View Audit Logs", "module": "audit"},
        
        # Meta Ads
        {"code": "meta.view", "name": "View Meta Ads", "module": "meta"},
        {"code": "meta.manage", "name": "Manage Meta Ads", "module": "meta"},
        
        # Blog
        {"code": "blog.view", "name": "View Blog Posts", "module": "blog"},
        {"code": "blog.create", "name": "Create Blog Posts", "module": "blog"},
        {"code": "blog.edit", "name": "Edit Blog Posts", "module": "blog"},
        {"code": "blog.delete", "name": "Delete Blog Posts", "module": "blog"},
    ]
    return permissions


def check_permission(user_permissions: List[str], required_permission: str) -> bool:
    """
    Check if user has the required permission.
    
    Args:
        user_permissions: List of user's permission codes
        required_permission: Required permission code
    
    Returns:
        True if user has permission
    """
    # Super admin has all permissions
    if PermissionCode.SUPER_ADMIN.value in user_permissions:
        return True
    
    return required_permission in user_permissions


def has_any_permission(user_permissions: List[str], required_permissions: List[str]) -> bool:
    """Check if user has any of the required permissions."""
    if PermissionCode.SUPER_ADMIN.value in user_permissions:
        return True
    
    return any(perm in user_permissions for perm in required_permissions)


def has_all_permissions(user_permissions: List[str], required_permissions: List[str]) -> bool:
    """Check if user has all of the required permissions."""
    if PermissionCode.SUPER_ADMIN.value in user_permissions:
        return True
    
    return all(perm in user_permissions for perm in required_permissions)
