"""
Regression coverage for role and permission CRUD API behavior.
"""

from uuid import uuid4

from app.api.deps import get_user_permissions
from app.core.security import hash_password
from app.models.auth import Permission, Role, RolePermission, User
from app.services.auth_service import AuthService
from tests.integration.helpers import ensure_role


def _super_admin_headers(client, db) -> dict[str, str]:
    role = ensure_role(db, "SUPER_ADMIN", "Super Admin")
    suffix = uuid4().hex[:8]
    user = User(
        email=f"super-admin-{suffix}@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Super",
        last_name="Admin",
        role_id=role.id,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    auth_service = AuthService(db)
    access_token, refresh_token, _ = auth_service.create_tokens(user)
    auth_service.create_session(
        user=user,
        access_token=access_token,
        refresh_token=refresh_token,
        ip_address="testclient",
        user_agent="pytest",
    )
    return {"Authorization": f"Bearer {access_token}"}


def test_permission_crud_uses_soft_delete_and_hides_deleted_records(client, db):
    headers = _super_admin_headers(client, db)
    suffix = uuid4().hex[:8]
    payload = {
        "name": f"Manage Widgets {suffix}",
        "code": f"widget.manage.{suffix}",
        "module": "widgets",
        "description": "Test permission",
    }

    create_response = client.post("/api/v1/permissions", json=payload, headers=headers)
    assert create_response.status_code == 200
    permission_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/permissions/{permission_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True

    get_response = client.get(f"/api/v1/permissions/{permission_id}", headers=headers)
    list_response = client.get("/api/v1/permissions", headers=headers)
    permission = db.query(Permission).filter(Permission.id == permission_id).first()

    assert get_response.status_code == 404
    assert permission.is_deleted is True
    assert permission.deleted_by is not None
    assert permission_id not in [item["id"] for item in list_response.json()]


def test_role_delete_soft_deletes_role_and_role_permissions(client, db):
    headers = _super_admin_headers(client, db)
    suffix = uuid4().hex[:8]
    permission = Permission(
        name=f"View Widgets {suffix}",
        code=f"widget.view.{suffix}",
        module="widgets",
        is_active=True,
    )
    db.add(permission)
    db.commit()
    db.refresh(permission)

    create_response = client.post(
        "/api/v1/roles",
        json={
            "name": f"Widget Manager {suffix}",
            "code": f"WIDGET_MANAGER_{suffix}",
            "scope": "company",
            "permission_ids": [permission.id],
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    role_id = create_response.json()["id"]

    detail_response = client.get(f"/api/v1/roles/{role_id}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["permission_count"] == 1

    delete_response = client.delete(f"/api/v1/roles/{role_id}", headers=headers)
    assert delete_response.status_code == 200

    get_response = client.get(f"/api/v1/roles/{role_id}", headers=headers)
    role = db.query(Role).filter(Role.id == role_id).first()
    role_permissions = db.query(RolePermission).filter(RolePermission.role_id == role_id).all()

    assert get_response.status_code == 404
    assert role.is_deleted is True
    assert role.deleted_by is not None
    assert role_permissions
    assert all(rp.is_deleted for rp in role_permissions)


def test_soft_deleted_role_permission_no_longer_grants_access(client, db):
    role = ensure_role(db, "LIMITED_TEST", "Limited Test")
    suffix = uuid4().hex[:8]
    user = User(
        email=f"limited-{suffix}@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Limited",
        last_name="User",
        role_id=role.id,
        is_active=True,
        is_verified=True,
    )
    permission = Permission(
        name=f"Temporary Permission {suffix}",
        code=f"temporary.access.{suffix}",
        module="temporary",
        is_active=True,
    )
    db.add_all([user, permission])
    db.flush()
    role_permission = RolePermission(role_id=role.id, permission_id=permission.id)
    db.add(role_permission)
    db.commit()

    assert permission.code in get_user_permissions(user, db)

    role_permission.soft_delete(user.id)
    db.commit()

    assert permission.code not in get_user_permissions(user, db)
