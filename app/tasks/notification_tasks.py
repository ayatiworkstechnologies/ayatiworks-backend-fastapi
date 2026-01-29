"""
Notification background tasks.
"""

from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def create_notification_async(
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "info",
    category: str = None,
    link: str = None,
    send_email: bool = False
):
    """
    Create notification asynchronously.
    """
    try:
        from app.database import SessionLocal
        from app.services.notification_service import NotificationService
        
        db = SessionLocal()
        try:
            notification_service = NotificationService(db)
            notification = notification_service.create(
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                category=category,
                link=link,
                send_email=send_email
            )
            
            return {"status": "created", "notification_id": notification.id}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def notify_team_async(
    team_id: int,
    title: str,
    message: str,
    notification_type: str = "info",
    exclude_user_id: int = None
):
    """
    Send notification to all team members.
    """
    try:
        from app.database import SessionLocal
        from app.models.team import TeamMember
        from app.services.notification_service import NotificationService
        
        db = SessionLocal()
        try:
            members = db.query(TeamMember).filter(
                TeamMember.team_id == team_id,
                TeamMember.is_deleted == False
            ).all()
            
            notification_service = NotificationService(db)
            count = 0
            
            for member in members:
                if member.employee and member.employee.user_id:
                    if exclude_user_id and member.employee.user_id == exclude_user_id:
                        continue
                    
                    notification_service.create(
                        user_id=member.employee.user_id,
                        title=title,
                        message=message,
                        notification_type=notification_type,
                        category="team"
                    )
                    count += 1
            
            return {"status": "sent", "count": count}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to notify team: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def send_deadline_reminders():
    """
    Send reminders for upcoming task deadlines.
    Scheduled to run daily.
    """
    try:
        from app.database import SessionLocal
        from app.models.project import Task
        from app.services.notification_service import NotificationService
        from datetime import date, timedelta
        
        db = SessionLocal()
        try:
            # Tasks due in next 2 days
            upcoming_date = date.today() + timedelta(days=2)
            
            tasks = db.query(Task).filter(
                Task.due_date <= upcoming_date,
                Task.due_date >= date.today(),
                Task.status.notin_(["done", "cancelled"]),
                Task.is_deleted == False
            ).all()
            
            notification_service = NotificationService(db)
            count = 0
            
            for task in tasks:
                if task.assignee and task.assignee.user_id:
                    days_left = (task.due_date - date.today()).days
                    
                    notification_service.create(
                        user_id=task.assignee.user_id,
                        title=f"Task Due {'Tomorrow' if days_left == 1 else 'Soon'}",
                        message=f"'{task.title}' is due in {days_left} day(s)",
                        notification_type="warning",
                        category="task",
                        link=f"/tasks/{task.id}"
                    )
                    count += 1
            
            logger.info(f"Sent {count} deadline reminders")
            return {"status": "complete", "reminders_sent": count}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to send deadline reminders: {e}")
        return {"status": "failed", "error": str(e)}
