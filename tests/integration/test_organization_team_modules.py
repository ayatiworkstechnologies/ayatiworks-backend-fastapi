"""
Regression coverage for department and team modules.
"""

from datetime import date

from app.core.security import hash_password
from app.models.auth import User
from app.models.employee import Employee
from app.models.organization import Department, Designation
from app.models.team import Team
from app.services.organization_service import DepartmentService
from app.services.team_service import TeamService
from tests.integration.helpers import create_org_setup, ensure_role, get_auth_headers


def test_department_tree_returns_root_departments(db):
    org = create_org_setup(db, code_suffix="TREE")
    child = Department(
        company_id=org["company"].id,
        name="Platform TREE",
        code="PLATREE",
        parent_id=org["department"].id,
        level=1,
    )
    db.add(child)
    db.commit()

    roots = DepartmentService(db).get_tree(org["company"].id)

    assert [dept.id for dept in roots] == [org["department"].id]
    assert roots[0].children[0].id == child.id


def test_team_delete_is_soft_delete_and_lists_exclude_deleted(db):
    org = create_org_setup(db, code_suffix="TEAM")
    service = TeamService(db)
    team = Team(
        company_id=org["company"].id,
        department_id=org["department"].id,
        name="Product Team",
        code="PRODTEAM",
        is_active=True,
    )
    db.add(team)
    db.commit()
    db.refresh(team)

    assert service.delete(team.id, deleted_by=99) is True

    deleted_team = db.query(Team).filter(Team.id == team.id).first()
    teams, total = service.get_all(company_id=org["company"].id)

    assert deleted_team.is_deleted is True
    assert deleted_team.deleted_by == 99
    assert teams == []
    assert total == 0


