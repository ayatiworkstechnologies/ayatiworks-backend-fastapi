"""
Notification service.
Creates in-app notifications and optionally sends emails.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.auth import User
from app.services.email_service import email_service, generic_notification_email
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for creating and managing notifications."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: str = "info",
        category: Optional[str] = None,
        link: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        send_email: bool = False
    ) -> Notification:
        """
        Create a notification for a user.
        
        Args:
            user_id: Target user ID
            title: Notification title
            message: Notification message
            notification_type: Type (info, success, warning, error)
            category: Category (leave, attendance, task, etc.)
            link: URL link for the notification
            entity_type: Related entity type
            entity_id: Related entity ID
            send_email: Whether to also send an email
            
        Returns:
            Created Notification object
        """
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            category=category,
            link=link,
            entity_type=entity_type,
            entity_id=entity_id
        )
        
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        
        # Send email if requested
        if send_email:
            self._send_notification_email(user_id, title, message, link)
        
        return notification
    
    def _send_notification_email(self, user_id: int, title: str, message: str, link: Optional[str] = None):
        """Send email notification to user."""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if user and user.email:
                subject, html_content = generic_notification_email(
                    recipient_name=user.first_name or "User",
                    title=title,
                    message=message,
                    action_url=link
                )
                email_service.send_email(
                    to_email=user.email,
                    subject=subject,
                    html_content=html_content
                )
        except Exception as e:
            logger.error(f"Failed to send notification email: {e}")
    
    def notify_employee_created(self, employee, created_by_name: str):
        """Send notification when employee is created."""
        if employee.manager_id:
            # Notify manager about new team member
            self.create(
                user_id=employee.manager.user_id if employee.manager else None,
                title="New Team Member Added",
                message=f"{employee.user.first_name} {employee.user.last_name or ''} has joined your team as {employee.designation.name if employee.designation else 'Employee'}.",
                notification_type="info",
                category="employee",
                entity_type="employee",
                entity_id=employee.id,
                send_email=True
            ) if employee.manager else None
    
    def notify_task_assigned(
        self,
        assignee_user_id: int,
        task_title: str,
        project_name: str,
        assigned_by: str,
        priority: str,
        task_id: int,
        due_date: Optional[str] = None
    ):
        """Send notification when task is assigned."""
        from app.services.email_service import task_assigned_email
        
        # Create in-app notification
        notification = self.create(
            user_id=assignee_user_id,
            title=f"New Task: {task_title}",
            message=f"You have been assigned a {priority} priority task on {project_name} by {assigned_by}.",
            notification_type="info",
            category="task",
            entity_type="task",
            entity_id=task_id,
            send_email=False  # We'll send custom email
        )
        
        # Send custom task email
        try:
            user = self.db.query(User).filter(User.id == assignee_user_id).first()
            if user:
                subject, html_content = task_assigned_email(
                    assignee_name=user.first_name or "User",
                    task_title=task_title,
                    project_name=project_name,
                    assigned_by=assigned_by,
                    priority=priority,
                    due_date=due_date
                )
                email_service.send_email(
                    to_email=user.email,
                    subject=subject,
                    html_content=html_content
                )
        except Exception as e:
            logger.error(f"Failed to send task assignment email: {e}")
        
        return notification
    
    def notify_leave_request(
        self,
        manager_user_id: int,
        employee_name: str,
        leave_type: str,
        start_date: str,
        end_date: str,
        days: int,
        leave_id: int,
        reason: Optional[str] = None
    ):
        """Send notification for leave request."""
        from app.services.email_service import leave_request_email
        
        # Create in-app notification
        notification = self.create(
            user_id=manager_user_id,
            title=f"Leave Request from {employee_name}",
            message=f"{employee_name} has requested {days} day(s) of {leave_type} leave from {start_date} to {end_date}.",
            notification_type="warning",
            category="leave",
            entity_type="leave",
            entity_id=leave_id,
            send_email=False
        )
        
        # Send custom email
        try:
            manager = self.db.query(User).filter(User.id == manager_user_id).first()
            if manager:
                subject, html_content = leave_request_email(
                    manager_name=manager.first_name or "Manager",
                    employee_name=employee_name,
                    leave_type=leave_type,
                    start_date=start_date,
                    end_date=end_date,
                    days=days,
                    reason=reason
                )
                email_service.send_email(
                    to_email=manager.email,
                    subject=subject,
                    html_content=html_content
                )
        except Exception as e:
            logger.error(f"Failed to send leave request email: {e}")
        
        return notification
    
    def notify_leave_status(
        self,
        employee_user_id: int,
        leave_type: str,
        start_date: str,
        end_date: str,
        status: str,
        leave_id: int,
        approved_by: Optional[str] = None,
        remarks: Optional[str] = None
    ):
        """Send notification for leave status update."""
        from app.services.email_service import leave_status_email
        
        status_type = "success" if status.lower() == "approved" else "error"
        
        # Create in-app notification
        notification = self.create(
            user_id=employee_user_id,
            title=f"Leave {status.capitalize()}",
            message=f"Your {leave_type} leave request ({start_date} to {end_date}) has been {status.lower()}.",
            notification_type=status_type,
            category="leave",
            entity_type="leave",
            entity_id=leave_id,
            send_email=False
        )
        
        # Send email
        try:
            user = self.db.query(User).filter(User.id == employee_user_id).first()
            if user:
                subject, html_content = leave_status_email(
                    employee_name=user.first_name or "Employee",
                    leave_type=leave_type,
                    start_date=start_date,
                    end_date=end_date,
                    status=status,
                    approved_by=approved_by,
                    remarks=remarks
                )
                email_service.send_email(
                    to_email=user.email,
                    subject=subject,
                    html_content=html_content
                )
        except Exception as e:
            logger.error(f"Failed to send leave status email: {e}")
        
        return notification
    
    def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        """Mark a notification as read."""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if notification:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            self.db.commit()
            return True
        return False
    
    def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user."""
        result = self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update({
            "is_read": True,
            "read_at": datetime.utcnow()
        })
        self.db.commit()
        return result
    
    def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications."""
        return self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()
