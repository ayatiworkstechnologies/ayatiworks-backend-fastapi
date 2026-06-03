"""
Regression coverage for public contact and career admin CRUD behavior.
"""

from uuid import uuid4

from app.core.security import hash_password
from app.models.auth import User
from app.models.public import CareerApplication, ContactEnquiry
from app.services.auth_service import AuthService
from tests.integration.helpers import ensure_role


def _admin_headers(db) -> dict[str, str]:
    role = ensure_role(db, "SUPER_ADMIN", "Super Admin")
    suffix = uuid4().hex[:8]
    user = User(
        email=f"public-admin-{suffix}@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Public",
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


def test_contact_admin_crud_hides_soft_deleted_records(client, db):
    headers = _admin_headers(db)
    suffix = uuid4().hex[:8]
    enquiry = ContactEnquiry(
        name=f"Contact {suffix}",
        email=f"contact-{suffix}@example.com",
        phone="9999999999",
        subject="Need a product demo",
        message="Please contact me about the product demo.",
    )
    db.add(enquiry)
    db.commit()
    db.refresh(enquiry)

    list_response = client.get("/api/v1/public/contact", headers=headers)
    assert list_response.status_code == 200, list_response.text
    assert "pages" in list_response.json()

    update_response = client.put(
        f"/api/v1/public/contact/{enquiry.id}",
        json={"status": "read"},
        headers=headers,
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["status"] == "read"

    delete_response = client.delete(f"/api/v1/public/contact/{enquiry.id}", headers=headers)
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["success"] is True

    get_response = client.get(f"/api/v1/public/contact/{enquiry.id}", headers=headers)
    list_after_delete = client.get("/api/v1/public/contact", headers=headers)
    db.refresh(enquiry)

    assert get_response.status_code == 404
    assert enquiry.is_deleted is True
    assert enquiry.deleted_by is not None
    assert enquiry.id not in [item["id"] for item in list_after_delete.json()["items"]]


def test_career_admin_crud_hides_soft_deleted_records(client, db):
    headers = _admin_headers(db)
    suffix = uuid4().hex[:8]
    application = CareerApplication(
        first_name="Career",
        last_name=suffix,
        email=f"career-{suffix}@example.com",
        phone="9999999999",
        position_applied="Backend Engineer",
        experience_years=5,
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    list_response = client.get("/api/v1/public/careers", headers=headers)
    assert list_response.status_code == 200, list_response.text
    assert "pages" in list_response.json()

    update_response = client.put(
        f"/api/v1/public/careers/{application.id}",
        json={"status": "reviewed"},
        headers=headers,
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["status"] == "reviewed"

    delete_response = client.delete(f"/api/v1/public/careers/{application.id}", headers=headers)
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["success"] is True

    get_response = client.get(f"/api/v1/public/careers/{application.id}", headers=headers)
    list_after_delete = client.get("/api/v1/public/careers", headers=headers)
    db.refresh(application)

    assert get_response.status_code == 404
    assert application.is_deleted is True
    assert application.deleted_by is not None
    assert application.id not in [item["id"] for item in list_after_delete.json()["items"]]
