
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import attendance as _attendance  # noqa: F401
from app.models import blog as _blog  # noqa: F401
from app.models import client as _client  # noqa: F401
from app.models import client_module as _client_module  # noqa: F401
from app.models import communication as _communication  # noqa: F401
from app.models import company as _company  # noqa: F401
from app.models import hr_advanced as _hr_advanced  # noqa: F401
from app.models import invoice as _invoice  # noqa: F401
from app.models import leave as _leave  # noqa: F401
from app.models import media as _media  # noqa: F401
from app.models import meta as _meta  # noqa: F401
from app.models import notification as _notification  # noqa: F401
from app.models import organization as _organization  # noqa: F401
from app.models import payroll as _payroll  # noqa: F401
from app.models import project as _project  # noqa: F401
from app.models import report as _report  # noqa: F401
from app.models import settings as _settings  # noqa: F401
from app.models import sprint as _sprint  # noqa: F401
from app.models import team as _team  # noqa: F401
from app.models import ticket as _ticket  # noqa: F401
from app.models.auth import Role, Permission, RolePermission
from app.models.employee import Employee  # noqa: F401 - ensure mapper registration
from app.models.organization import Department, Designation  # noqa: F401 - ensure mapper registration
from app.models.team import TeamMember  # noqa: F401 - ensure mapper registration
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
            "SUPER_ADMIN": all_perm_codes,
            "ADMIN": all_perm_codes,
            "MANAGER": mgr_perms,
            "EMPLOYEE": emp_perms,
            "MEMBER": emp_perms, # Alias for member
        }
        
        # 3. Apply
        for role_code, perm_codes in roles_config.items():
            role = db.query(Role).filter(Role.code == role_code).first()
            if not role:
                # Only create if standard roles missing. 
                # For 'member', it might be default.
                print(f"Creating role: {role_code}")
                role = Role(name=role_code.replace('_', ' ').title(), code=role_code, is_system=True)
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
