"""
Email background tasks.
Send emails asynchronously to avoid blocking API requests.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_async(
    self,
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str = None
):
    """
    Send email asynchronously.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email body
        text_content: Plain text fallback
    """
    try:
        from app.services.email_service import email_service

        success = email_service.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )

        if success:
            logger.info(f"Email sent successfully to {to_email}")
            return {"status": "sent", "to": to_email}
        else:
            raise Exception("Email sending failed")

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_welcome_email_async(self, user_id: int, temp_password: str = None):
    """
    Send welcome email to new employee.
    """
    try:
        from app.database import SessionLocal
        from app.models.auth import User
        from app.services.email_service import email_service, welcome_email_content

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found for welcome email")
                return {"status": "user_not_found"}

            html_content = welcome_email_content(
                name=user.full_name,
                email=user.email,
                temp_password=temp_password
            )

            success = email_service.send_email(
                to_email=user.email,
                subject="Welcome to Enterprise HRMS",
                html_content=html_content
            )

            return {"status": "sent" if success else "failed", "user_id": user_id}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to send welcome email to user {user_id}: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3)
def send_notification_email_async(
    self,
    user_id: int,
    title: str,
    message: str,
    link: str = None
):
    """
    Send notification email to user.
    """
    try:
        from app.database import SessionLocal
        from app.models.auth import User
        from app.services.email_service import email_service, generic_notification_email

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"status": "user_not_found"}

            html_content = generic_notification_email(
                name=user.full_name,
                title=title,
                message=message,
                link=link
            )

            success = email_service.send_email(
                to_email=user.email,
                subject=title,
                html_content=html_content
            )

            return {"status": "sent" if success else "failed"}

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to send notification email: {e}")
        raise self.retry(exc=e)


@shared_task
def send_bulk_emails(
    email_list: list,
    subject: str,
    html_content: str
):
    """
    Send bulk emails (e.g., announcements).

    Args:
        email_list: List of email addresses
        subject: Email subject
        html_content: HTML content
    """
    from app.services.email_service import email_service

    results = {"sent": 0, "failed": 0, "errors": []}

    for email in email_list:
        try:
            success = email_service.send_email(
                to_email=email,
                subject=subject,
                html_content=html_content
            )
            if success:
                results["sent"] += 1
            else:
                results["failed"] += 1

        except Exception as e:
            results["failed"] += 1
            results["errors"].append({"email": email, "error": str(e)})

    logger.info(f"Bulk email complete: {results['sent']} sent, {results['failed']} failed")
    return results

