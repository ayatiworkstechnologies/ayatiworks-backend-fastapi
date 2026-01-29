
import httpx
import time

BASE_URL = "http://localhost:8001/api/v1"
ADMIN_EMAIL = "admin@demo.com"
ADMIN_PASSWORD = "admin123"

def run():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    
    print("1. Login...")
    resp = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return
    
    data = resp.json()
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login OK.")
    
    # Skip Organization
    
    print("\n--- 5. Projects & Tasks ---")
    proj_data = {
        "name": f"Test Project {int(time.time())}",
        "code": f"PRJ-{int(time.time())}",
        "start_date": "2026-01-01",
        "status": "active"
    }
    try:
        resp = client.post("/projects", json=proj_data, headers=headers)
        print(f"Create Project Status: {resp.status_code}")
        if resp.status_code in [200, 201]:
            print("Project Created")
            proj_id = resp.json()["id"]
            
            task_data = {
                "project_id": proj_id,
                "title": "Initial Setup",
                "priority": "high",
                "start_date": "2026-01-01"
            }
            resp = client.post("/projects/tasks", json=task_data, headers=headers)
            print(f"Create Task Status: {resp.status_code}")
    except Exception as e:
        print(f"Project Error: {e}")

    print("\n--- 6. CRM (Clients) ---")
    client_data = {
        "name": f"Acme Corp {int(time.time())}",
        "email": "contact@acme.com",
        "status": "active"
    }
    try:
        resp = client.post("/clients", json=client_data, headers=headers)
        print(f"Create Client Status: {resp.status_code}")
    except Exception as e:
        print(f"CRM Error: {e}")

    print("\n--- 7. Content (Blog) ---")
    blog_data = {
        "title": f"New Release {int(time.time())}",
        "slug": f"new-release-{int(time.time())}",
        "content": "This is a dummy post.",
        "status": "published"
    }
    try:
        resp = client.post("/blogs", json=blog_data, headers=headers)
        print(f"Create Blog Status: {resp.status_code}")
    except Exception as e:
        print(f"CMS Error: {e}")

if __name__ == "__main__":
    run()
