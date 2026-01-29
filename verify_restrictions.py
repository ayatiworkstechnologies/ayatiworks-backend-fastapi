
import sys
import os
import requests

# Add backend directory to sys.path to ensure we can import if needed, 
# but for this script we will use requests to hit the running API.
# Assume API is running on localhost:8000

BASE_URL = "http://localhost:8000/api/v1"

def login(email, password):
    response = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        print(f"Failed to login as {email}: {response.text}")
        return None

def check_projects(token, role_name):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/projects", headers=headers)
    if response.status_code == 200:
        data = response.json()
        count = data['total']
        print(f"[{role_name}] Visible Projects: {count}")
        return count
    else:
        print(f"[{role_name}] Failed to get projects: {response.text}")
        return -1

def check_tasks(token, role_name):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/tasks", headers=headers)
    if response.status_code == 200:
        data = response.json()
        count = data['total']
        print(f"[{role_name}] Visible Tasks: {count}")
        return count
    else:
        print(f"[{role_name}] Failed to get tasks: {response.text}")
        return -1

def main():
    print("="*60)
    print("VERIFYING DATA ACCESS RESTRICTIONS")
    print("="*60)

    # 1. Test Admin Access
    print("\n1. Testing Admin Access...")
    admin_token = login("admin@demo.com", "admin123")
    if admin_token:
        admin_projects = check_projects(admin_token, "Admin")
        admin_tasks = check_tasks(admin_token, "Admin")
    else:
        print("Skipping Admin tests due to login failure.")
        return

    # 2. Test Employee Access
    print("\n2. Testing Employee Access...")
    # Using 'employee@demo.com' which is a standard employee
    emp_token = login("employee@demo.com", "employee123")
    if emp_token:
        emp_projects = check_projects(emp_token, "Employee")
        emp_tasks = check_tasks(emp_token, "Employee")
        
        # Verification Logic
        print("\n" + "-"*30)
        print("RESULTS")
        print("-"*30)
        
        if admin_projects > emp_projects:
             print(f"✅ SUCCESS: Admin sees more projects ({admin_projects}) than Employee ({emp_projects})")
        elif admin_projects == emp_projects and emp_projects == 0:
             print(f"⚠️  WARNING: Both see 0 projects. Create some data to test properly.")
        else:
             print(f"❌ FAILURE: Admin ({admin_projects}) and Employee ({emp_projects}) see same number of projects (or Employee sees more).")

        if admin_tasks > emp_tasks:
             print(f"✅ SUCCESS: Admin sees more tasks ({admin_tasks}) than Employee ({emp_tasks})")
        elif admin_tasks == emp_tasks and emp_tasks == 0:
             print(f"⚠️  WARNING: Both see 0 tasks. Create some data to test properly.")
        else:
             print(f"❌ FAILURE: Admin ({admin_tasks}) and Employee ({emp_tasks}) see same number of tasks (or Employee sees more).")
             
    else:
        print("Skipping Employee tests due to login failure.")

if __name__ == "__main__":
    main()
