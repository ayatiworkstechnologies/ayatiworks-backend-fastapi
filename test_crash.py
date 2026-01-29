
import httpx

BASE_URL = "http://localhost:8001/api/v1"
ADMIN_EMAIL = "admin@demo.com"
ADMIN_PASSWORD = "admin123"

def run():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    
    print("1. Login...", flush=True)
    resp = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}", flush=True)
        return
    
    data = resp.json()
    token = data["access_token"]
    cid = data["user"]["company_id"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"Login OK. Company ID: {cid}", flush=True)
    
    print(f"2. Get Company {cid}...", flush=True)
    try:
        resp = client.get(f"/companies/{cid}", headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text[:500]}")
    except Exception as e:
        print(f"Crash/Error Company: {e}")

    print("3. Get Departments...")
    try:
        resp = client.get("/departments", headers=headers)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
             print(f"Count: {len(resp.json().get('items', []))}")
    except Exception as e:
        print(f"Crash/Error Departments: {e}")

    print("4. Get Designations...")
    desig_id = None
    try:
        resp = client.get("/departments/designations", headers=headers)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
             items = resp.json().get('items', [])
             if items:
                 desig_id = items[0]["id"]
    except Exception as e:
        print(f"Crash/Error Designations: {e}")

    print("5. Create Employee...")
    try:
        from datetime import date
        import time
        emp_code = f"E{int(time.time())}"
        emp_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": f"john.doe.{int(time.time())}@example.com",
            "joining_date": str(date.today()),
            "company_id": cid,
            "employee_code": emp_code,
            "employment_type": "full_time",
            "work_mode": "office",
            "salary": 50000
        }
        if desig_id:
             emp_data["designation_id"] = desig_id
             # Department?
             # Need department id.
             # I'll fetch departments again or use from Step 3
             pass
        
        # Helper to get dept
        resp = client.get("/departments", headers=headers)
        if resp.status_code==200 and resp.json().get("items"):
             emp_data["department_id"] = resp.json()["items"][0]["id"]

        resp = client.post("/employees", json=emp_data, headers=headers)
        print(f"Status: {resp.status_code}")
        # print(f"Body: {resp.text[:200]}")
    except Exception as e:
        print(f"Crash/Error Employee: {e}")

if __name__ == "__main__":
    run()
