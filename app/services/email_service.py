"""
Enhanced email service with Jinja2 template rendering.
Uses HTML email templates for professional, branded emails.
"""

import logging
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Enhanced email service with template rendering."""

    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME

        # Setup Jinja2 template environment
        template_dir = Path(__file__).parent.parent / 'templates'
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )

        # Default template context
        self.default_context = {
            'company_name': getattr(settings, 'COMPANY_NAME', 'Enterprise HRMS'),
            'company_address': getattr(settings, 'COMPANY_ADDRESS', ''),
            'company_website': getattr(settings, 'COMPANY_WEBSITE', ''),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', self.from_email),
            'current_year': datetime.now().year,
            'login_url': getattr(settings, 'FRONTEND_URL', 'http://localhost:3000') + '/login',
        }

    def _create_connection(self):
        """Create SMTP connection with SSL."""
        context = ssl.create_default_context()
        if self.port == 465:
            server = smtplib.SMTP_SSL(self.host, self.port, context=context)
        else:
            server = smtplib.SMTP(self.host, self.port)
            server.starttls(context=context)

        server.login(self.user, self.password)
        return server

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        """
        Render email template with context.

        Args:
            template_name: Template file name (e.g., 'email/welcome.html')
            context: Template variables

        Returns:
            Rendered HTML string
        """
        # Merge with default context
        full_context = {**self.default_context, **context}

        template = self.jinja_env.get_template(template_name)
        return template.render(**full_context)

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_content: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            plain_content: Plain text fallback (optional)
            cc: List of CC addresses (optional)
            bcc: List of BCC addresses (optional)

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email

            if cc:
                msg["Cc"] = ", ".join(cc)

            # Add plain text part
            if plain_content:
                msg.attach(MIMEText(plain_content, "plain"))

            # Add HTML part
            msg.attach(MIMEText(html_content, "html"))

            # Build recipient list
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            # Send email
            with self._create_connection() as server:
                server.sendmail(self.from_email, recipients, msg.as_string())

            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_templated_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: dict[str, Any],
        cc: list[str] | None = None,
        bcc: list[str] | None = None
    ) -> bool:
        """
        Send email using template.

        Args:
            to_email: Recipient email address
            subject: Email subject
            template_name: Template file name
            context: Template variables
            cc: CC recipients
            bcc: BCC recipients

        Returns:
            True if sent successfully
        """
        # Add recipient email to context
        context['recipient_email'] = to_email
        context['title'] = subject

        # Render template
        html_content = self.render_template(template_name, context)

        # Send email
        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            cc=cc,
            bcc=bcc
        )

    # ============== Template-based Email Methods ==============

    def send_welcome_email(
        self,
        to_email: str,
        employee_name: str,
        employee_id: str,
        temp_password: str | None = None
    ) -> bool:
        """Send welcome email to new employee."""
        context = {
            'employee_name': employee_name,
            'email': to_email,
            'employee_id': employee_id,
            'temp_password': temp_password,
        }

        return self.send_templated_email(
            to_email=to_email,
            subject=f"Welcome to {self.default_context['company_name']}!",
            template_name='email/welcome.html',
            context=context
        )

    def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_code: str,
        reset_url: str,
        expiry_minutes: int = 30
    ) -> bool:
        """Send password reset email."""
        context = {
            'user_name': user_name,
            'reset_code': reset_code,
            'reset_url': reset_url,
            'expiry_minutes': expiry_minutes,
        }

        return self.send_templated_email(
            to_email=to_email,
            subject="Password Reset Request",
            template_name='email/password_reset.html',
            context=context
        )

    def send_otp_email(
        self,
        to_email: str,
        user_name: str,
        otp_code: str,
        ip_address: str | None = None,
        device_info: str | None = None,
        expiry_minutes: int = 10
    ) -> bool:
        """Send 2FA OTP email."""
        context = {
            'user_name': user_name,
            'otp_code': otp_code,
            'expiry_minutes': expiry_minutes,
            'login_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ip_address': ip_address or 'Unknown',
            'device_info': device_info or 'Unknown device',
        }

        return self.send_templated_email(
            to_email=to_email,
            subject="Two-Factor Authentication Code",
            template_name='email/otp.html',
            context=context
        )

    def send_leave_status_email(
        self,
        to_email: str,
        employee_name: str,
        leave_type: str,
        from_date: str,
        to_date: str,
        duration: int,
        status: str,
        approver_name: str | None = None,
        approver_comments: str | None = None,
        leave_balances: list[dict] | None = None,
        reason: str | None = None
    ) -> bool:
        """Send leave status notification."""
        # Status-specific styling
        status_config = {
            'Approved': {'emoji': '✅', 'color': '#28a745'},
            'Rejected': {'emoji': '❌', 'color': '#dc3545'},
            'Pending': {'emoji': '⏳', 'color': '#ffc107'},
        }
        config = status_config.get(status, {'emoji': 'ℹ️', 'color': '#667eea'})

        context = {
            'employee_name': employee_name,
            'leave_type': leave_type,
            'from_date': from_date,
            'to_date': to_date,
            'duration': duration,
            'status': status,
            'status_emoji': config['emoji'],
            'status_color': config['color'],
            'approver_name': approver_name,
            'approver_comments': approver_comments,
            'leave_balances': leave_balances or [],
            'reason': reason,
            'dashboard_url': f"{self.default_context.get('login_url', '')}/leaves",
        }

        return self.send_templated_email(
            to_email=to_email,
            subject=f"Leave Request {status} {config['emoji']}",
            template_name='email/leave_status.html',
            context=context
        )

    def send_notification_email(
        self,
        to_email: str,
        recipient_name: str,
        notification_title: str,
        notification_message: str,
        details: dict[str, Any] | None = None,
        action_url: str | None = None,
        action_text: str = 'View Details',
        footer_note: str | None = None
    ) -> bool:
        """Send generic notification email."""
        context = {
            'recipient_name': recipient_name,
            'notification_title': notification_title,
            'notification_message': notification_message,
            'details': details,
            'action_url': action_url,
            'action_text': action_text,
            'footer_note': footer_note,
        }

        return self.send_templated_email(
            to_email=to_email,
            subject=notification_title,
            template_name='email/notification.html',
            context=context
        )

    def send_contact_emails(
        self,
        contact_data: dict[str, Any]
    ) -> None:
        """
        Send notification to admin and acknowledgement to user for contact enquiry.
        """
        # 1. Send notification to Admin/Support
        admin_context = {
            'name': contact_data.get('name'),
            'email': contact_data.get('email'),
            'phone': contact_data.get('phone', 'N/A'),
            'subject': contact_data.get('subject'),
            'message': contact_data.get('message'),
            'ip_address': contact_data.get('ip_address', 'Unknown'),
        }

        # Determine admin email - usually from settings, fallback to sender
        admin_email = getattr(settings, 'SUPPORT_EMAIL', self.from_email)

        self.send_templated_email(
            to_email=admin_email,
            subject=f"New Enquiry: {contact_data.get('subject')}",
            template_name='email/contact_notification.html',
            context=admin_context
        )

        # 2. Send acknowledgement to User
        if contact_data.get('email'):
            user_context = {
                'name': contact_data.get('name'),
                'subject': contact_data.get('subject'),
                'reference_id': contact_data.get('id', 'N/A'),
            }

            self.send_templated_email(
                to_email=contact_data.get('email'),
                subject=f"We received your message - {self.default_context['company_name']}",
                template_name='email/contact_acknowledgement.html',
                context=user_context
            )

    def send_career_emails(
        self,
        application_data: dict[str, Any]
    ) -> None:
        """
        Send notification to HR and acknowledgement to candidate.
        """
        # 1. Send notification to HR
        hr_context = {
            'first_name': application_data.get('first_name'),
            'last_name': application_data.get('last_name'),
            'email': application_data.get('email'),
            'phone': application_data.get('phone'),
            'position': application_data.get('position_applied'),
            'experience_years': application_data.get('experience_years'),
            'current_company': application_data.get('current_company', 'N/A'),
            'linkedin_url': application_data.get('linkedin_url'),
            'portfolio_url': application_data.get('portfolio_url'),
            'resume_url': application_data.get('resume_url'),
            'cover_letter': application_data.get('cover_letter'),
        }

        # Determine HR email - usually from settings, fallback to sender
        hr_email = getattr(settings, 'HR_EMAIL', self.from_email)

        self.send_templated_email(
            to_email=hr_email,
            subject=f"Job Application: {application_data.get('position_applied')} - {application_data.get('first_name')} {application_data.get('last_name')}",
            template_name='email/career_notification.html',
            context=hr_context
        )

        # 2. Send acknowledgement to Candidate
        if application_data.get('email'):
            candidate_context = {
                'first_name': application_data.get('first_name'),
                'position': application_data.get('position_applied'),
                'application_id': application_data.get('id', 'N/A'),
            }

            self.send_templated_email(
                to_email=application_data.get('email'),
                subject=f"Application Received - {application_data.get('position_applied')}",
                template_name='email/career_acknowledgement.html',
                context=candidate_context
            )



    def send_project_created_email(
        self,
        to_email: str,
        manager_name: str,
        project_data: dict[str, Any]
    ) -> bool:
        """Send notification to manager about new project."""
        context = {
            'manager_name': manager_name,
            'project_name': project_data.get('name'),
            'project_code': project_data.get('code'),
            'client_name': project_data.get('client_name', 'N/A'),
            'start_date': project_data.get('start_date'),
            'end_date': project_data.get('end_date'),
            'dashboard_url': f"{self.default_context.get('login_url', '')}/projects/{project_data.get('id')}",
        }

        return self.send_templated_email(
            to_email=to_email,
            subject=f"New Project Assigned: {project_data.get('name')}",
            template_name='email/project_created.html',
            context=context
        )

    def send_project_assignment_email(
        self,
        to_email: str,
        employee_name: str,
        project_name: str,
        role: str,
        manager_name: str,
        start_date: str,
        project_id: int
    ) -> bool:
        """Send notification to employee about project assignment."""
        context = {
            'employee_name': employee_name,
            'project_name': project_name,
            'manager_name': manager_name,
            'role': role,
            'start_date': start_date,
            'dashboard_url': f"{self.default_context.get('login_url', '')}/projects/{project_id}",
        }

        return self.send_templated_email(
            to_email=to_email,
            subject=f"You've been added to {project_name}",
            template_name='email/project_assigned.html',
            context=context
        )

    def send_team_addition_email(
        self,
        to_email: str,
        employee_name: str,
        team_name: str,
        department_name: str,
        team_lead_name: str,
        role: str,
        team_id: int
    ) -> bool:
        """Send notification to employee about team addition."""
        context = {
            'employee_name': employee_name,
            'team_name': team_name,
            'department_name': department_name,
            'team_lead_name': team_lead_name,
            'role': role,
            'dashboard_url': f"{self.default_context.get('login_url', '')}/teams/{team_id}",
        }

        return self.send_templated_email(
            to_email=to_email,
            subject=f"Welcome to the {team_name} Team!",
            template_name='email/team_added.html',
            context=context
        )


# Singleton instance
email_service = EmailService()


# Helper functions for generating email content directly (used by some endpoints)
def employee_welcome_email(
    first_name: str,
    last_name: str,
    email: str,
    employee_code: str,
    department: str,
    designation: str,
    joining_date: str,
    password: str | None = None
) -> tuple[str, str]:
    """
    Generate welcome email subject and content.
    Returns (subject, html_content)
    """
    context = {
        'employee_name': f"{first_name} {last_name}".strip(),
        'email': email,
        'employee_id': employee_code,
        'department': department,
        'designation': designation,
        'joining_date': joining_date,
        'temp_password': password,
    }

    subject = f"Welcome to {email_service.default_context['company_name']}!"
    html_content = email_service.render_template('email/welcome.html', context)

    return subject, html_content


def generic_notification_email(
    recipient_name: str,
    title: str,
    message: str,
    action_url: str | None = None
) -> tuple[str, str]:
    """Generate generic notification email."""
    context = {
        'recipient_name': recipient_name,
        'notification_title': title,
        'notification_message': message,
        'action_url': action_url,
        'action_text': 'View Details' if action_url else None
    }
    
    html_content = email_service.render_template('email/notification.html', context)
    return title, html_content


def task_assigned_email(
    assignee_name: str,
    task_title: str,
    project_name: str,
    assigned_by: str,
    priority: str,
    due_date: str | None = None
) -> tuple[str, str]:
    """Generate task assigned email."""
    context = {
        'assignee_name': assignee_name,
        'task_title': task_title,
        'project_name': project_name,
        'assigned_by': assigned_by,
        'priority': priority,
        'due_date': due_date,
        'dashboard_url': f"{email_service.default_context.get('login_url', '')}/tasks"
    }
    
    html_content = email_service.render_template('email/task_assigned.html', context)
    return f"New Task Assigned: {task_title}", html_content
