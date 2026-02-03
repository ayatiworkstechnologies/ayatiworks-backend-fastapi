import os
import sys
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, date
from jinja2 import Environment, FileSystemLoader

# SMTP Configuration
SMTP_HOST = "mail.ayatiworks.com"
SMTP_PORT = 465
SMTP_USER = "emailsmtp@ayatiworks.com"
SMTP_PASSWORD = "hYd@W,$nwNjC"
SMTP_FROM_EMAIL = "emailsmtp@ayatiworks.com"
SMTP_FROM_NAME = "Ayatiworks Workspace"

# Adjust paths relative to script location
# If running from backend/scripts/
# TEMPLATE_DIR should be ../app/templates
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "templates")
OUTPUT_DIR = "test_email_output"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def send_email(to_email, subject, html_content):
    print(f"📧 Sending email to {to_email}...")
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        # Attach HTML content
        msg.attach(MIMEText(html_content, "html"))

        # Create connection
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, to_email, msg.as_string())
        
        print(f"✅ Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

def render_template(env, template_name, context, output_name):
    try:
        template = env.get_template(template_name)
        output = template.render(**context)
        output_path = os.path.join(OUTPUT_DIR, output_name)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"✅ Rendered {template_name} -> {output_path}")
        return output 
    except Exception as e:
        print(f"❌ Failed to render {template_name}: {e}")
        return None

def main():
    if not os.path.exists(TEMPLATE_DIR):
        print(f"Error: Template directory not found at {TEMPLATE_DIR}")
        # print("Run this script from the project root (d:\\2026\\product 1)")
        return

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

    # Common Branding
    base_context = {
        "title": "Ayatiworks Notification",
        "company_name": "Ayatiworks Workspace",
        "current_year": "2026",
        "company_website": "https://ayatiworks.com",
        "support_email": "rubankumar@ayatiworks.com",
        "company_address": "123 Innovation Drive, Tech City",
        "login_url": "http://localhost:3000/login"
    }
    
    recipient_email = "rubankumar@ayatiworks.com"

    # 1. Welcome Email
    print("\n--- Generating Welcome Email ---")
    welcome_context = base_context.copy()
    welcome_context.update({
        "employee_name": "Ruban Kumar",
        "email": recipient_email,
        "employee_id": "EMP-2026-001",
        "temp_password": "TempPassword123!"
    })
    
    html_content = render_template(env, "email/welcome.html", welcome_context, "welcome.html")
    if html_content:
        send_email(recipient_email, "Welcome to Ayatiworks Workspace! 🎉", html_content)

    # 2. Password Reset
    print("\n--- Generating Password Reset Email ---")
    reset_context = base_context.copy()
    reset_context.update({
        "user_name": "Ruban Kumar",
        "reset_code": "849201",
        "expiry_minutes": "15",
        "reset_url": "http://localhost:3000/reset-password?token=xyz"
    })
    html_content = render_template(env, "email/password_reset.html", reset_context, "password_reset.html")
    if html_content:
        send_email(recipient_email, "Reset Your Password - Ayatiworks", html_content)


    # 3. OTP
    print("\n--- Generating OTP Email ---")
    otp_context = base_context.copy()
    otp_context.update({
        "user_name": "Ruban Kumar",
        "otp_code": "994421",
        "expiry_minutes": "10",
        "login_time": datetime.now().strftime("%b %d, %Y %I:%M %p"),
        "ip_address": "192.168.1.1"
    })
    
    html_content = render_template(env, "email/otp.html", otp_context, "otp.html")
    if html_content:
        send_email(recipient_email, "Your Verification Code - Ayatiworks", html_content)


    # 4. Leave Status (Approved)
    print("\n--- Generating Leave Status Email ---")
    leave_context = base_context.copy()
    leave_context.update({
        "employee_name": "Ruban Kumar",
        "status": "Approved",
        "status_color": "#059669", # Emerald 600
        "status_emoji": "✅",
        "leave_type": "Sick Leave",
        "from_date": "Feb 5, 2026",
        "to_date": "Feb 6, 2026",
        "duration": 2,
        "dashboard_url": "http://localhost:3000/leaves",
        "leave_balances": [
             {"type": "Sick Leave", "available": 5},
             {"type": "Casual Leave", "available": 10}
        ]
    })
    
    html_content = render_template(env, "email/leave_status.html", leave_context, "leave_approve.html")
    if html_content:
        send_email(recipient_email, "Leave Request Approved ✅", html_content)

    # 5. Review Leave Status (Rejection)
    # Skipped to avoid spamming too many similar emails, but included in rendering
    leave_reject_context = leave_context.copy()
    leave_reject_context.update({
        "status": "Rejected",
        "status_color": "#dc2626", # Red 600
        "status_emoji": "❌",
        "approver_comments": "Please provide a medical certificate."
    })
    render_template(env, "email/leave_status.html", leave_reject_context, "leave_reject.html")


    # ================= NEW NOTIFICATIONS =================

    # 6. Project Created
    print("\n--- Generating Project Created Email (Manager) ---")
    project_created_context = base_context.copy()
    project_created_context.update({
        "manager_name": "Ruban Kumar",
        "project_name": "Website Redesign 2026",
        "project_code": "PRJ-2026-005",
        "client_name": "Acme Corp",
        "start_date": "Feb 10, 2026",
        "end_date": "May 30, 2026",
        "dashboard_url": "http://localhost:3000/projects/123"
    })
    html_content = render_template(env, "email/project_created.html", project_created_context, "project_created.html")
    if html_content:
        send_email(recipient_email, "New Project Assigned: Website Redesign 2026", html_content)

    # 7. Project Assigned
    print("\n--- Generating Project Assigned Email (Employee) ---")
    project_assigned_context = base_context.copy()
    project_assigned_context.update({
        "employee_name": "Ruban Kumar",
        "project_name": "Website Redesign 2026",
        "manager_name": "Alice Manager",
        "role": "Frontend Developer",
        "start_date": "Feb 12, 2026",
        "dashboard_url": "http://localhost:3000/projects/123"
    })
    html_content = render_template(env, "email/project_assigned.html", project_assigned_context, "project_assigned.html")
    if html_content:
        send_email(recipient_email, "You've been added to Website Redesign 2026", html_content)

    # 8. Team Added
    print("\n--- Generating Team Added Email ---")
    team_added_context = base_context.copy()
    team_added_context.update({
        "employee_name": "Ruban Kumar",
        "team_name": "UX Design Team",
        "department_name": "Design",
        "team_lead_name": "David Lead",
        "role": "Senior Designer",
        "dashboard_url": "http://localhost:3000/teams/456"
    })
    html_content = render_template(env, "email/team_added.html", team_added_context, "team_added.html")
    if html_content:
        send_email(recipient_email, "Welcome to the UX Design Team!", html_content)

    # 9. Task Assigned
    print("\n--- Generating Task Assigned Email ---")
    task_context = base_context.copy()
    task_context.update({
        "assignee_name": "Ruban Kumar",
        "task_title": "Implement Login Page Design",
        "project_name": "Website Redesign 2026",
        "assigned_by": "Alice Manager",
        "priority": "High",
        "due_date": "Feb 15, 2026",
        "dashboard_url": "http://localhost:3000/tasks/789"
    })
    html_content = render_template(env, "email/task_assigned.html", task_context, "task_assigned.html")
    if html_content:
        send_email(recipient_email, "New Task Assigned: Implement Login Page Design", html_content)


if __name__ == "__main__":
    main()
