"""
Payroll API Endpoints.

Salary structures, payslip generation, and payroll management.
"""

import calendar
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import PermissionChecker
from app.database import get_db
from app.models.auth import User
from app.models.employee import Employee
from app.models.payroll import PaySlip, PayrollStatus, SalaryStructure
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.payroll import (
    PayrollGenerateRequest,
    PayrollSummary,
    PaySlipApprove,
    PaySlipResponse,
    SalaryStructureCreate,
    SalaryStructureResponse,
    SalaryStructureUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Payroll"])


# ============ Helpers ============

def _calc_totals(struct: SalaryStructure) -> None:
    """Recalculate gross, net, and CTC for a salary structure."""
    gross = float(struct.basic or 0) + float(struct.hra or 0) + float(struct.da or 0) + \
            float(struct.transport_allowance or 0) + float(struct.medical_allowance or 0) + \
            float(struct.special_allowance or 0)

    # Add custom allowances
    if struct.other_allowances and isinstance(struct.other_allowances, dict):
        for v in struct.other_allowances.values():
            try:
                gross += float(v)
            except (ValueError, TypeError):
                pass

    total_employee_deductions = float(struct.pf_employee or 0) + float(struct.esi_employee or 0) + \
                                float(struct.professional_tax or 0) + float(struct.tds or 0)

    # Add custom deductions
    if struct.other_deductions and isinstance(struct.other_deductions, dict):
        for v in struct.other_deductions.values():
            try:
                total_employee_deductions += float(v)
            except (ValueError, TypeError):
                pass

    net = gross - total_employee_deductions
    ctc = gross + float(struct.pf_employer or 0) + float(struct.esi_employer or 0)

    struct.gross_salary = round(gross, 2)
    struct.net_salary = round(net, 2)
    struct.ctc = round(ctc, 2)


def _build_salary_response(struct: SalaryStructure) -> SalaryStructureResponse:
    """Build a salary structure response with employee info."""
    resp = SalaryStructureResponse.model_validate(struct)

    if struct.employee:
        emp = struct.employee
        if emp.user:
            resp.employee_name = f"{emp.user.first_name} {emp.user.last_name or ''}".strip()
        resp.employee_code = emp.employee_code

    return resp


def _build_payslip_response(slip: PaySlip) -> PaySlipResponse:
    """Build a payslip response with employee info."""
    resp = PaySlipResponse.model_validate(slip)

    if slip.employee:
        emp = slip.employee
        if emp.user:
            resp.employee_name = f"{emp.user.first_name} {emp.user.last_name or ''}".strip()
        resp.employee_code = emp.employee_code
        if emp.department:
            resp.department_name = emp.department.name

    return resp


# ============ Payroll Summary / Dashboard ============

@router.get("/payroll/summary", response_model=PayrollSummary)
async def get_payroll_summary(
    month: int | None = None,
    year: int | None = None,
    current_user: User = Depends(PermissionChecker("payroll.view")),
    db: Session = Depends(get_db),
):
    """Get payroll summary stats for the dashboard."""
    now = date.today()
    m = month or now.month
    y = year or now.year

    total_with_salary = db.query(SalaryStructure).filter(
        SalaryStructure.effective_to.is_(None) | (SalaryStructure.effective_to >= now)
    ).count()

    # Payslip stats for the month
    slips_query = db.query(PaySlip).filter(PaySlip.month == m, PaySlip.year == y)
    total_slips = slips_query.count()
    pending = slips_query.filter(PaySlip.status.in_(["draft", "generated"])).count()
    approved = slips_query.filter(PaySlip.status == "approved").count()
    paid = slips_query.filter(PaySlip.status == "paid").count()

    totals = db.query(
        func.coalesce(func.sum(PaySlip.gross), 0),
        func.coalesce(func.sum(PaySlip.net), 0),
        func.coalesce(func.sum(PaySlip.total_deductions), 0),
    ).filter(PaySlip.month == m, PaySlip.year == y).first()

    return PayrollSummary(
        total_employees_with_salary=total_with_salary,
        total_payslips=total_slips,
        pending_payslips=pending,
        approved_payslips=approved,
        paid_payslips=paid,
        total_gross=float(totals[0]) if totals else 0,
        total_net=float(totals[1]) if totals else 0,
        total_deductions=float(totals[2]) if totals else 0,
        current_month=m,
        current_year=y,
    )


# ============ Salary Structures ============

@router.get("/payroll/salary-structures", response_model=PaginatedResponse[SalaryStructureResponse])
async def list_salary_structures(
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("payroll.view")),
    db: Session = Depends(get_db),
):
    """List all salary structures."""
    query = db.query(SalaryStructure).options(
        joinedload(SalaryStructure.employee).joinedload(Employee.user),
    )

    if search:
        query = query.join(Employee).join(User, Employee.user_id == User.id).filter(
            User.first_name.ilike(f"%{search}%") |
            User.last_name.ilike(f"%{search}%") |
            Employee.employee_code.ilike(f"%{search}%")
        )

    total = query.count()
    items = query.order_by(desc(SalaryStructure.id)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return PaginatedResponse.create(
        [_build_salary_response(s) for s in items], total, page, page_size
    )


@router.get("/payroll/salary-structures/{struct_id}", response_model=SalaryStructureResponse)
async def get_salary_structure(
    struct_id: int,
    current_user: User = Depends(PermissionChecker("payroll.view")),
    db: Session = Depends(get_db),
):
    """Get a specific salary structure."""
    struct = db.query(SalaryStructure).options(
        joinedload(SalaryStructure.employee).joinedload(Employee.user),
    ).filter(SalaryStructure.id == struct_id).first()

    if not struct:
        raise HTTPException(status_code=404, detail="Salary structure not found")

    return _build_salary_response(struct)


@router.post("/payroll/salary-structures", response_model=SalaryStructureResponse, status_code=201)
async def create_salary_structure(
    data: SalaryStructureCreate,
    current_user: User = Depends(PermissionChecker("payroll.manage")),
    db: Session = Depends(get_db),
):
    """Create a new salary structure for an employee."""
    # Check employee exists
    employee = db.query(Employee).filter(Employee.id == data.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Close previous active structure
    active = db.query(SalaryStructure).filter(
        SalaryStructure.employee_id == data.employee_id,
        SalaryStructure.effective_to.is_(None),
    ).first()
    if active:
        active.effective_to = data.effective_from

    struct = SalaryStructure(
        employee_id=data.employee_id,
        basic=data.basic,
        hra=data.hra,
        da=data.da,
        transport_allowance=data.transport_allowance,
        medical_allowance=data.medical_allowance,
        special_allowance=data.special_allowance,
        other_allowances=data.other_allowances,
        pf_employee=data.pf_employee,
        pf_employer=data.pf_employer,
        esi_employee=data.esi_employee,
        esi_employer=data.esi_employer,
        professional_tax=data.professional_tax,
        tds=data.tds,
        other_deductions=data.other_deductions,
        effective_from=data.effective_from,
        effective_to=data.effective_to,
        created_by=current_user.id,
    )

    _calc_totals(struct)
    db.add(struct)
    db.commit()
    db.refresh(struct)

    return _build_salary_response(struct)


@router.put("/payroll/salary-structures/{struct_id}", response_model=SalaryStructureResponse)
async def update_salary_structure(
    struct_id: int,
    data: SalaryStructureUpdate,
    current_user: User = Depends(PermissionChecker("payroll.manage")),
    db: Session = Depends(get_db),
):
    """Update a salary structure."""
    struct = db.query(SalaryStructure).options(
        joinedload(SalaryStructure.employee).joinedload(Employee.user),
    ).filter(SalaryStructure.id == struct_id).first()

    if not struct:
        raise HTTPException(status_code=404, detail="Salary structure not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(struct, key, value)

    struct.updated_by = current_user.id
    _calc_totals(struct)

    db.commit()
    db.refresh(struct)

    return _build_salary_response(struct)


# ============ Payslips ============

@router.get("/payroll/payslips", response_model=PaginatedResponse[PaySlipResponse])
async def list_payslips(
    month: int | None = None,
    year: int | None = None,
    employee_id: int | None = None,
    status_filter: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("payroll.view")),
    db: Session = Depends(get_db),
):
    """List payslips with filters."""
    query = db.query(PaySlip).options(
        joinedload(PaySlip.employee).joinedload(Employee.user),
        joinedload(PaySlip.employee).joinedload(Employee.department),
    )

    if month:
        query = query.filter(PaySlip.month == month)
    if year:
        query = query.filter(PaySlip.year == year)
    if employee_id:
        query = query.filter(PaySlip.employee_id == employee_id)
    if status_filter:
        query = query.filter(PaySlip.status == status_filter)

    total = query.count()
    slips = query.order_by(desc(PaySlip.year), desc(PaySlip.month), desc(PaySlip.id)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return PaginatedResponse.create(
        [_build_payslip_response(s) for s in slips], total, page, page_size
    )


@router.get("/payroll/payslips/{slip_id}", response_model=PaySlipResponse)
async def get_payslip(
    slip_id: int,
    current_user: User = Depends(PermissionChecker("payroll.view")),
    db: Session = Depends(get_db),
):
    """Get a specific payslip."""
    slip = db.query(PaySlip).options(
        joinedload(PaySlip.employee).joinedload(Employee.user),
        joinedload(PaySlip.employee).joinedload(Employee.department),
    ).filter(PaySlip.id == slip_id).first()

    if not slip:
        raise HTTPException(status_code=404, detail="Payslip not found")

    return _build_payslip_response(slip)


# ============ Generate Payroll ============

@router.post("/payroll/payslips/generate", response_model=MessageResponse)
async def generate_payslips(
    data: PayrollGenerateRequest,
    current_user: User = Depends(PermissionChecker("payroll.manage")),
    db: Session = Depends(get_db),
):
    """
    Generate payslips for a given month/year.
    Uses the active salary structure for each employee.
    """
    m, y = data.month, data.year

    # Get active salary structures
    structures_query = db.query(SalaryStructure).options(
        joinedload(SalaryStructure.employee),
    ).filter(
        SalaryStructure.effective_from <= date(y, m, 1),
        SalaryStructure.effective_to.is_(None) | (SalaryStructure.effective_to >= date(y, m, 1)),
    )

    if data.employee_ids:
        structures_query = structures_query.filter(
            SalaryStructure.employee_id.in_(data.employee_ids)
        )

    structures = structures_query.all()

    if not structures:
        raise HTTPException(status_code=400, detail="No active salary structures found for the period")

    generated = 0
    skipped = 0

    _, days_in_month = calendar.monthrange(y, m)

    for struct in structures:
        # Skip if payslip already exists
        existing = db.query(PaySlip).filter(
            PaySlip.employee_id == struct.employee_id,
            PaySlip.month == m,
            PaySlip.year == y,
        ).first()
        if existing:
            skipped += 1
            continue

        # Calculate working days (simple: weekdays)
        total_days = days_in_month
        working_days = sum(
            1 for day in range(1, days_in_month + 1)
            if date(y, m, day).weekday() < 5
        )

        # Create payslip from salary structure
        slip = PaySlip(
            employee_id=struct.employee_id,
            salary_structure_id=struct.id,
            month=m,
            year=y,
            pay_period_start=date(y, m, 1),
            pay_period_end=date(y, m, days_in_month),
            total_days=total_days,
            working_days=working_days,
            present_days=working_days,  # Default: full attendance
            leave_days=0,
            lop_days=0,
            # Earnings from salary structure
            basic=float(struct.basic or 0),
            hra=float(struct.hra or 0),
            da=float(struct.da or 0),
            transport=float(struct.transport_allowance or 0),
            medical=float(struct.medical_allowance or 0),
            special=float(struct.special_allowance or 0),
            overtime=0,
            bonus=0,
            gross=float(struct.gross_salary or 0),
            # Deductions
            pf=float(struct.pf_employee or 0),
            esi=float(struct.esi_employee or 0),
            professional_tax=float(struct.professional_tax or 0),
            tds=float(struct.tds or 0),
            lop_deduction=0,
            total_deductions=float(struct.pf_employee or 0) + float(struct.esi_employee or 0) +
                             float(struct.professional_tax or 0) + float(struct.tds or 0),
            net=float(struct.net_salary or 0),
            status=PayrollStatus.GENERATED.value,
            created_by=current_user.id,
        )
        db.add(slip)
        generated += 1

    db.commit()

    month_name = calendar.month_name[m]
    return MessageResponse(
        message=f"Payroll for {month_name} {y}: {generated} payslips generated, {skipped} skipped (already exist)"
    )


# ============ Approve / Pay ============

@router.put("/payroll/payslips/{slip_id}/approve", response_model=PaySlipResponse)
async def approve_payslip(
    slip_id: int,
    data: PaySlipApprove,
    current_user: User = Depends(PermissionChecker("payroll.manage")),
    db: Session = Depends(get_db),
):
    """Approve or mark payslip as paid."""
    slip = db.query(PaySlip).options(
        joinedload(PaySlip.employee).joinedload(Employee.user),
        joinedload(PaySlip.employee).joinedload(Employee.department),
    ).filter(PaySlip.id == slip_id).first()

    if not slip:
        raise HTTPException(status_code=404, detail="Payslip not found")

    valid_transitions = {
        "draft": ["approved", "cancelled"],
        "generated": ["approved", "cancelled"],
        "approved": ["paid", "cancelled"],
    }

    current_status = slip.status
    if current_status not in valid_transitions or data.status not in valid_transitions.get(current_status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change status from '{current_status}' to '{data.status}'"
        )

    slip.status = data.status
    slip.approved_by = current_user.id
    slip.approved_at = date.today()

    if data.status == "paid":
        slip.payment_date = data.payment_date or date.today()
        slip.payment_method = data.payment_method
        slip.bank_reference = data.bank_reference

    slip.updated_by = current_user.id
    db.commit()
    db.refresh(slip)

    return _build_payslip_response(slip)
