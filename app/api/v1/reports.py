"""
Reports and Dashboard API routes.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import PermissionChecker, get_current_active_user
from app.database import get_db
from app.models.attendance import Attendance
from app.models.auth import User
from app.models.employee import Employee
from app.models.leave import Leave
from app.models.project import Project, Task
from app.models.report import Report
from app.services.employee_service import EmployeeService

router = APIRouter(tags=["Reports & Dashboard"])


# ============== Dashboard Data ==============

@router.get("/dashboard/stats")
async def get_report_dashboard_stats(
    period: str = Query("month", regex="^(week|month|quarter|year)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get dashboard statistics for current user."""
    emp_service = EmployeeService(db)
    employee = emp_service.get_by_user_id(current_user.id)

    today = date.today()

    # Quick stats
    stats = {}

    if employee:
        # Today's attendance
        today_attendance = db.query(Attendance).filter(
            Attendance.employee_id == employee.id,
            Attendance.date == today
        ).first()

        stats["attendance_today"] = {
            "checked_in": today_attendance.check_in is not None if today_attendance else False,
            "checked_out": today_attendance.check_out is not None if today_attendance else False,
            "check_in_time": today_attendance.check_in if today_attendance else None,
            "check_out_time": today_attendance.check_out if today_attendance else None
        }

        # Pending leaves
        pending_leaves = db.query(Leave).filter(
            Leave.employee_id == employee.id,
            Leave.status == "pending"
        ).count()

        stats["pending_leaves"] = pending_leaves

        # My tasks
        my_tasks = db.query(Task).filter(
            Task.assignee_id == employee.id,
            Task.status.notin_(["done", "cancelled"]),
            Task.is_deleted == False
        ).count()

        stats["active_tasks"] = my_tasks

    # Team stats for managers
    if employee and employee.manager_id is None:  # If user is a manager
        team_count = db.query(Employee).filter(
            Employee.manager_id == employee.id,
            Employee.is_deleted == False
        ).count()

        stats["team_size"] = team_count

        # Pending approvals
        pending_leave_approvals = db.query(Leave).join(Employee).filter(
            Employee.manager_id == employee.id,
            Leave.status == "pending"
        ).count()

        stats["pending_approvals"] = pending_leave_approvals

    return stats


@router.get("/dashboard/attendance-overview")
async def get_attendance_overview(
    from_date: date = Query(default=None),
    to_date: date = Query(default=None),
    current_user: User = Depends(PermissionChecker("attendance.view_all")),
    db: Session = Depends(get_db)
):
    """Get attendance overview for dashboard."""
    if not from_date:
        from_date = date.today()
    if not to_date:
        to_date = date.today()

    # Get counts by status
    present = db.query(Attendance).filter(
        Attendance.date >= from_date,
        Attendance.date <= to_date,
        Attendance.status == "present"
    ).count()

    late = db.query(Attendance).filter(
        Attendance.date >= from_date,
        Attendance.date <= to_date,
        Attendance.is_late == True
    ).count()

    wfh = db.query(Attendance).filter(
        Attendance.date >= from_date,
        Attendance.date <= to_date,
        Attendance.work_mode == "wfh"
    ).count()

    total_employees = db.query(Employee).filter(
        Employee.is_deleted == False,
        Employee.is_active == True
    ).count()

    return {
        "total_employees": total_employees,
        "present": present,
        "late": late,
        "wfh": wfh,
        "absent": total_employees - present
    }


@router.get("/dashboard/project-overview")
async def get_project_overview(
    current_user: User = Depends(PermissionChecker("project.view")),
    db: Session = Depends(get_db)
):
    """Get project overview for dashboard."""
    # Count by status
    by_status = db.query(
        Project.status,
        func.count(Project.id)
    ).filter(Project.is_deleted == False).group_by(Project.status).all()

    status_counts = dict(by_status)

    # Recent projects
    recent = db.query(Project).filter(
        Project.is_deleted == False
    ).order_by(Project.created_at.desc()).limit(5).all()

    return {
        "by_status": status_counts,
        "total": sum(status_counts.values()),
        "recent": [
            {
                "id": p.id,
                "name": p.name,
                "code": p.code,
                "status": p.status,
                "progress": p.progress
            }
            for p in recent
        ]
    }


