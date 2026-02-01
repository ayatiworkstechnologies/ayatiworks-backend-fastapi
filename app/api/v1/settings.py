"""
Settings and Feature Flags API routes.
"""


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import PermissionChecker, get_current_active_user
from app.core.feature_control import get_module_features, is_feature_enabled
from app.database import get_db
from app.models.auth import User
from app.models.settings import FeatureFlag, SuperSettings

router = APIRouter(prefix="/settings", tags=["Settings"])


# ============== Super Settings ==============

@router.get("")
async def list_settings(
    category: str | None = None,
    scope: str | None = None,
    current_user: User = Depends(PermissionChecker("settings.view")),
    db: Session = Depends(get_db)
):
    """List all settings."""
    query = db.query(SuperSettings).filter(SuperSettings.is_deleted == False)

    if category:
        query = query.filter(SuperSettings.category == category)

    if scope:
        query = query.filter(SuperSettings.scope == scope)

    settings = query.all()

    return [
        {
            "id": s.id,
            "key": s.key,
            "value": s.get_typed_value(),
            "value_type": s.value_type,
            "scope": s.scope,
            "target_id": s.target_id,
            "category": s.category,
            "description": s.description,
            "is_public": s.is_public
        }
        for s in settings
    ]


@router.get("/{key}")
async def get_setting(
    key: str,
    scope: str = "global",
    target_id: int | None = None,
    current_user: User = Depends(PermissionChecker("settings.view")),
    db: Session = Depends(get_db)
):
    """Get a specific setting."""
    query = db.query(SuperSettings).filter(
        SuperSettings.key == key,
        SuperSettings.scope == scope,
        SuperSettings.is_deleted == False
    )

    if target_id:
        query = query.filter(SuperSettings.target_id == target_id)

    setting = query.first()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found"
        )

    return {
        "key": setting.key,
        "value": setting.get_typed_value(),
        "value_type": setting.value_type,
        "scope": setting.scope
    }


@router.put("/{key}")
async def update_setting(
    key: str,
    value: str,
    value_type: str = "string",
    scope: str = "global",
    target_id: int | None = None,
    current_user: User = Depends(PermissionChecker("settings.edit")),
    db: Session = Depends(get_db)
):
    """Update or create a setting."""
    query = db.query(SuperSettings).filter(
        SuperSettings.key == key,
        SuperSettings.scope == scope,
        SuperSettings.is_deleted == False
    )

    if target_id:
        query = query.filter(SuperSettings.target_id == target_id)

    setting = query.first()

    if setting:
        setting.value = value
        setting.value_type = value_type
        setting.updated_by = current_user.id
    else:
        setting = SuperSettings(
            key=key,
            value=value,
            value_type=value_type,
            scope=scope,
            target_id=target_id,
            created_by=current_user.id
        )
        db.add(setting)

    db.commit()

    return {"message": "Setting updated successfully"}


# ============== Feature Flags ==============

@router.get("/features/modules")
async def list_feature_modules(
    current_user: User = Depends(PermissionChecker("feature.manage")),
    db: Session = Depends(get_db)
):
    """List all modules with their features."""
    modules = ["attendance", "leave", "payroll", "employee", "project"]

    result = []
    for module in modules:
        features = get_module_features(module)
        result.append({
            "module": module,
            "features": features
        })

    return result


@router.get("/features")
async def list_features(
    module: str | None = None,
    scope: str | None = None,
    current_user: User = Depends(PermissionChecker("feature.manage")),
    db: Session = Depends(get_db)
):
    """List all feature flags."""
    query = db.query(FeatureFlag).filter(FeatureFlag.is_deleted == False)

    if module:
        query = query.filter(FeatureFlag.module == module)

    if scope:
        query = query.filter(FeatureFlag.scope == scope)

    flags = query.all()

    return [
        {
            "id": f.id,
            "module": f.module,
            "feature": f.feature,
            "name": f.name,
            "description": f.description,
            "is_enabled": f.is_enabled,
            "scope": f.scope,
            "target_id": f.target_id
        }
        for f in flags
    ]


@router.put("/features/{module}/{feature}")
async def toggle_feature(
    module: str,
    feature: str,
    is_enabled: bool,
    scope: str = "global",
    target_id: int | None = None,
    current_user: User = Depends(PermissionChecker("feature.manage")),
    db: Session = Depends(get_db)
):
    """Enable or disable a feature."""
    query = db.query(FeatureFlag).filter(
        FeatureFlag.module == module,
        FeatureFlag.feature == feature,
        FeatureFlag.scope == scope,
        FeatureFlag.is_deleted == False
    )

    if target_id:
        query = query.filter(FeatureFlag.target_id == target_id)

    flag = query.first()

    if flag:
        flag.is_enabled = is_enabled
        flag.updated_by = current_user.id
    else:
        flag = FeatureFlag(
            module=module,
            feature=feature,
            is_enabled=is_enabled,
            scope=scope,
            target_id=target_id,
            created_by=current_user.id
        )
        db.add(flag)

    db.commit()

    return {
        "message": f"Feature {module}.{feature} {'enabled' if is_enabled else 'disabled'}",
        "is_enabled": is_enabled
    }


@router.get("/features/check/{module}/{feature}")
async def check_feature(
    module: str,
    feature: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Check if a feature is enabled for current user."""
    enabled = is_feature_enabled(
        db,
        module,
        feature,
        company_id=current_user.company_id,
        role_id=current_user.role_id
    )

    return {
        "module": module,
        "feature": feature,
        "is_enabled": enabled
    }

