from app.services.email_service import (
    email_service,
    generic_notification_email,
    get_base_template,
    leave_request_email,
    task_assigned_email,
    welcome_email_content,
)


def test_email_service_builds_live_admin_urls():
    assert email_service.build_app_url("/login") == "https://admin.ayatiworks.com/login"
    assert email_service.build_app_url("projects/1") == "https://admin.ayatiworks.com/projects/1"


def test_welcome_email_uses_live_login_url():
    html = welcome_email_content(
        name="Test User",
        email="test@example.com",
        temp_password="TempPass123!",
    )

    assert "https://admin.ayatiworks.com/login" in html


def test_notification_helpers_use_live_urls():
    _, notification_html = generic_notification_email(
        recipient_name="Test User",
        title="Test Notification",
        message="Please review this item.",
        action_url="/notifications",
    )
    _, task_html = task_assigned_email(
        assignee_name="Test User",
        task_title="Prepare Report",
        project_name="Operations",
        assigned_by="Manager",
        priority="high",
    )
    _, leave_html = leave_request_email(
        manager_name="Manager",
        employee_name="Test User",
        leave_type="Casual",
        start_date="2026-06-03",
        end_date="2026-06-04",
        days=2,
    )

    assert "https://admin.ayatiworks.com/notifications" in notification_html
    assert "https://admin.ayatiworks.com/tasks" in task_html
    assert "https://admin.ayatiworks.com/leaves" in leave_html


def test_base_template_wraps_custom_event_content():
    html = get_base_template("Custom Event", "<p>Event body</p>")

    assert "Custom Event" in html
    assert "Event body" in html
