"""
Celery application configuration.
Background task processing for emails, reports, and heavy operations.
"""

from celery import Celery

from app.config import settings

# Get Redis URL or use default
REDIS_URL = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')

# Create Celery app
celery_app = Celery(
    'enterprise_hrms',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        'app.tasks.email_tasks',
        'app.tasks.report_tasks',
        'app.tasks.notification_tasks',
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result settings
    result_expires=3600,  # Results expire after 1 hour
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Rate limiting
    task_default_rate_limit='100/m',
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Task routes
    task_routes={
        'app.tasks.email_tasks.*': {'queue': 'email'},
        'app.tasks.report_tasks.*': {'queue': 'reports'},
        'app.tasks.notification_tasks.*': {'queue': 'notifications'},
    },
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        # Daily attendance report
        'generate-daily-attendance-report': {
            'task': 'app.tasks.report_tasks.generate_daily_attendance_report',
            'schedule': 3600.0 * 24,  # Every 24 hours
        },
        # Clear old sessions
        'cleanup-expired-sessions': {
            'task': 'app.tasks.cleanup_tasks.cleanup_expired_sessions',
            'schedule': 3600.0 * 6,  # Every 6 hours
        },
    },
)


# Optional: configure for Windows
import platform
if platform.system() == 'Windows':
    celery_app.conf.update(
        worker_pool='solo',  # Use solo pool on Windows
    )
