"""
Integration tests for employee, client, and project CRUD flows.
"""

from datetime import date

import pytest

from tests.integration.helpers import create_org_setup, ensure_role, get_auth_headers


@pytest.fixture(autouse=True)
def stub_email_senders(monkeypatch):
    from app.api.v1 import projects as projects_api
    from app.main import app
    from app.services import email_service as email_module

    monkeypatch.setattr(email_module.email_service, "send_email", lambda *args, **kwargs: True)
    monkeypatch.setattr(projects_api.email_service, "send_project_created_email", lambda *args, **kwargs: True)

    storage = getattr(app.state.limiter, "_storage", None)
    if storage and hasattr(storage, "reset"):
        storage.reset()


def test_employee_user_list_shows_only_self(client, db, test_user):
    from app.models.employee import Employee

    org = create_org_setup(db, code_suffix="SELF")
    headers = get_auth_headers(
        client,
        db,
        test_user,
        ["employee.view"],
    )

    employee = Employee(
        user_id=test_user.id,
        employee_code="AW0001",
        company_id=org["company"].id,
        branch_id=org["branch"].id,
        department_id=org["department"].id,
        designation_id=org["designation"].id,
        joining_date=date(2026, 4, 13),
        employment_type="full_time",
        employment_status="active",
        work_mode="office",
    )
    db.add(employee)
    db.commit()

    response = client.get("/api/v1/employees", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["user_id"] == test_user.id


def test_logout_invalidates_access_token(client, db, test_user):
    headers = get_auth_headers(
        client,
        db,
        test_user,
        ["employee.view"],
    )

    profile_response = client.get("/api/v1/auth/me", headers=headers)
    assert profile_response.status_code == 200, profile_response.text

    logout_response = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_response.status_code == 200, logout_response.text

    denied_response = client.get("/api/v1/auth/me", headers=headers)
    assert denied_response.status_code == 401, denied_response.text


def test_login_2fa_sends_otp(client, db, test_user, monkeypatch):
    from app.services import email_service as email_module

    test_user.is_2fa_enabled = True
    db.commit()

    monkeypatch.setattr(email_module.email_service, "send_otp_email", lambda *args, **kwargs: True)

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 202, response.text
    payload = response.json()
    assert payload["error_code"] == "2FA_REQUIRED"


def test_employee_crud_flow(client, db, test_user):
    org = create_org_setup(db, code_suffix="EMP")
    employee_role = ensure_role(db, code="EMPLOYEE", name="Employee")
    headers = get_auth_headers(
        client,
        db,
        test_user,
        [
            "employee.view",
            "employee.view_all",
            "employee.create",
            "employee.edit",
            "employee.delete",
        ],
    )

    create_response = client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "email": "employee-crud@example.com",
            "first_name": "Riya",
            "last_name": "Sharma",
            "password": "StrongPass123!",
            "company_id": org["company"].id,
            "branch_id": org["branch"].id,
            "department_id": org["department"].id,
            "designation_id": org["designation"].id,
            "role_id": employee_role.id,
            "joining_date": "2026-04-13",
            "employment_type": "full_time",
            "work_mode": "office",
            "personal_phone": "9999999999",
            "city": "Bengaluru",
            "country": "India",
        },
    )
    assert create_response.status_code == 201, create_response.text
    employee = create_response.json()
    employee_id = employee["id"]
    assert employee["user"]["email"] == "employee-crud@example.com"
    assert employee["department_id"] == org["department"].id

    list_response = client.get("/api/v1/employees", headers=headers)
    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["total"] >= 1

    get_response = client.get(f"/api/v1/employees/{employee_id}", headers=headers)
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["employee_code"].startswith("AW")

    code_response = client.get("/api/v1/employees/next-code", headers=headers)
    assert code_response.status_code == 200, code_response.text
    assert code_response.json()["code"].startswith("AW")

    update_response = client.put(
        f"/api/v1/employees/{employee_id}",
        headers=headers,
        json={
            "employment_status": "probation",
            "work_mode": "hybrid",
            "city": "Mumbai",
            "personal_phone": "8888888888",
        },
    )
    assert update_response.status_code == 200, update_response.text
    updated = update_response.json()
    assert updated["employment_status"] == "probation"
    assert updated["work_mode"] == "hybrid"
    assert updated["city"] == "Mumbai"

    delete_response = client.delete(f"/api/v1/employees/{employee_id}", headers=headers)
    assert delete_response.status_code == 200, delete_response.text


