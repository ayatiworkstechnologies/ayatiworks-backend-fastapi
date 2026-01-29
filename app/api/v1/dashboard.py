"""
Dashboard API endpoints.
Provides role-based dashboard statistics and data.
"""

from typing import Any, Dict
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models.auth import User, Role
from app.models.employee import Employee
from app.models.company import Company, Branch
from app.models.organization import Department
from app.models.project import Project, Task
from app.models.attendance import Attendance
from app.models.leave import Leave, LeaveBalance
from app.models.client import Client
from app.models.invoice import Invoice, InvoiceStatus
from app.models.project import Project, Task, TaskStatus, ProjectMember
from app.api.deps import get_current_active_user
from app.core.exceptions import (
    ResourceNotFoundError,
    ResourceAlreadyExistsError,
    InvalidCredentialsError,
    PermissionDeniedError,
    ValidationError,
    BusinessLogicError
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get role-based dashboard statistics.
    Returns different stats based on user's role.
    """
    # Get user's role
    role_code = current_user.role.code if current_user.role else "EMPLOYEE"
    
    # Base response
    stats = {
        "role": role_code,
        "user_name": current_user.full_name,
    }
    
    # Role-specific stats
    if role_code == "SUPER_ADMIN":
        stats.update(_get_super_admin_stats(db))
    elif role_code == "ADMIN":
        stats.update(_get_admin_stats(db, current_user))
    elif role_code == "MANAGER":
        stats.update(_get_manager_stats(db, current_user))
    elif role_code == "HR":
        stats.update(_get_hr_stats(db, current_user))
    elif role_code == "CLIENT":
        stats.update(_get_client_stats(db, current_user))
    else:  # EMPLOYEE or default
        stats.update(_get_employee_stats(db, current_user))
    
    return stats


@router.get("/project-overview")
def get_project_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get project overview statistics for Projects page.
    """
    query = db.query(Project).filter(Project.is_deleted == False)
    
    # If client, filter by client
    if current_user.role and current_user.role.code == "CLIENT":
        client = db.query(Client).filter(Client.email == current_user.email).first()
        if client:
            query = query.filter(Project.client_id == client.id)
        else:
            return {"total": 0, "by_status": {}}
    
    # Calculate counts by status
    status_counts = {}
    projects = query.all()
    
    for p in projects:
        status_value = p.status
        status_counts[status_value] = status_counts.get(status_value, 0) + 1
        
    return {
        "total": len(projects),
        "by_status": status_counts
    }


def _get_super_admin_stats(db: Session) -> Dict[str, Any]:
    """Stats for Super Admin role."""
    total_companies = db.query(Company).filter(Company.is_active == True).count()
    total_users = db.query(User).filter(User.is_active == True).count()
    total_employees = db.query(Employee).count()
    active_projects = db.query(Project).filter(Project.status.in_(["active", "in_progress"])).count()
    
    # System health check (DB connection)
    try:
        db.execute("SELECT 1")
        system_health = "Healthy"
    except Exception:
        system_health = "Degraded"

    return {
        "companies_count": total_companies,
        "users_count": total_users,
        "employees_count": total_employees,
        "active_projects": active_projects,
        "system_health": system_health,
    }


def _get_admin_stats(db: Session, user: User) -> Dict[str, Any]:
    """Stats for Admin role."""
    company_id = user.company_id
    
    employees_count = db.query(Employee).filter(
        Employee.company_id == company_id
    ).count()
    
    projects_count = db.query(Project).filter(
        Project.company_id == company_id,
        Project.status.in_(["active", "in_progress"])
    ).count()
    
    departments_count = db.query(Department).filter(
        Department.company_id == company_id
    ).count()
    
    # Pending approvals (leaves)
    pending_leaves = db.query(Leave).filter(
        Leave.company_id == company_id,
        Leave.status == "pending"
    ).count()
    
    return {
        "employees_count": employees_count,
        "projects_count": projects_count,
        "departments_count": departments_count,
        "pending_approvals": pending_leaves,
    }


def _get_manager_stats(db: Session, user: User) -> Dict[str, Any]:
    """Stats for Manager role."""
    # Get team members (employees reporting to this manager)
    employee = db.query(Employee).filter(Employee.user_id == user.id).first()
    
    if not employee:
        return {
            "team_members_count": 0,
            "active_projects": 0,
            "tasks_this_week": 0,
            "team_attendance_rate": 0,
        }
    
    team_members = db.query(Employee).filter(
        Employee.manager_id == employee.id
    ).count()
    
    # Projects where user is manager or team member
    active_projects = db.query(Project).filter(
        or_(
            Project.manager_id == employee.id,
            Project.members.any(ProjectMember.employee_id == employee.id)
        ),
        Project.status.in_(["active", "in_progress"])
    ).count()
    
    # Tasks completed by team this week
    week_start = datetime.now() - timedelta(days=datetime.now().weekday())
    
    # Get IDs of all team members
    team_member_ids = db.query(Employee.id).filter(Employee.manager_id == employee.id).all()
    team_member_ids = [t[0] for t in team_member_ids]
    
    tasks_this_week = 0
    if team_member_ids:
        tasks_this_week = db.query(Task).filter(
            Task.assignee_id.in_(team_member_ids),
            Task.status == TaskStatus.DONE.value,
            Task.updated_at >= week_start
        ).count()
    
    # Team attendance rate (today)
    today = datetime.now().date()
    team_present = db.query(Attendance).filter(
        Attendance.employee_id.in_(team_member_ids),
        func.date(Attendance.check_in) == today
    ).count()
    
    attendance_rate = (team_present / team_members * 100) if team_members > 0 else 0
    
    return {
        "team_members_count": team_members,
        "active_projects": active_projects,
        "tasks_this_week": tasks_this_week,  # Completed by team
        "team_attendance_rate": round(attendance_rate, 1),
    }


def _get_hr_stats(db: Session, user: User) -> Dict[str, Any]:
    """Stats for HR role."""
    company_id = user.company_id
    
    employees_count = db.query(Employee).filter(
        Employee.company_id == company_id,
        Employee.employment_status == "active"
    ).count()
    
    # Employees on leave today
    today = datetime.now().date()
    on_leave_today = db.query(Leave).filter(
        Leave.company_id == company_id,
        Leave.status == "approved",
        Leave.start_date <= today,
        Leave.end_date >= today
    ).count()
    
    # Pending leave requests
    pending_leaves = db.query(Leave).filter(
        Leave.company_id == company_id,
        Leave.status == "pending"
    ).count()
    
    new_hires = db.query(Employee).filter(
        Employee.company_id == company_id,
        Employee.joining_date >= first_day_of_month.date()
    ).count()
    
    # Present today (checked in)
    present_today = db.query(Attendance).join(Employee).filter(
        Employee.company_id == company_id,
        func.date(Attendance.check_in) == today
    ).count()
    
    return {
        "employees_count": employees_count,
        "on_leave_today": on_leave_today,
        "pending_leaves": pending_leaves,
        "new_hires_month": new_hires,
        "present_today": present_today,
    }


def _get_employee_stats(db: Session, user: User) -> Dict[str, Any]:
    """Stats for Employee role."""
    employee = db.query(Employee).filter(Employee.user_id == user.id).first()
    
    if not employee:
        return {
            "my_tasks_count": 0,
            "leave_balance": 0,
            "hours_this_month": 0,
            "my_projects_count": 0,
        }
    
    # My tasks
    my_tasks = db.query(Task).filter(
        Task.assignee_id == employee.id,
        Task.status.in_(["todo", "in_progress"])
    ).count()
    
    # Leave balance (from LeaveBalance model)
    current_year = datetime.now().year
    leave_balances = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == employee.id,
        LeaveBalance.year == current_year
    ).all()
    
    # Sum available balance from all leave types
    leave_balance = sum([lb.available for lb in leave_balances]) if leave_balances else 0
    
    # Hours worked this month
    first_day_of_month = datetime.now().replace(day=1)
    attendances = db.query(Attendance).filter(
        Attendance.employee_id == employee.id,
        Attendance.check_in >= first_day_of_month
    ).all()
    
    total_hours = 0
    for att in attendances:
        if att.check_out:
            delta = att.check_out - att.check_in
            total_hours += delta.total_seconds() / 3600
    
    # My projects
    my_projects = db.query(Project).filter(
        or_(
            Project.manager_id == employee.id,
            Project.members.any(ProjectMember.employee_id == employee.id)
        ),
        Project.status.in_(["active", "in_progress"])
    ).count()
    
    return {
        "my_tasks_count": my_tasks,
        "leave_balance": leave_balance,
        "hours_this_month": round(total_hours, 1),
        "my_projects_count": my_projects,
    }