def test_team_api_lifecycle_and_member_detail_uses_employee_user(client, db, test_user, monkeypatch):
    from app.api.v1 import teams as teams_api

    monkeypatch.setattr(
        teams_api.email_service,
        "send_team_addition_email",
        lambda *args, **kwargs: True,
    )

    org = create_org_setup(db, code_suffix="TLIF")
    employee_role = ensure_role(db, code="EMPLOYEE", name="Employee")
    test_user.company_id = org["company"].id

    employee_user = User(
        email="team-member@example.com",
        password_hash=hash_password("StrongPass123!"),
        first_name="Asha",
        last_name="Member",
        role_id=employee_role.id,
        company_id=org["company"].id,
        branch_id=org["branch"].id,
        is_active=True,
        is_verified=True,
    )
    db.add(employee_user)
    db.flush()
    employee = Employee(
        user_id=employee_user.id,
        employee_code="AW7777",
        company_id=org["company"].id,
        branch_id=org["branch"].id,
        department_id=org["department"].id,
        designation_id=org["designation"].id,
        joining_date=date(2026, 6, 3),
        employment_type="full_time",
        employment_status="active",
        work_mode="office",
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)

    headers = get_auth_headers(
        client,
        db,
        test_user,
        ["team.view", "team.create", "team.edit", "team.delete", "team.manage_members"],
    )

    create_response = client.post(
        "/api/v1/teams",
        headers=headers,
        json={
            "company_id": org["company"].id,
            "department_id": org["department"].id,
            "team_lead_id": employee_user.id,
            "name": "Delivery Team TLIF",
            "code": "DELTLIF",
            "team_type": "web",
            "max_members": 5,
            "description": "Delivery team",
            "is_active": True,
        },
    )
    assert create_response.status_code == 201, create_response.text
    team_id = create_response.json()["id"]

    list_response = client.get(
        f"/api/v1/teams?company_id={org['company'].id}&page_size=100",
        headers=headers,
    )
    assert list_response.status_code == 200, list_response.text
    assert any(item["id"] == team_id for item in list_response.json()["items"])

    add_member_response = client.post(
        f"/api/v1/teams/{team_id}/members",
        headers=headers,
        json={
            "employee_id": employee.id,
            "role": "Developer",
            "joined_date": "2026-06-03",
            "is_active": True,
        },
    )
    assert add_member_response.status_code == 200, add_member_response.text
    assert add_member_response.json()["employee_name"] == "Asha Member"
    assert add_member_response.json()["department_name"] == org["department"].name
    assert add_member_response.json()["designation_name"] == org["designation"].name

    duplicate_response = client.post(
        f"/api/v1/teams/{team_id}/members",
        headers=headers,
        json={"employee_id": employee.id, "role": "Developer"},
    )
    assert duplicate_response.status_code == 400, duplicate_response.text
    assert duplicate_response.json()["detail"] == "Employee is already a member of this team"

    detail_response = client.get(f"/api/v1/teams/{team_id}", headers=headers)
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["team_lead_name"] == "Asha Member"
    assert detail["member_count"] == 1
    assert detail["members"][0]["employee_name"] == "Asha Member"

    update_response = client.put(
        f"/api/v1/teams/{team_id}",
        headers=headers,
        json={"name": "Delivery Team Updated TLIF", "code": "DELTLIF2"},
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["name"] == "Delivery Team Updated TLIF"

    remove_response = client.delete(
        f"/api/v1/teams/{team_id}/members/{employee.id}",
        headers=headers,
    )
    assert remove_response.status_code == 200, remove_response.text

    restore_response = client.post(
        f"/api/v1/teams/{team_id}/members",
        headers=headers,
        json={"employee_id": employee.id, "role": "Restored"},
    )
    assert restore_response.status_code == 200, restore_response.text
    assert restore_response.json()["role"] == "Restored"


def test_team_update_rejects_duplicate_code(client, db, test_user):
    org = create_org_setup(db, code_suffix="TDUP")
    test_user.company_id = org["company"].id
    db.add_all([
        Team(
            company_id=org["company"].id,
            department_id=org["department"].id,
            name="First TDUP",
            code="FIRSTTDUP",
            is_active=True,
        ),
        Team(
            company_id=org["company"].id,
            department_id=org["department"].id,
            name="Second TDUP",
            code="SECONDTDUP",
            is_active=True,
        ),
    ])
    db.commit()
    second = db.query(Team).filter(Team.code == "SECONDTDUP").first()

    headers = get_auth_headers(client, db, test_user, ["team.edit"])
    response = client.put(
        f"/api/v1/teams/{second.id}",
        headers=headers,
        json={"code": "FIRSTTDUP"},
    )

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Team code already exists"


def test_designation_list_returns_display_fields(client, db, test_user):
    org = create_org_setup(db, code_suffix="DESL")
    org["designation"].description = "Builds product interfaces"
    org["designation"].min_salary = 50000
    org["designation"].max_salary = 70000
    db.commit()

    headers = get_auth_headers(client, db, test_user, ["designation.view"])
    response = client.get("/api/v1/organizations/designations?page_size=100", headers=headers)

    assert response.status_code == 200, response.text
    item = next(
        designation
        for designation in response.json()["items"]
        if designation["id"] == org["designation"].id
    )

    assert item["department_name"] == org["department"].name
    assert item["description"] == "Builds product interfaces"
    assert item["min_salary"] == 50000
    assert item["max_salary"] == 70000
    assert item["employee_count"] == 0


def test_designation_list_filters_by_department(client, db, test_user):
    org = create_org_setup(db, code_suffix="DFLT")
    other_department = Department(
        company_id=org["company"].id,
        name="Operations DFLT",
        code="OPSDFLT",
        level=0,
    )
    db.add(other_department)
    db.flush()
    other_designation = Designation(
        name="Operations Lead DFLT",
        code="OPSLEADDFLT",
        department_id=other_department.id,
        level=3,
    )
    db.add(other_designation)
    db.commit()

    headers = get_auth_headers(client, db, test_user, ["designation.view"])
    response = client.get(
        f"/api/v1/organizations/designations?page_size=100&department_id={org['department'].id}",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    ids = {item["id"] for item in response.json()["items"]}
    assert org["designation"].id in ids
    assert other_designation.id not in ids
