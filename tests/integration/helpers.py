"""
Shared helpers for integration tests.
"""

from app.core.permissions import get_all_permissions
from app.models.auth import Permission, Role, RolePermission
from app.models.company import Branch, Company
from app.models.organization import Department, Designation
from app.services.auth_service import AuthService


def grant_permissions(db, role_id: int, permission_codes: list[str]) -> None:
    permission_map = {perm["code"]: perm for perm in get_all_permissions()}

    for code in permission_codes:
        permission = db.query(Permission).filter(Permission.code == code).first()
        if permission is None:
            meta = permission_map[code]
            permission = Permission(
                name=meta["name"],
                code=meta["code"],
                module=meta["module"],
            )
            db.add(permission)
            db.flush()

        existing = db.query(RolePermission).filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission.id,
        ).first()
        if existing is None:
            db.add(RolePermission(role_id=role_id, permission_id=permission.id))

    db.commit()


def get_auth_headers(client, db, test_user, permission_codes: list[str]) -> dict[str, str]:
    grant_permissions(db, test_user.role_id, permission_codes)
    auth_service = AuthService(db)
    access_token, refresh_token, _ = auth_service.create_tokens(test_user)
    auth_service.create_session(
        user=test_user,
        access_token=access_token,
        refresh_token=refresh_token,
        ip_address="testclient",
        user_agent="pytest",
    )
    return {"Authorization": f"Bearer {access_token}"}


def ensure_role(db, code: str, name: str | None = None) -> Role:
    role = db.query(Role).filter(Role.code == code).first()
    if role is None:
        role = Role(
            name=name or code.title(),
            code=code,
            description=f"{code} role",
            is_active=True,
        )
        db.add(role)
        db.commit()
        db.refresh(role)
    return role


def create_org_setup(db, *, code_suffix: str = "TST"):
    company = Company(
        name=f"Test Company {code_suffix}",
        code=f"CMP{code_suffix}",
        email=f"company-{code_suffix.lower()}@example.com",
        city="Bengaluru",
        country="India",
        timezone="Asia/Kolkata",
        currency="INR",
        date_format="YYYY-MM-DD",
    )
    db.add(company)
    db.flush()

    branch = Branch(
        company_id=company.id,
        name=f"Main Branch {code_suffix}",
        code=f"BR{code_suffix}",
        city="Bengaluru",
        country="India",
    )
    db.add(branch)
    db.flush()

    department = Department(
        company_id=company.id,
        name=f"Engineering {code_suffix}",
        code=f"ENG{code_suffix}",
        description="Test department",
    )
    db.add(department)
    db.flush()

    designation = Designation(
        name=f"Developer {code_suffix}",
        code=f"DEV{code_suffix}",
        description="Test designation",
        department_id=department.id,
        level=2,
    )
    db.add(designation)
    db.commit()
    db.refresh(company)
    db.refresh(branch)
    db.refresh(department)
    db.refresh(designation)

    return {
        "company": company,
        "branch": branch,
        "department": department,
        "designation": designation,
    }