# ============== Reports ==============

@router.get("/reports")
async def list_reports(
    report_type: str | None = None,
    current_user: User = Depends(PermissionChecker("report.view")),
    db: Session = Depends(get_db)
):
    """List saved reports."""
    query = db.query(Report).filter(
        Report.is_deleted == False,
        (Report.owner_id == current_user.id) | (Report.is_public == True)
    )

    if report_type:
        query = query.filter(Report.report_type == report_type)

    reports = query.order_by(Report.name).all()

    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "report_type": r.report_type,
            "is_scheduled": r.is_scheduled,
            "owner_id": r.owner_id,
            "is_public": r.is_public
        }
        for r in reports
    ]


@router.post("/reports")
async def create_report(
    name: str,
    report_type: str,
    config: dict,
    description: str | None = None,
    chart_type: str | None = None,
    is_public: bool = False,
    current_user: User = Depends(PermissionChecker("report.create")),
    db: Session = Depends(get_db)
):
    """Create a custom report."""
    report = Report(
        name=name,
        description=description,
        report_type=report_type,
        config=config,
        chart_type=chart_type,
        owner_id=current_user.id,
        is_public=is_public,
        company_id=current_user.company_id,
        created_by=current_user.id
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return {"id": report.id, "message": "Report created"}


@router.get("/reports/attendance")
async def generate_attendance_report(
    from_date: date = Query(...),
    to_date: date = Query(...),
    department_id: int | None = None,
    employee_id: int | None = None,
    current_user: User = Depends(PermissionChecker("report.view")),
    db: Session = Depends(get_db)
):
    """Generate attendance report."""
    query = db.query(
        Attendance.employee_id,
        func.count(Attendance.id).label("total_days"),
        func.sum(func.IF(Attendance.status == "present", 1, 0)).label("present"),
        func.sum(func.IF(Attendance.is_late == True, 1, 0)).label("late"),
        func.sum(Attendance.working_hours).label("total_hours"),
        func.sum(Attendance.overtime_hours).label("overtime_hours")
    ).join(Employee).filter(
        Attendance.date >= from_date,
        Attendance.date <= to_date,
        Attendance.is_deleted == False
    )

    if department_id:
        query = query.filter(Employee.department_id == department_id)

    if employee_id:
        query = query.filter(Attendance.employee_id == employee_id)

    query = query.group_by(Attendance.employee_id)

    results = query.all()

    # Get employee details
    emp_ids = [r[0] for r in results]
    employees = {e.id: e for e in db.query(Employee).filter(Employee.id.in_(emp_ids)).all()}

    return {
        "from_date": from_date,
        "to_date": to_date,
        "data": [
            {
                "employee_id": r[0],
                "employee_code": employees[r[0]].employee_code if r[0] in employees else None,
                "employee_name": employees[r[0]].user.full_name if r[0] in employees and employees[r[0]].user else None,
                "total_days": r[1],
                "present_days": r[2] or 0,
                "late_days": r[3] or 0,
                "total_hours": round(r[4] or 0, 2),
                "overtime_hours": round(r[5] or 0, 2)
            }
            for r in results
        ]
    }


@router.get("/reports/leave")
async def generate_leave_report(
    year: int = Query(...),
    department_id: int | None = None,
    current_user: User = Depends(PermissionChecker("report.view")),
    db: Session = Depends(get_db)
):
    """Generate leave report."""
    query = db.query(
        Leave.employee_id,
        Leave.leave_type_id,
        func.sum(Leave.days).label("total_days")
    ).join(Employee).filter(
        func.year(Leave.from_date) == year,
        Leave.status == "approved",
        Leave.is_deleted == False
    )

    if department_id:
        query = query.filter(Employee.department_id == department_id)

    query = query.group_by(Leave.employee_id, Leave.leave_type_id)

    results = query.all()

    return {
        "year": year,
        "data": [
            {
                "employee_id": r[0],
                "leave_type_id": r[1],
                "total_days": float(r[2] or 0)
            }
            for r in results
        ]
    }