def test_client_crud_flow(client, db, test_user):
    org = create_org_setup(db, code_suffix="CLI")
    ensure_role(db, code="CLIENT", name="Client")
    headers = get_auth_headers(
        client,
        db,
        test_user,
        [
            "client.view",
            "client.create",
            "client.edit",
            "client.delete",
        ],
    )

    create_response = client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "first_name": "Aman",
            "last_name": "Verma",
            "email": "client-crud@example.com",
            "password": "StrongPass123!",
            "phone": "7777777777",
            "company_id": org["company"].id,
            "department_id": org["department"].id,
            "designation_id": org["designation"].id,
            "joining_date": "2026-04-13",
            "company_name": "ClientCorp",
            "industry": "Software",
            "city": "Delhi",
            "country": "India",
            "website": "https://clientcorp.example.com",
            "tags": ["vip", "enterprise"],
        },
    )
    assert create_response.status_code == 201, create_response.text
    client_payload = create_response.json()
    client_id = client_payload["id"]
    assert client_payload["email"] == "client-crud@example.com"
    assert client_payload["company_name"] == "ClientCorp"
    assert client_payload["employee_code"].startswith("AWC")

    list_response = client.get("/api/v1/clients", headers=headers)
    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["total"] >= 1

    get_response = client.get(f"/api/v1/clients/{client_id}", headers=headers)
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["crm_client_id"] is not None

    update_response = client.put(
        f"/api/v1/clients/{client_id}",
        headers=headers,
        json={
            "phone": "7666666666",
            "status": "inactive",
            "company_name": "ClientCorp Updated",
            "city": "Pune",
        },
    )
    assert update_response.status_code == 200, update_response.text
    updated = update_response.json()
    assert updated["phone"] == "7666666666"
    assert updated["status"] == "inactive"
    assert updated["company_name"] == "ClientCorp Updated"

    delete_response = client.delete(f"/api/v1/clients/{client_id}", headers=headers)
    assert delete_response.status_code == 200, delete_response.text


def test_project_crud_flow(client, db, test_user):
    org = create_org_setup(db, code_suffix="PRJ")
    employee_role = ensure_role(db, code="EMPLOYEE", name="Employee")
    ensure_role(db, code="CLIENT", name="Client")
    headers = get_auth_headers(
        client,
        db,
        test_user,
        [
            "employee.create",
            "client.create",
            "project.view",
            "project.view_all",
            "project.create",
            "project.edit",
            "project.delete",
        ],
    )

    manager_response = client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "email": "manager-project@example.com",
            "first_name": "Neha",
            "last_name": "Manager",
            "password": "StrongPass123!",
            "company_id": org["company"].id,
            "branch_id": org["branch"].id,
            "department_id": org["department"].id,
            "designation_id": org["designation"].id,
            "role_id": employee_role.id,
            "joining_date": "2026-04-13",
            "employment_type": "full_time",
            "work_mode": "office",
        },
    )
    assert manager_response.status_code == 201, manager_response.text
    manager_id = manager_response.json()["id"]

    client_response = client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "first_name": "Project",
            "last_name": "Client",
            "email": "project-client@example.com",
            "password": "StrongPass123!",
            "company_id": org["company"].id,
            "department_id": org["department"].id,
            "designation_id": org["designation"].id,
            "company_name": "Project Client Co",
        },
    )
    assert client_response.status_code == 201, client_response.text
    crm_client_id = client_response.json()["crm_client_id"]

    next_code_response = client.get("/api/v1/projects/next-code", headers=headers)
    assert next_code_response.status_code == 200, next_code_response.text
    project_code = next_code_response.json()["next_code"]

    create_response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "name": "Backend Upgrade",
            "code": project_code,
            "description": "Upgrade and stabilize the backend",
            "client_id": crm_client_id,
            "manager_id": manager_id,
            "company_id": org["company"].id,
            "start_date": "2026-04-13",
            "end_date": "2026-05-13",
            "budget": 250000,
            "currency": "INR",
            "billing_type": "fixed",
            "tags": ["backend", "upgrade"],
        },
    )
    assert create_response.status_code == 201, create_response.text
    project = create_response.json()
    project_id = project["id"]
    assert project["code"] == project_code

    list_response = client.get("/api/v1/projects", headers=headers)
    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["total"] >= 1

    get_response = client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["id"] == project_id

    update_response = client.put(
        f"/api/v1/projects/{project_id}",
        headers=headers,
        json={
            "status": "in_progress",
            "progress": 45,
            "name": "Backend Upgrade Phase 1",
        },
    )
    assert update_response.status_code == 200, update_response.text
    updated = update_response.json()
    assert updated["status"] == "in_progress"
    assert updated["progress"] == 45
    assert updated["name"] == "Backend Upgrade Phase 1"

    delete_response = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert delete_response.status_code == 200, delete_response.text
