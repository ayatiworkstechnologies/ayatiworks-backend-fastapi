import sys
import os

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import SessionLocal
from app.core.permissions import PermissionCode

def update_admin_permissions():
    db = SessionLocal()
    try:
        print("Checking admin role permissions...")
        
        # SQL to find the admin role
        result = db.execute(text("SELECT id, name FROM roles WHERE name = 'admin'"))
        admin_role = result.fetchone()
        
        if not admin_role:
            print("Admin role not found!")
            return

        role_id = admin_role[0]
        print(f"Found admin role ID: {role_id}")

        # Permissions to ensure
        required_perms = [
            "client.view", "client.create", "client.edit", "client.delete",
        ]

        for perm_code in required_perms:
            # Check if permission exists in permissions table
            perm_check = db.execute(text("SELECT id FROM permissions WHERE code = :code"), {"code": perm_code}).fetchone()
            if not perm_check:
                print(f"Creating permission {perm_code}...")
                db.execute(text("INSERT INTO permissions (code, name, module) VALUES (:code, :name, :module)"), 
                           {"code": perm_code, "name": f"Manage {perm_code}", "module": "client"})
                perm_id = db.execute(text("SELECT id FROM permissions WHERE code = :code"), {"code": perm_code}).fetchone()[0]
            else:
                perm_id = perm_check[0]

            # Check if role has this permission
            role_perm = db.execute(text("SELECT * FROM role_permissions WHERE role_id = :rid AND permission_id = :pid"), 
                                   {"rid": role_id, "pid": perm_id}).fetchone()
            
            if not role_perm:
                print(f"Adding {perm_code} to admin role...")
                db.execute(text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:rid, :pid)"), 
                           {"rid": role_id, "pid": perm_id})
            else:
                print(f"Admin already has {perm_code}")

        db.commit()
        print("Permissions updated successfully!")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_admin_permissions()
