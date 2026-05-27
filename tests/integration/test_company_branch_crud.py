"""
Integration tests for company and branch CRUD flows.
"""

from tests.integration.helpers import get_auth_headers


def test_company_and_branch_crud_flow(client, db, test_user):
    headers = get_auth_headers(
        client,
        db,
        test_user,
        [
            "company.view",
            "company.create",
            "company.edit",
            "company.delete",
            "branch.view",
            "branch.create",
            "branch.edit",
            "branch.delete",
        ],
    )

    create_company = client.post(
        "/api/v1/companies",
        headers=headers,
        json={
            "name": "Acme Corp",
            "code": "ACME",
            "email": "hello@acme.example.com",
            "city": "Bengaluru",
            "country": "India",
            "timezone": "Asia/Kolkata",
            "currency": "INR",
            "date_format": "YYYY-MM-DD",
        },
    )
    assert create_company.status_code == 201, create_company.text
    company = create_company.json()
    company_id = company["id"]
    assert company["name"] == "Acme Corp"
    assert company["code"] == "ACME"

    list_companies = client.get("/api/v1/companies", headers=headers)
    assert list_companies.status_code == 200, list_companies.text
    assert list_companies.json()["total"] >= 1

    get_company = client.get(f"/api/v1/companies/{company_id}", headers=headers)
    assert get_company.status_code == 200, get_company.text
    assert get_company.json()["id"] == company_id

    update_company = client.put(
        f"/api/v1/companies/{company_id}",
        headers=headers,
        json={"name": "Acme Updated", "phone": "+91-9999999999"},
    )
    assert update_company.status_code == 200, update_company.text
    updated_company = update_company.json()
    assert updated_company["name"] == "Acme Updated"
    assert updated_company["phone"] == "+91-9999999999"

    create_branch = client.post(
        "/api/v1/branches",
        headers=headers,
        json={
            "company_id": company_id,
            "name": "HQ",
            "code": "HQ",
            "email": "hq@acme.example.com",
            "city": "Bengaluru",
            "country": "India",
            "geo_fence_radius": 150,
        },
    )
    assert create_branch.status_code == 201, create_branch.text
    branch = create_branch.json()
    branch_id = branch["id"]
    assert branch["company_id"] == company_id

    get_branch = client.get(f"/api/v1/branches/{branch_id}", headers=headers)
    assert get_branch.status_code == 200, get_branch.text
    assert get_branch.json()["id"] == branch_id

    update_branch = client.put(
        f"/api/v1/branches/{branch_id}",
        headers=headers,
        json={"city": "Mumbai", "geo_fence_radius": 250},
    )
    assert update_branch.status_code == 200, update_branch.text
    updated_branch = update_branch.json()
    assert updated_branch["city"] == "Mumbai"
    assert updated_branch["geo_fence_radius"] == 250

    delete_branch = client.delete(f"/api/v1/branches/{branch_id}", headers=headers)
    assert delete_branch.status_code == 200, delete_branch.text

    delete_company = client.delete(f"/api/v1/companies/{company_id}", headers=headers)
    assert delete_company.status_code == 200, delete_company.text
