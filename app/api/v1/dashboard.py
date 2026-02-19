"""
Dashboard API endpoints.
Provides role-based dashboard statistics and data.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db

from alembic import command
from alembic.config import Config
from app.models.attendance import Attendance
from app.models.auth import User
from app.models.client import Client
from app.models.company import Company
from app.models.employee import Employee
from app.models.invoice import Invoice, InvoiceStatus
from app.models.leave import Leave, LeaveBalance
from app.models.organization import Department
from app.models.project import Project, ProjectMember, Task, TaskStatus

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _find_client_for_user(db: Session, user: User):
    """Find CRM Client record for a user — try user_id first, then email."""
    client = db.query(Client).filter(Client.user_id == user.id).first()
    if not client and user.email:
        client = db.query(Client).filter(Client.email == user.email).first()
    return client


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


@router.get("/my-portal")
def get_my_portal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get client portal data for the currently logged-in user.
    Matches user by user_id first, then email to a Client record.
    Returns profile data + computed stats (modules, projects, tasks, invoices).
    """
    from fastapi import HTTPException
    from app.models.client_module import ClientModule

    client = _find_client_for_user(db, current_user)

    if not client:
        raise HTTPException(status_code=404, detail="No client profile found for your account.")

    # Computed stats
    modules_count = db.query(ClientModule).filter(
        ClientModule.client_id == client.id,
        ClientModule.is_deleted == False,
    ).count()

    my_projects = db.query(Project).filter(
        Project.client_id == client.id,
        Project.status.in_(["active", "in_progress"]),
    ).count()

    active_tasks = db.query(Task).join(Project).filter(
        Project.client_id == client.id,
        Task.status.in_(["todo", "in_progress"]),
    ).count()

    open_invoices = db.query(Invoice).filter(
        Invoice.client_id == client.id,
        Invoice.status.in_([
            InvoiceStatus.SENT.value,
            InvoiceStatus.VIEWED.value,
            InvoiceStatus.PARTIAL.value,
            InvoiceStatus.OVERDUE.value,
            "pending",
        ]),
    ).count()

    total_spent = db.query(func.sum(Invoice.total)).filter(
        Invoice.client_id == client.id,
        Invoice.status == InvoiceStatus.PAID.value,
    ).scalar() or 0

    return {
        "client_id": client.id,
        "name": client.name,
        "slug": client.slug,
        "code": client.code,
        "email": client.email,
        "phone": client.phone,
        "company_name": client.company_name,
        "industry": client.industry,
        "website": client.website,
        "address": client.address,
        "city": client.city,
        "state": client.state,
        "country": client.country,
        "status": client.status,
        # Computed stats
        "modules_count": modules_count,
        "projects_count": my_projects,
        "active_tasks_count": active_tasks,
        "open_invoices_count": open_invoices,
        "total_spent": float(total_spent),
    }


