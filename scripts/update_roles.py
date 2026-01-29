
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.auth import Role, Permission, RolePermission
from app.core.permissions import get_all_permissions

def update_roles():
    db = SessionLocal()
    try:
        print("Syncing permissions...")
        defined_perms = get_all_permissions()
        
        # 1. Sync Permissions
        for perm_data in defined_perms:
            perm = db.query(Permission).filter(Permission.code == perm_data["code"]).first()
            if not perm:
                perm = Permission(
                    code=perm_data["code"],
                    name=perm_data["name"],
                    module=perm_data["module"]
                )
                db.add(perm)
            else:
                perm.name = perm_data["name"]
                perm.module = perm_data["module"]
        
        db.commit()
        
        # Build Map
        all_perms_map = {p.code: p for p in db.query(Permission).all()}
        all_perm_codes = list(all_perms_map.keys())
        
        # 2. Define Configurations
        
        # Employee Permissions
        emp_perms = [
            "dashboard.view", # Logic: dashboard access
            "project.view",
            "task.view", "task.create",
            "attendance.view", "attendance.mark",
            "leave.view", "leave.apply",
            "settings.view",
            "employee.view"
        ]
        
        # Manager Permissions (Employee + Manage/Assign)
        mgr_perms = emp_perms + [
             "project.view_all", "project.create", "project.edit", "project.delete",
             "task.view_all", "task.edit", "task.delete", "task.assign",
             "attendance.view_all", "attendance.approve", "attendance.edit",
             "leave.view_all", "leave.approve", "leave.cancel",
             "employee.view_all", 
             "report.view", "report.create", "report.export",
             "client.view", "client.create", "client.edit",
             "lead.view", "lead.create", "lead.edit",
             "invoice.view", "invoice.create", "invoice.edit"
        ]
        
        roles_config = {
            "super_admin": all_perm_codes,
            "admin": all_perm_codes,
            "manager": mgr_perms,
            "employee": emp_perms,
            "member": emp_perms # Alias for member
        }
        
        # 3. Apply
        for role_code, perm_codes in roles_config.items():
            role = db.query(Role).filter(Role.code == role_code).first()
            if not role:
                # Only create if standard roles missing. 
                # For 'member', it might be default.
                print(f"Creating role: {role_code}")
                role = Role(name=role_code.replace('_', ' ').title(), code=role_code)
                db.add(role)
                db.commit()
            
            # clear existing
            db.query(RolePermission).filter(RolePermission.role_id == role.id).delete()
            
            # add new
            count = 0
            for p in perm_codes:
                if p in all_perms_map:
                    db.add(RolePermission(role_id=role.id, permission_id=all_perms_map[p].id))
                    count += 1
            
            print(f"Updated {role_code} with {count} permissions.")
            
        db.commit()
        print("Roles updated successfully.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_roles()