def _get_client_stats(db: Session, user: User) -> Dict[str, Any]:
    """Stats for Client role."""
    # Find client record linked to this user
    client = db.query(Client).filter(Client.email == user.email).first()
    
    if not client:
        return {
            "my_projects_count": 0,
            "open_invoices_count": 0,
            "active_tasks_count": 0,
            "total_spent": 0,
        }
    
    # Projects for this client
    my_projects = db.query(Project).filter(
        Project.client_id == client.id,
        Project.status.in_(["active", "in_progress"])
    ).count()
    
    # Open invoices (pending, sent, viewed, partial, overdue)
    open_invoices = db.query(Invoice).filter(
        Invoice.client_id == client.id,
        Invoice.status.in_([
            InvoiceStatus.SENT.value, 
            InvoiceStatus.VIEWED.value, 
            InvoiceStatus.PARTIAL.value, 
            InvoiceStatus.OVERDUE.value,
            "pending" # Handle legacy "pending" if exists
        ])
    ).count()
    
    # Active tasks in client's projects
    active_tasks = db.query(Task).join(Project).filter(
        Project.client_id == client.id,
        Task.status.in_(["todo", "in_progress"])
    ).count()
    
    # Total spent (sum of paid invoices)
    total_spent = db.query(func.sum(Invoice.total)).filter(
        Invoice.client_id == client.id,
        Invoice.status == InvoiceStatus.PAID.value
    ).scalar() or 0
    
    return {
        "my_projects_count": my_projects,
        "open_invoices_count": open_invoices,
        "active_tasks_count": active_tasks,
        "total_spent": float(total_spent),
    }


