"""
Cleanup background tasks.
"""

from datetime import datetime

from celery import shared_task


@shared_task
def cleanup_expired_sessions():
    """Delete expired or invalidated user sessions."""
    from app.database import SessionLocal
    from app.models.auth import UserSession

    db = SessionLocal()
    try:
        deleted = db.query(UserSession).filter(
            (UserSession.is_valid == False) | (UserSession.expires_at <= datetime.utcnow())
        ).delete(synchronize_session=False)
        db.commit()
        return {"deleted_sessions": deleted}
    finally:
        db.close()
