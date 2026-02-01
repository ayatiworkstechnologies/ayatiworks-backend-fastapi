"""
Feature control utilities.
Check if modules/features are enabled based on scope.
"""


from sqlalchemy.orm import Session

from app.models.settings import FeatureFlag


def is_feature_enabled(
    db: Session,
    module: str,
    feature: str,
    company_id: int | None = None,
    role_id: int | None = None
) -> bool:
    """
    Check if a feature is enabled.
    Priority: role-specific > company-specific > global

    Args:
        db: Database session
        module: Module name
        feature: Feature name
        company_id: Optional company ID for scoped check
        role_id: Optional role ID for scoped check

    Returns:
        True if feature is enabled
    """
    # Check role-specific first
    if role_id:
        role_flag = db.query(FeatureFlag).filter(
            FeatureFlag.module == module,
            FeatureFlag.feature == feature,
            FeatureFlag.scope == "role",
            FeatureFlag.target_id == role_id,
            FeatureFlag.is_deleted == False
        ).first()

        if role_flag:
            return role_flag.is_enabled

    # Check company-specific
    if company_id:
        company_flag = db.query(FeatureFlag).filter(
            FeatureFlag.module == module,
            FeatureFlag.feature == feature,
            FeatureFlag.scope == "company",
            FeatureFlag.target_id == company_id,
            FeatureFlag.is_deleted == False
        ).first()

        if company_flag:
            return company_flag.is_enabled

    # Check global
    global_flag = db.query(FeatureFlag).filter(
        FeatureFlag.module == module,
        FeatureFlag.feature == feature,
        FeatureFlag.scope == "global",
        FeatureFlag.is_deleted == False
    ).first()

    if global_flag:
        return global_flag.is_enabled

    # Default to enabled if no flag exists
    return True


def get_disabled_features(
    db: Session,
    company_id: int | None = None,
    role_id: int | None = None
) -> list:
    """
    Get list of all disabled features for given scope.

    Returns:
        List of disabled feature dictionaries
    """
    disabled = []

    # Get all flags
    query = db.query(FeatureFlag).filter(
        FeatureFlag.is_enabled == False,
        FeatureFlag.is_deleted == False
    )

    flags = query.all()

    for flag in flags:
        # Check if this flag applies to the given scope
        applies = False

        if flag.scope == "global":
            applies = True
        elif flag.scope == "company" and flag.target_id == company_id:
            applies = True
        elif flag.scope == "role" and flag.target_id == role_id:
            applies = True

        if applies:
            disabled.append({
                "module": flag.module,
                "feature": flag.feature
            })

    return disabled


def get_module_features(module: str) -> list:
    """Get all available features for a module."""

    # Define features per module
    module_features = {
        "attendance": [
            {"feature": "geo_location", "name": "Geo-Location Tracking", "description": "Track employee location during check-in/out"},
            {"feature": "wfh", "name": "Work From Home", "description": "Allow WFH attendance marking"},
            {"feature": "remote", "name": "Remote Work", "description": "Allow remote attendance marking"},
            {"feature": "overtime", "name": "Overtime Tracking", "description": "Calculate overtime hours"},
            {"feature": "approval", "name": "Attendance Approval", "description": "Require manager approval"},
        ],
        "leave": [
            {"feature": "encashment", "name": "Leave Encashment", "description": "Allow leave encashment"},
            {"feature": "carry_forward", "name": "Carry Forward", "description": "Allow carry forward of leaves"},
            {"feature": "half_day", "name": "Half Day Leave", "description": "Allow half-day leaves"},
        ],
        "payroll": [
            {"feature": "auto_generate", "name": "Auto Generate Payslips", "description": "Automatically generate monthly payslips"},
            {"feature": "tax_calculation", "name": "Tax Calculation", "description": "Auto calculate tax deductions"},
        ],
        "employee": [
            {"feature": "self_service", "name": "Self Service Portal", "description": "Employee self-service features"},
            {"feature": "document_upload", "name": "Document Upload", "description": "Allow document uploads"},
        ],
        "project": [
            {"feature": "time_tracking", "name": "Time Tracking", "description": "Track time spent on tasks"},
            {"feature": "sprints", "name": "Sprint Management", "description": "Agile sprint features"},
        ],
    }

    return module_features.get(module, [])