@router.get("/recent-activity")
def get_recent_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = 10,
) -> Any:
    """
    Get recent activity for the dashboard.
    Returns role-based recent activities.
    """
    role_code = current_user.role.code if current_user.role else "EMPLOYEE"
    
    activities = []
    
    employee = current_user.employee if role_code != "SUPER_ADMIN" else None
    
    # Get recent projects
    project_query = db.query(Project)
    
    if role_code == "ADMIN":
        project_query = project_query.filter(Project.company_id == current_user.company_id)
    elif role_code == "MANAGER" and employee:
        project_query = project_query.filter(
            or_(
                Project.manager_id == employee.id,
                Project.members.any(ProjectMember.employee_id == employee.id)
            )
        )
    elif role_code == "CLIENT":
        client = db.query(Client).filter(Client.email == current_user.email).first()
        if client:
            project_query = project_query.filter(Project.client_id == client.id)
        else:
             project_query = project_query.filter(Project.id == -1) # No results
    
    # Only fetch projects if role is appropriate
    if role_code in ["SUPER_ADMIN", "ADMIN", "MANAGER", "CLIENT"]:
        recent_projects = project_query.order_by(Project.created_at.desc()).limit(5).all()
        
        for project in recent_projects:
            activities.append({
                "type": "project",
                "title": project.name,
                "description": f"Project {project.status}",
                "timestamp": project.created_at.isoformat(),
                "id": project.id,
            })
    
    # Get recent leaves (for HR and Managers)
    leave_query = db.query(Leave)
    
    if role_code == "HR" or role_code == "ADMIN":
        leave_query = leave_query.filter(Leave.employee.has(company_id=current_user.company_id))
    elif role_code == "MANAGER" and employee:
        # Leaves of team members
        leave_query = leave_query.filter(Leave.employee.has(manager_id=employee.id))
    
    if role_code in ["HR", "MANAGER", "ADMIN"]:
        recent_leaves = leave_query.order_by(Leave.created_at.desc()).limit(5).all()
        
        for leave in recent_leaves:
            l_employee = leave.employee
            activities.append({
                "type": "leave",
                "title": f"{l_employee.first_name} {l_employee.last_name} - Leave Request",
                "description": f"{leave.leave_type.name if leave.leave_type else 'Leave'} - {leave.status}",
                "timestamp": leave.created_at.isoformat(),
                "id": leave.id,
            })
            
    # Employee/Client might see their own activity?
    if role_code == "EMPLOYEE" and employee:
        # Your recent tasks
        recent_tasks = db.query(Task).filter(
             Task.assignee_id == employee.id
        ).order_by(Task.updated_at.desc()).limit(5).all()
        
        for task in recent_tasks:
             activities.append({
                "type": "task",
                "title": task.title,
                "description": f"Task {task.status}",
                "timestamp": task.updated_at.isoformat() if task.updated_at else task.created_at.isoformat(),
                "id": task.id,
            })
    
    # Sort by timestamp and limit
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return activities[:limit]