@router.get("/project-overview")
def get_project_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get project overview statistics for Projects page.
    Optimized: uses SQL GROUP BY instead of fetching all rows.
    """
    base_filter = [Project.is_deleted == False]

    # If client, filter by client
    if current_user.role and current_user.role.code == "CLIENT":
        client = _find_client_for_user(db, current_user)
        if client:
            base_filter.append(Project.client_id == client.id)
        else:
            return {"total": 0, "by_status": {}}

    # Use SQL GROUP BY for counting — much faster than fetching all rows
    status_rows = db.query(
        Project.status, func.count(Project.id)
    ).filter(*base_filter).group_by(Project.status).all()

    status_counts = {status: count for status, count in status_rows}
    total = sum(status_counts.values())

    return {
        "total": total,
        "by_status": status_counts
    }


def _get_super_admin_stats(db: Session) -> dict[str, Any]:
    """Stats for Super Admin role."""
    total_companies = db.query(Company).filter(Company.is_active == True).count()
    total_users = db.query(User).filter(User.is_active == True).count()
    total_employees = db.query(Employee).count()
    active_projects = db.query(Project).filter(Project.status.in_(["active", "in_progress"])).count()

    # System health check (DB connection)
    try:
        db.execute(text("SELECT 1"))
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


def _get_admin_stats(db: Session, user: User) -> dict[str, Any]:
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


def _get_manager_stats(db: Session, user: User) -> dict[str, Any]:
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


def _get_hr_stats(db: Session, user: User) -> dict[str, Any]:
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

    # New hires this month
    first_day_of_month = datetime.now().replace(day=1)
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


def _get_employee_stats(db: Session, user: User) -> dict[str, Any]:
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


def _get_client_stats(db: Session, user: User) -> dict[str, Any]:
    """Stats for Client role."""
    # Find client record linked to this user
    client = _find_client_for_user(db, user)

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
        client = _find_client_for_user(db, current_user)
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


@router.get("/charts")
def get_dashboard_charts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get role-based dashboard charts data.
    """
    role_code = current_user.role.code if current_user.role else "EMPLOYEE"

    # Common Date Range (Last 6 Months)
    today = datetime.now()
    six_months_ago = today - timedelta(days=180)

    charts = {}

    # --- ADMIN / SUPER ADMIN ---
    if role_code in ["SUPER_ADMIN", "ADMIN"]:
        # 1. Project Distribution
        project_query = db.query(Project.status, func.count(Project.id)).filter(
            Project.is_deleted == False
        )
        if role_code == "ADMIN":
            project_query = project_query.filter(Project.company_id == current_user.company_id)

        project_dist = project_query.group_by(Project.status).all()
        charts["project_distribution"] = [
            {"name": status.replace("_", " ").title(), "value": count} 
            for status, count in project_dist
        ]

        # 2. Revenue Trend (Invoices Paid)
        invoice_query = db.query(Invoice).filter(
            Invoice.status == InvoiceStatus.PAID.value,
            Invoice.updated_at >= six_months_ago
            # Note: you might want to use paid_at if available
        )
        if role_code == "ADMIN":
            invoice_query = invoice_query.filter(Invoice.company_id == current_user.company_id)

        invoices = invoice_query.all()

        # Aggregate by Month
        revenue_map = {}
        for i in range(6):
            # i=0 is current month
            # i=5 is 5 months ago
            date = today - timedelta(days=30 * i)
            key = date.strftime("%b")
            revenue_map[key] = 0

        # Initialize map with zero (reversed order for display)
        # We need keys in chronological order
        chronological_keys = []
        for i in range(5, -1, -1):
             dt = today - timedelta(days=30 * i)
             k = dt.strftime("%b")
             chronological_keys.append(k)
             revenue_map[k] = 0 # Ensure key exists

        for inv in invoices:
            if inv.updated_at:
                date_key = inv.updated_at.strftime("%b")
                if date_key in revenue_map:
                    revenue_map[date_key] += inv.total

        charts["revenue_trend"] = [
            {"name": k, "value": revenue_map[k]} for k in chronological_keys
        ]

    # --- CLIENT ---
    elif role_code == "CLIENT":
        client = _find_client_for_user(db, current_user)
        if client:
            # 1. Spending Trend
            invoices = db.query(Invoice).filter(
                Invoice.client_id == client.id,
                Invoice.status == InvoiceStatus.PAID.value,
                Invoice.updated_at >= six_months_ago
            ).all()

            # Initialize map
            spending_map = {}
            chronological_keys = []
            for i in range(5, -1, -1):
                 dt = today - timedelta(days=30 * i)
                 k = dt.strftime("%b")
                 chronological_keys.append(k)
                 spending_map[k] = 0

            for inv in invoices:
                if inv.updated_at:
                    k = inv.updated_at.strftime("%b")
                    if k in spending_map:
                        spending_map[k] += inv.total

            charts["spending_trend"] = [
                {"name": k, "value": spending_map[k]} for k in chronological_keys
            ]

            # 2. Project Status
            proj_dist = db.query(Project.status, func.count(Project.id)).filter(
                Project.client_id == client.id,
                Project.is_deleted == False
            ).group_by(Project.status).all()

            charts["project_status"] = [
                {"name": s.replace("_", " ").title(), "value": c} for s, c in proj_dist
            ]

    # --- EMPLOYEE / MANAGER ---
    elif role_code in ["EMPLOYEE", "MANAGER"]:
        employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if employee:
             # 1. Task Completion (Last 7 Days)
             week_ago = today - timedelta(days=7)

             tasks_query = db.query(Task).filter(
                 Task.status == TaskStatus.DONE.value,
                 Task.updated_at >= week_ago
             )

             if role_code == "MANAGER":
                 # Team tasks
                 tasks_query = tasks_query.filter(Task.assignee.has(Employee.manager_id == employee.id))
             else:
                 # My tasks
                 tasks_query = tasks_query.filter(Task.assignee_id == employee.id)

             completed_tasks = tasks_query.all()

             # Daily aggregation
             daily_map = {}
             chronological_keys = []
             for i in range(6, -1, -1):
                 dt = today - timedelta(days=i)
                 # e.g. "Mon"
                 key = dt.strftime("%a")
                 chronological_keys.append(key)
                 daily_map[key] = 0

             for t in completed_tasks:
                 if t.updated_at:
                     k = t.updated_at.strftime("%a")
                     if k in daily_map:
                         daily_map[k] += 1

             charts["task_completion"] = [
                 {"name": k, "value": daily_map[k]} for k in chronological_keys
             ]

    # --- HR ---
    elif role_code == "HR":
        company_id = current_user.company_id

        # 1. Recruitment Trend (New Hires)
        new_hires_query = db.query(Employee).filter(
            Employee.company_id == company_id,
            Employee.joining_date >= six_months_ago.date()
        ).all()

        hiring_map = {}
        chronological_keys = []
        for i in range(5, -1, -1):
             dt = today - timedelta(days=30 * i)
             k = dt.strftime("%b")
             chronological_keys.append(k)
             hiring_map[k] = 0

        for emp in new_hires_query:
            if emp.joining_date:
                # Convert date to datetime for strftime if needed, or just use date directly
                # emp.joining_date is likely date object
                k = emp.joining_date.strftime("%b")
                if k in hiring_map:
                    hiring_map[k] += 1

        charts["recruitment_trend"] = [
            {"name": k, "value": hiring_map[k]} for k in chronological_keys
        ]

        # 2. Leave Trend (Approved Leaves)
        leaves_query = db.query(Leave).filter(
            Leave.company_id == company_id,
            Leave.status == "approved",
            Leave.start_date >= six_months_ago.date()
        ).all()

        leave_map = {}
        for k in chronological_keys:
            leave_map[k] = 0

        for leave in leaves_query:
            if leave.start_date:
                k = leave.start_date.strftime("%b")
                if k in leave_map:
                    leave_map[k] += 1

        charts["leave_trend"] = [
            {"name": k, "value": leave_map[k]} for k in chronological_keys
        ]

    return charts


