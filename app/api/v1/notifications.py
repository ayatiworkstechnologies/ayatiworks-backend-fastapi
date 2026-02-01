"""
Notifications API routes.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import PermissionChecker, get_current_active_user
from app.core.exceptions import ResourceNotFoundError
from app.database import get_db
from app.models.auth import User
from app.models.notification import Announcement, AnnouncementRead, Notification

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications(
    is_read: bool | None = None,
    category: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List notifications for current user."""
    query = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_deleted == False
    )

    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)

    if category:
        query = query.filter(Notification.category == category)

    total = query.count()
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
        Notification.is_deleted == False
    ).count()

    offset = (page - 1) * page_size
    notifications = query.order_by(Notification.created_at.desc()).offset(offset).limit(page_size).all()

    return {
        "items": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "category": n.category,
                "link": n.link,
                "is_read": n.is_read,
                "created_at": n.created_at
            }
            for n in notifications
        ],
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "page_size": page_size
    }


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark notification as read."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notification:
        raise ResourceNotFoundError("Notification", notification_id)

    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()

    return {"message": "Marked as read"}


@router.post("/read-all")
async def mark_all_as_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True, "read_at": datetime.utcnow()})

    db.commit()

    return {"message": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a notification."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notification:
        raise ResourceNotFoundError("Notification", notification_id)

    notification.is_deleted = True
    db.commit()

    return {"message": "Notification deleted"}


# ============== Announcements ==============

@router.get("/announcements")
async def list_announcements(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List active announcements for current user."""
    now = datetime.utcnow()

    query = db.query(Announcement).filter(
        Announcement.status == "published",
        Announcement.is_deleted == False
    )

    # Filter by date
    query = query.filter(
        (Announcement.start_date is None) | (Announcement.start_date <= now)
    ).filter(
        (Announcement.end_date is None) | (Announcement.end_date >= now)
    )

    # Filter by scope
    query = query.filter(
        (Announcement.target_scope == "all") |
        ((Announcement.target_scope == "company") & (Announcement.company_id == current_user.company_id))
    )

    announcements = query.order_by(
        Announcement.is_pinned.desc(),
        Announcement.published_at.desc()
    ).limit(20).all()

    # Get read status
    read_ids = {
        r.announcement_id for r in db.query(AnnouncementRead).filter(
            AnnouncementRead.user_id == current_user.id
        ).all()
    }

    return [
        {
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "priority": a.priority,
            "is_pinned": a.is_pinned,
            "is_read": a.id in read_ids,
            "published_at": a.published_at
        }
        for a in announcements
    ]


@router.post("/announcements/{announcement_id}/read")
async def mark_announcement_read(
    announcement_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark announcement as read."""
    existing = db.query(AnnouncementRead).filter(
        AnnouncementRead.announcement_id == announcement_id,
        AnnouncementRead.user_id == current_user.id
    ).first()

    if not existing:
        read = AnnouncementRead(
            announcement_id=announcement_id,
            user_id=current_user.id
        )
        db.add(read)
        db.commit()

    return {"message": "Marked as read"}


@router.post("/announcements", status_code=status.HTTP_201_CREATED)
async def create_announcement(
    title: str,
    content: str,
    priority: str = "normal",
    target_scope: str = "all",
    is_pinned: bool = False,
    current_user: User = Depends(PermissionChecker("announcement.create")),
    db: Session = Depends(get_db)
):
    """Create a new announcement."""
    announcement = Announcement(
        title=title,
        content=content,
        priority=priority,
        target_scope=target_scope,
        company_id=current_user.company_id,
        is_pinned=is_pinned,
        status="published",
        published_at=datetime.utcnow(),
        created_by=current_user.id
    )

    db.add(announcement)
    db.commit()
    db.refresh(announcement)

    return {"id": announcement.id, "message": "Announcement created"}

