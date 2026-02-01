"""
HR Advanced models - Performance, Training, Assets, Expenses.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)

from app.models.base import AuditMixin, BaseModel

# ============== Performance Management ==============

class PerformanceCycle(BaseModel, AuditMixin):
    """Performance review cycle."""

    __tablename__ = "performance_cycles"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)

    # Period
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Type
    cycle_type = Column(String(50), default="annual")  # annual, quarterly, probation

    # Status
    status = Column(String(20), default="draft")  # draft, active, completed, archived


class PerformanceReview(BaseModel, AuditMixin):
    """Individual performance review."""

    __tablename__ = "performance_reviews"

    cycle_id = Column(Integer, ForeignKey("performance_cycles.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    # Self assessment
    self_assessment = Column(JSON, nullable=True)  # {goals, achievements, challenges}

    # Manager review
    manager_review = Column(JSON, nullable=True)

    # Ratings
    overall_rating = Column(Float, nullable=True)
    ratings = Column(JSON, nullable=True)  # {criterion: rating}

    # Goals
    goals_achieved = Column(JSON, nullable=True)
    new_goals = Column(JSON, nullable=True)

    # Development
    strengths = Column(Text, nullable=True)
    areas_for_improvement = Column(Text, nullable=True)
    development_plan = Column(Text, nullable=True)

    # Status
    status = Column(String(20), default="draft")  # draft, self_review, manager_review, completed

    submitted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class Goal(BaseModel, AuditMixin):
    """Employee goal / OKR."""

    __tablename__ = "goals"

    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Type
    goal_type = Column(String(50), default="individual")  # individual, team, company

    # Key results
    key_results = Column(JSON, nullable=True)  # [{title, target, current, unit}]

    # Timeline
    start_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)

    # Progress
    progress = Column(Integer, default=0)  # 0-100
    status = Column(String(20), default="active")  # active, completed, cancelled

    # Weight
    weight = Column(Float, default=1.0)

    # Review cycle
    cycle_id = Column(Integer, ForeignKey("performance_cycles.id"), nullable=True)


# ============== Training Management ==============

class Training(BaseModel, AuditMixin):
    """Training course/program."""

    __tablename__ = "trainings"

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Type
    training_type = Column(String(50), default="online")  # online, classroom, workshop
    category = Column(String(100), nullable=True)

    # Provider
    provider = Column(String(255), nullable=True)
    instructor = Column(String(100), nullable=True)

    # Schedule
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    duration_hours = Column(Float, nullable=True)

    # Location
    location = Column(String(255), nullable=True)
    meeting_link = Column(String(500), nullable=True)

    # Capacity
    max_participants = Column(Integer, nullable=True)

    # Cost
    cost_per_person = Column(Numeric(10, 2), nullable=True)

    # Resources
    materials = Column(JSON, nullable=True)  # [{name, url}]

    # Status
    status = Column(String(20), default="draft")  # draft, scheduled, in_progress, completed, cancelled

    # Certification
    provides_certification = Column(Boolean, default=False)


class TrainingEnrollment(BaseModel, AuditMixin):
    """Training enrollment record."""

    __tablename__ = "training_enrollments"

    training_id = Column(Integer, ForeignKey("trainings.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)

    # Status
    status = Column(String(20), default="enrolled")  # enrolled, in_progress, completed, cancelled, failed

    # Progress
    progress = Column(Integer, default=0)

    # Dates
    enrolled_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Score
    score = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=True)

    # Feedback
    rating = Column(Integer, nullable=True)  # 1-5
    feedback = Column(Text, nullable=True)


class Certification(BaseModel, AuditMixin):
    """Employee certification."""

    __tablename__ = "certifications"

    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    issuing_organization = Column(String(255), nullable=True)
    credential_id = Column(String(100), nullable=True)

    # Dates
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)

    # Document
    document_path = Column(String(500), nullable=True)

    # Verification
    is_verified = Column(Boolean, default=False)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Training link
    training_id = Column(Integer, ForeignKey("trainings.id"), nullable=True)


# ============== Asset Management ==============

class Asset(BaseModel, AuditMixin):
    """Company asset."""

    __tablename__ = "assets"

    name = Column(String(255), nullable=False)
    asset_code = Column(String(50), unique=True, nullable=False, index=True)

    # Category
    category = Column(String(50), nullable=False)  # laptop, phone, furniture, vehicle

    # Details
    brand = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True)

    # Purchase
    purchase_date = Column(Date, nullable=True)
    purchase_cost = Column(Numeric(12, 2), nullable=True)
    vendor = Column(String(255), nullable=True)

    # Warranty
    warranty_expiry = Column(Date, nullable=True)

    # Location
    location = Column(String(255), nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)

    # Assignment
    assigned_to = Column(Integer, ForeignKey("employees.id"), nullable=True)
    assigned_at = Column(Date, nullable=True)

    # Status
    status = Column(String(20), default="available")  # available, assigned, maintenance, retired
    condition = Column(String(20), default="good")  # good, fair, poor

    # Depreciation
    depreciation_method = Column(String(20), nullable=True)
    useful_life_years = Column(Integer, nullable=True)
    salvage_value = Column(Numeric(12, 2), nullable=True)


class AssetAssignment(BaseModel, AuditMixin):
    """Asset assignment history."""

    __tablename__ = "asset_assignments"

    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    assigned_at = Column(Date, nullable=False)
    returned_at = Column(Date, nullable=True)

    # Condition
    condition_at_assignment = Column(String(20), nullable=True)
    condition_at_return = Column(String(20), nullable=True)

    notes = Column(Text, nullable=True)


# ============== Expense Management ==============

class ExpenseCategory(BaseModel, AuditMixin):
    """Expense category."""

    __tablename__ = "expense_categories"

    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    # Limits
    max_amount = Column(Numeric(10, 2), nullable=True)
    requires_receipt = Column(Boolean, default=True)
    requires_approval = Column(Boolean, default=True)


class Expense(BaseModel, AuditMixin):
    """Expense claim."""

    __tablename__ = "expenses"

    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)

    # Category
    category_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=False)

    # Details
    date = Column(Date, nullable=False)  # noqa: F811
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD")
    description = Column(Text, nullable=True)

    # Project
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)

    # Receipt
    receipt_path = Column(String(500), nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, approved, rejected, paid

    # Approval
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_notes = Column(Text, nullable=True)

    # Payment
    paid_at = Column(Date, nullable=True)
    payment_reference = Column(String(100), nullable=True)


class ExpenseReport(BaseModel, AuditMixin):
    """Expense report (group of expenses)."""

    __tablename__ = "expense_reports"

    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Period
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False)

    # Totals
    total_amount = Column(Numeric(12, 2), default=0)
    approved_amount = Column(Numeric(12, 2), default=0)

    # Status
    status = Column(String(20), default="draft")  # draft, submitted, approved, rejected, paid

    submitted_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)

