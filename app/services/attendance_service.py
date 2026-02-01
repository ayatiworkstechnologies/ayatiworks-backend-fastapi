"""
Attendance service.
Handles check-in, check-out, and attendance management.
"""

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.attendance import Attendance, Shift
from app.models.employee import Employee
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceStatsResponse,
    AttendanceSummary,
    CheckInRequest,
    CheckOutRequest,
)


class AttendanceService:
    """Attendance service class."""

    def __init__(self, db: Session):
        self.db = db

    def check_in(
        self,
        employee_id: int,
        data: CheckInRequest,
        ip_address: str | None = None,
        device_info: str | None = None
    ) -> Attendance:
        """
        Mark employee check-in.
        """
        today = date.today()
        now = datetime.now()

        # Check if already checked in today
        existing = self.db.query(Attendance).filter(
            Attendance.employee_id == employee_id,
            Attendance.date == today,
            Attendance.is_deleted == False
        ).first()

        if existing and existing.check_in:
            raise ValueError("Already checked in today")

        # Get employee shift
        employee = self.db.query(Employee).filter(
            Employee.id == employee_id
        ).first()

        shift_id = employee.shift_id if employee else None

        # Calculate late status if shift exists
        is_late = False
        late_minutes = 0

        if shift_id:
            shift = self.db.query(Shift).filter(Shift.id == shift_id).first()
            if shift:
                shift_start = datetime.combine(today, shift.start_time)
                grace_end = shift_start + timedelta(minutes=shift.grace_period_in)

                if now > grace_end:
                    is_late = True
                    late_minutes = int((now - shift_start).total_seconds() / 60)

        if existing:
            # Update existing record
            existing.check_in = now
            existing.work_mode = data.work_mode
            existing.check_in_latitude = data.latitude
            existing.check_in_longitude = data.longitude
            existing.check_in_address = data.address
            existing.check_in_ip = ip_address
            existing.check_in_device = device_info
            existing.is_late = is_late
            existing.late_minutes = late_minutes
            existing.notes = data.notes
            existing.status = "present"

            self.db.commit()
            self.db.refresh(existing)
            return existing

        # Create new attendance record
        attendance = Attendance(
            employee_id=employee_id,
            date=today,
            shift_id=shift_id,
            check_in=now,
            work_mode=data.work_mode,
            check_in_latitude=data.latitude,
            check_in_longitude=data.longitude,
            check_in_address=data.address,
            check_in_ip=ip_address,
            check_in_device=device_info,
            status="present",
            is_late=is_late,
            late_minutes=late_minutes,
            notes=data.notes
        )

        self.db.add(attendance)
        self.db.commit()
        self.db.refresh(attendance)

        # Send late check-in notification if employee is late
        if is_late and late_minutes > 0:
            self._send_late_notification(employee, attendance, late_minutes)

        return attendance

    def _send_late_notification(self, employee, attendance, late_minutes: int):
        """Send email notification for late check-in."""
        try:
            from app.services.email_service import email_service, get_base_template
            from app.services.notification_service import NotificationService

            if not employee.user or not employee.user.email:
                return

            # Create in-app notification
            notification_service = NotificationService(self.db)
            notification_service.create(
                user_id=employee.user_id,
                title="Late Check-in Recorded",
                message=f"You checked in {late_minutes} minutes late today. Please ensure punctuality.",
                notification_type="warning",
                category="attendance",
                entity_type="attendance",
                entity_id=attendance.id,
                send_email=False
            )

            # Send email
            hours = late_minutes // 60
            mins = late_minutes % 60
            late_time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins} minutes"

            content = f"""
            <h2 style="color: #f59e0b;">Late Check-in Notification ⚠️</h2>
            <p>Hi {employee.user.first_name},</p>
            <p>This is to inform you that your check-in today was recorded <strong>{late_time_str}</strong> after the scheduled time.</p>

            <div class="info-box" style="background: #fef3c7; border-color: #f59e0b;">
                <p><span class="label">Date:</span> <span class="value">{attendance.date}</span></p>
                <p><span class="label">Check-in Time:</span> <span class="value">{attendance.check_in.strftime('%I:%M %p')}</span></p>
                <p><span class="label">Late By:</span> <span class="value" style="color: #ef4444;">{late_time_str}</span></p>
            </div>

            <p>Regular attendance is important for team productivity. Please ensure you arrive on time.</p>
            <p>If you have any concerns, please discuss with your manager or HR.</p>

            <p>Best regards,<br>HR Team</p>
            """

            html = get_base_template("Late Check-in Notification", content)
            email_service.send_email(
                to_email=employee.user.email,
                subject=f"Late Check-in: {late_time_str} late on {attendance.date}",
                html_content=html
            )

            # Also notify manager if exists
            if employee.manager and employee.manager.user:
                manager_content = f"""
                <h2 style="color: #f59e0b;">Team Member Late Check-in ⚠️</h2>
                <p>Hi {employee.manager.user.first_name},</p>
                <p>Your team member <strong>{employee.user.first_name} {employee.user.last_name or ''}</strong> checked in late today.</p>

                <div class="info-box">
                    <p><span class="label">Employee:</span> <span class="value">{employee.employee_code} - {employee.user.full_name}</span></p>
                    <p><span class="label">Date:</span> <span class="value">{attendance.date}</span></p>
                    <p><span class="label">Check-in Time:</span> <span class="value">{attendance.check_in.strftime('%I:%M %p')}</span></p>
                    <p><span class="label">Late By:</span> <span class="value" style="color: #ef4444;">{late_time_str}</span></p>
                </div>

                <p>Best regards,<br>Enterprise HRMS</p>
                """

                manager_html = get_base_template("Team Member Late Check-in", manager_content)
                email_service.send_email(
                    to_email=employee.manager.user.email,
                    subject=f"Team Alert: {employee.user.first_name} checked in {late_time_str} late",
                    html_content=manager_html
                )
        except Exception as e:
            import logging
            logging.error(f"Failed to send late check-in notification: {e}")

    def check_out(
        self,
        employee_id: int,
        data: CheckOutRequest,
        ip_address: str | None = None,
        device_info: str | None = None
    ) -> Attendance | None:
        """
        Mark employee check-out.
        """
        today = date.today()
        now = datetime.now()

        attendance = self.db.query(Attendance).filter(
            Attendance.employee_id == employee_id,
            Attendance.date == today,
            Attendance.is_deleted == False
        ).first()

        if not attendance:
            raise ValueError("No check-in found for today")

        if attendance.check_out:
            raise ValueError("Already checked out today")

        attendance.check_out = now
        attendance.check_out_latitude = data.latitude
        attendance.check_out_longitude = data.longitude
        attendance.check_out_address = data.address
        attendance.check_out_ip = ip_address
        attendance.check_out_device = device_info

        if data.notes:
            if attendance.notes:
                attendance.notes += f"\n{data.notes}"
            else:
                attendance.notes = data.notes

        # Calculate working hours
        attendance.calculate_working_hours()

        # Calculate early leave
        if attendance.shift_id:
            shift = self.db.query(Shift).filter(
                Shift.id == attendance.shift_id
            ).first()

            if shift:
                shift_end = datetime.combine(today, shift.end_time)
                grace_start = shift_end - timedelta(minutes=shift.grace_period_out)

                if now < grace_start:
                    attendance.is_early_leave = True
                    attendance.early_leave_minutes = int((shift_end - now).total_seconds() / 60)

                # Calculate overtime
                if shift.ot_enabled:
                    ot_start = shift_end + timedelta(minutes=shift.ot_start_after)
                    if now > ot_start:
                        attendance.is_overtime = True
                        attendance.overtime_hours = round((now - ot_start).total_seconds() / 3600, 2)

                # Check if half day
                if attendance.working_hours < shift.min_working_hours:
                    attendance.is_half_day = True
                    attendance.status = "half_day"

        self.db.commit()
        self.db.refresh(attendance)

        return attendance

    def get_today_attendance(self, employee_id: int) -> Attendance | None:
        """Get today's attendance for an employee."""
        return self.db.query(Attendance).filter(
            Attendance.employee_id == employee_id,
            Attendance.date == date.today(),
            Attendance.is_deleted == False
        ).first()

    def get_by_id(self, attendance_id: int) -> Attendance | None:
        """Get attendance by ID."""
        return self.db.query(Attendance).filter(
            Attendance.id == attendance_id,
            Attendance.is_deleted == False
        ).first()

    def get_employee_attendance(
        self,
        employee_id: int,
        from_date: date,
        to_date: date
    ) -> list[Attendance]:
        """Get attendance records for an employee in date range."""
        return self.db.query(Attendance).filter(
            Attendance.employee_id == employee_id,
            Attendance.date >= from_date,
            Attendance.date <= to_date,
            Attendance.is_deleted == False
        ).order_by(Attendance.date.desc()).all()

    def get_all_attendance(
        self,
        from_date: date,
        to_date: date,
        company_id: int | None = None,
        branch_id: int | None = None,
        department_id: int | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[Attendance], int]:
        """Get all attendance records with filters."""
        query = self.db.query(Attendance).join(Employee).filter(
            Attendance.date >= from_date,
            Attendance.date <= to_date,
            Attendance.is_deleted == False
        )

        if company_id:
            query = query.filter(Employee.company_id == company_id)

        if branch_id:
            query = query.filter(Employee.branch_id == branch_id)

        if department_id:
            query = query.filter(Employee.department_id == department_id)

        if status:
            query = query.filter(Attendance.status == status)

        total = query.count()

        offset = (page - 1) * page_size
        attendances = query.order_by(
            Attendance.date.desc()
        ).offset(offset).limit(page_size).all()

        return attendances, total

    def get_summary(
        self,
        employee_id: int,
        from_date: date,
        to_date: date
    ) -> AttendanceSummary:
        """Get attendance summary for an employee."""
        attendances = self.get_employee_attendance(employee_id, from_date, to_date)

        # Calculate total days
        delta = to_date - from_date
        total_days = delta.days + 1

        # Count by status
        present_days = sum(1 for a in attendances if a.status == "present")
        absent_days = total_days - len(attendances)
        late_days = sum(1 for a in attendances if a.is_late)
        wfh_days = sum(1 for a in attendances if a.work_mode == "wfh")
        half_days = sum(1 for a in attendances if a.is_half_day)

        # Calculate hours
        total_working_hours = sum(a.working_hours for a in attendances)
        total_overtime_hours = sum(a.overtime_hours for a in attendances)

        return AttendanceSummary(
            total_days=total_days,
            present_days=present_days,
            absent_days=absent_days,
            late_days=late_days,
            wfh_days=wfh_days,
            half_days=half_days,
            total_working_hours=round(total_working_hours, 2),
            total_overtime_hours=round(total_overtime_hours, 2)
        )

    def create_manual(self, data: AttendanceCreate, created_by: int = None) -> Attendance:
        """Create attendance record manually (admin)."""
        attendance = Attendance(
            employee_id=data.employee_id,
            date=data.date,
            shift_id=data.shift_id,
            check_in=data.check_in,
            check_out=data.check_out,
            work_mode=data.work_mode,
            status=data.status,
            notes=data.notes,
            created_by=created_by
        )

        if data.check_in and data.check_out:
            attendance.calculate_working_hours()

        self.db.add(attendance)
        self.db.commit()
        self.db.refresh(attendance)

        return attendance

    def approve(
        self,
        attendance_id: int,
        approved_by: int,
        status: str = "approved",
        notes: str = None
    ) -> Attendance | None:
        """Approve or reject attendance."""
        attendance = self.get_by_id(attendance_id)

        if not attendance:
            return None

        attendance.approval_status = status
        attendance.approved_by = approved_by
        attendance.approved_at = datetime.now()
        attendance.approval_notes = notes

        self.db.commit()
        self.db.refresh(attendance)

        return attendance
        return attendance

    def mark_employee_on_leave(
        self,
        employee_id: int,
        attendance_date: date,
        leave_type_name: str,
        is_half_day: bool = False,
        notes: str = None
    ) -> Attendance:
        """
        Mark employee as on leave for a specific date.
        Propagates from LeaveService when leave is approved.
        """
        # Check if attendance already exists
        attendance = self.db.query(Attendance).filter(
            Attendance.employee_id == employee_id,
            Attendance.date == attendance_date,
            Attendance.is_deleted == False
        ).first()

        status = "half_day" if is_half_day else "on_leave"
        work_mode = "leave"

        # Format notes
        leave_note = f"On Leave ({leave_type_name})"
        if notes:
            leave_note += f": {notes}"

        if attendance:
            # Update existing record
            # Only update status if it's not already 'present' (unless we want to overwrite present with leave? Usually leave overrides absent/missing)
            # Decision: Leave approval overrides everything except maybe an explicit 'present' with check-in/out?
            # For now, let's assume approved leave overrides.

            attendance.status = status
            attendance.work_mode = work_mode
            attendance.is_half_day = is_half_day

            # Append to notes if not already there
            if attendance.notes:
                if leave_note not in attendance.notes:
                    attendance.notes += f"\n{leave_note}"
            else:
                attendance.notes = leave_note

        else:
            # Create new record
            attendance = Attendance(
                employee_id=employee_id,
                date=attendance_date,
                status=status,
                work_mode=work_mode,
                is_half_day=is_half_day,
                notes=leave_note
            )
            self.db.add(attendance)

        self.db.commit()
        self.db.refresh(attendance)
        return attendance

    def get_overall_stats(
        self,
        from_date: date,
        to_date: date,
        company_id: int | None = None,
        branch_id: int | None = None,
        department_id: int | None = None
    ) -> AttendanceStatsResponse:
        """Get overall attendance statistics."""
        # 1. Get Total Active Employees
        emp_query = self.db.query(Employee).filter(Employee.is_active == True, Employee.is_deleted == False)

        if company_id:
            emp_query = emp_query.filter(Employee.company_id == company_id)
        if branch_id:
            emp_query = emp_query.filter(Employee.branch_id == branch_id)
        if department_id:
            emp_query = emp_query.filter(Employee.department_id == department_id)

        total_active_employees = emp_query.count()

        # 2. Get Attendance Records for period
        att_query = self.db.query(Attendance).join(Employee).filter(
            Attendance.date >= from_date,
            Attendance.date <= to_date,
            Attendance.is_deleted == False
        )

        if company_id:
            att_query = att_query.filter(Employee.company_id == company_id)
        if branch_id:
            att_query = att_query.filter(Employee.branch_id == branch_id)
        if department_id:
            att_query = att_query.filter(Employee.department_id == department_id)

        attendances = att_query.all()

        # 3. Calculate Stats
        total_present = sum(1 for a in attendances if a.status in ['present', 'half_day'])
        total_late = sum(1 for a in attendances if a.is_late)
        total_wfh = sum(1 for a in attendances if a.work_mode == 'wfh')

        # Improve Absent Calculation:
        # For a single day, absent = total_active - total_present
        # For a range, this is roughly (total_active * days) - total_present
        # However, simplistic "Absent" usually means "did not show up today".
        # If range is > 1 day, "Total Absent" can be ambiguous.
        # For now, let's treat "Absent" as (Total Active * days in range) - Total Present Records
        # But for 'Today' view (single day), it's exact.

        delta = (to_date - from_date).days + 1
        total_possible_attendance = total_active_employees * delta

        total_absent = max(0, total_possible_attendance - total_present)

        attendance_rate = 0.0
        if total_possible_attendance > 0:
            attendance_rate = round((total_present / total_possible_attendance) * 100, 2)

        return AttendanceStatsResponse(
            total_active_employees=total_active_employees,
            total_present=total_present,
            total_absent=total_absent,
            total_late=total_late,
            total_wfh=total_wfh,
            attendance_rate=attendance_rate
        )