@router.post("/migrate")
def run_db_migration(
    current_user: User = Depends(get_current_active_user),
):
    """
    Run database migrations programmatically.
    Use this to fix 500 errors on live server if shell access is unavailable.
    """
    if current_user.role.code != "SUPER_ADMIN":
        return {"status": "error", "message": "Unauthorized"}

    try:
        import os
        cwd = os.getcwd()
        ini_path = os.path.join(cwd, "alembic.ini")

        # If not in CWD, look in parent directory (in case CWD is app/)
        if not os.path.exists(ini_path):
             parent = os.path.dirname(cwd)
             ini_path_parent = os.path.join(parent, "alembic.ini")
             if os.path.exists(ini_path_parent):
                 ini_path = ini_path_parent
                 # We might need to change CWD for alembic to find 'migrations' folder relative to ini
                 os.chdir(parent)
             else:
                 return {
                     "status": "error", 
                     "message": f"alembic.ini not found in {cwd} or parent. Files in {cwd}: {os.listdir(cwd)}"
                 }

        # Assuming alembic.ini is in the root of the backend folder (CWD)
        alembic_cfg = Config(ini_path)
        command.upgrade(alembic_cfg, "head")
        return {"status": "success", "message": "Database migration applied successfully."}
    except Exception as e:
        return {"status": "error", "message": f"Error: {str(e)} | CWD: {os.getcwd()}"}

