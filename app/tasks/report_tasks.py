"""
Report generation background tasks.
Generate heavy reports asynchronously.
"""

from celery import shared_task
from datetime import date, datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def generate_daily_attendance_report(self, company_id: int = None, report_date: str = None):
    """
    Generate daily attendance report.
    Scheduled to run daily.
    """
    try:
        from app.database import SessionLocal
        from app.models.attendance import Attendance
        from app.models.employee import Employee
        from sqlalchemy import func
        
        if report_date:
            target_date = datetime.strptime(report_date, "%Y-%m-%d").date()
        else:
            target_date = date.today() - timedelta(days=1)  # Yesterday
        
        db = SessionLocal()
        try:
            query = db.query(Attendance).filter(Attendance.date == target_date)
            
            if company_id:
                query = query.join(Employee).filter(Employee.company_id == company_id)
            
            attendances = query.all()
            
            # Calculate statistics
            stats = {
                "date": str(target_date),
                "total_records": len(attendances),
                "present": sum(1 for a in attendances if a.status == "present"),
                "late": sum(1 for a in attendances if a.is_late),
                "early_leave": sum(1 for a in attendances if a.is_early_leave),
                "wfh": sum(1 for a in attendances if a.work_mode == "wfh"),
                "total_hours": sum((a.working_hours or 0) for a in attendances),
                "overtime_hours": sum((a.overtime_hours or 0) for a in attendances),
            }
            
            logger.info(f"Daily attendance report generated: {stats}")
            return stats
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to generate attendance report: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True)
def generate_leave_balance_report(self, company_id: int, year: int = None):
    """
    Generate leave balance report for all employees.
    """
    try:
        from app.database import SessionLocal
        from app.models.employee import Employee
        from app.services.leave_service import LeaveService
        
        if year is None:
            year = date.today().year
        
        db = SessionLocal()
        try:
            employees = db.query(Employee).filter(
                Employee.company_id == company_id,
                Employee.employment_status == "active",
                Employee.is_deleted == False
            ).all()
            
            report = []
            leave_service = LeaveService(db)
            
            for emp in employees:
                balances = leave_service.get_all_balances(emp.id, year)
                report.append({
                    "employee_id": emp.id,
                    "employee_code": emp.employee_code,
                    "name": f"{emp.first_name} {emp.last_name or ''}",
                    "department": emp.department.name if emp.department else None,
                    "balances": balances
                })
            
            logger.info(f"Leave balance report generated for {len(report)} employees")
            return {"year": year, "employees": len(report), "data": report}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to generate leave report: {e}")
        raise


@shared_task(bind=True)
def generate_project_summary_report(self, project_id: int):
    """
    Generate project summary report.
    """
    try:
        from app.database import SessionLocal
        from app.models.project import Project, Task
        from app.models.sprint import TimeEntry
        from sqlalchemy import func
        
        db = SessionLocal()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {"error": "Project not found"}
            
            # Task statistics
            tasks = db.query(Task).filter(
                Task.project_id == project_id,
                Task.is_deleted == False
            ).all()
            
            task_stats = {
                "total": len(tasks),
                "todo": sum(1 for t in tasks if t.status == "todo"),
                "in_progress": sum(1 for t in tasks if t.status == "in_progress"),
                "in_review": sum(1 for t in tasks if t.status == "in_review"),
                "done": sum(1 for t in tasks if t.status == "done"),
            }
            
            # Time entries
            time_entries = db.query(
                func.sum(TimeEntry.hours)
            ).filter(TimeEntry.project_id == project_id).scalar() or 0
            
            report = {
                "project_id": project_id,
                "project_name": project.name,
                "status": project.status,
                "progress": project.progress,
                "task_stats": task_stats,
                "total_hours_logged": float(time_entries),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Project report generated for {project.name}")
            return report
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to generate project report: {e}")
        raise