@router.get("/quick-actions")
def get_quick_actions(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get role-based quick actions for the dashboard.
    """
    role_code = current_user.role.code if current_user.role else "EMPLOYEE"
    
    actions_map = {
        "SUPER_ADMIN": [
            {"label": "Add Company", "href": "/companies/new", "icon": "HiOutlinePlus", "color": "blue"},
            {"label": "Manage Roles", "href": "/roles", "icon": "HiOutlineShieldCheck", "color": "purple"},
            {"label": "View Users", "href": "/users", "icon": "HiOutlineUsers", "color": "green"},
            {"label": "System Settings", "href": "/settings", "icon": "HiOutlineCog", "color": "gray"},
        ],
        "ADMIN": [
            {"label": "Add Employee", "href": "/employees/new", "icon": "HiOutlinePlus", "color": "blue"},
            {"label": "Create Project", "href": "/projects/new", "icon": "HiOutlineFolder", "color": "violet"},
            {"label": "View Reports", "href": "/reports", "icon": "HiOutlineChartBar", "color": "emerald"},
            {"label": "Manage Departments", "href": "/departments", "icon": "HiOutlineOfficeBuilding", "color": "orange"},
        ],
        "MANAGER": [
            {"label": "Create Project", "href": "/projects/new", "icon": "HiOutlineFolder", "color": "violet"},
            {"label": "Assign Task", "href": "/tasks", "icon": "HiOutlineClipboardCheck", "color": "blue"},
            {"label": "Approve Leaves", "href": "/leaves", "icon": "HiOutlineCalendar", "color": "emerald"},
            {"label": "Team Reports", "href": "/reports", "icon": "HiOutlineChartBar", "color": "orange"},
        ],
        "HR": [
            {"label": "Add Employee", "href": "/employees/new", "icon": "HiOutlineUserAdd", "color": "blue"},
            {"label": "Approve Leave", "href": "/leaves", "icon": "HiOutlineCalendar", "color": "emerald"},
            {"label": "View Attendance", "href": "/attendance", "icon": "HiOutlineClock", "color": "violet"},
            {"label": "Payroll Reports", "href": "/reports", "icon": "HiOutlineCurrencyDollar", "color": "amber"},
        ],
        "EMPLOYEE": [
            {"label": "Mark Attendance", "href": "/attendance", "icon": "HiOutlineClock", "color": "blue"},
            {"label": "Apply Leave", "href": "/leaves/apply", "icon": "HiOutlineCalendar", "color": "emerald"},
            {"label": "My Tasks", "href": "/tasks", "icon": "HiOutlineClipboardCheck", "color": "violet"},
            {"label": "My Projects", "href": "/projects", "icon": "HiOutlineFolder", "color": "orange"},
        ],
        "CLIENT": [
            {"label": "View Projects", "href": "/projects", "icon": "HiOutlineFolder", "color": "violet"},
            {"label": "View Invoices", "href": "/invoices", "icon": "HiOutlineCurrencyDollar", "color": "amber"},
            {"label": "My Tasks", "href": "/tasks", "icon": "HiOutlineClipboardCheck", "color": "blue"},
            {"label": "Support", "href": "/support", "icon": "HiOutlineSupport", "color": "emerald"},
        ],
    }
    
    return actions_map.get(role_code, actions_map["EMPLOYEE"])
