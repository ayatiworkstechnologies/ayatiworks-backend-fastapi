import sys
from app.database import SessionLocal
from app.models.auth import Role, Permission, RolePermission
from app.core.permissions import PermissionCode

def fix_permissions():
    db = SessionLocal()
    try:
        print("Fixing Client Permissions...")
        
        # Get Client Role
        client_role = db.query(Role).filter_by(code="CLIENT").first()
        if not client_role:
            print("Error: CLIENT role not found!")
            return

        # Permissions to assign
        perms_to_assign = [
            "dashboard.view",
            "project.view_own",
            "invoice.view_own",
            "client.view_own",
            "lead.view",
            "task.view"
        ]

        for p_code in perms_to_assign:
            # Get Permission ID
            perm = db.query(Permission).filter_by(code=p_code).first()
            if not perm:
                print(f"Warning: Permission {p_code} not found in DB.")
                continue
            
            # Check if exists
            exists = db.query(RolePermission).filter_by(
                role_id=client_role.id,
                permission_id=perm.id
            ).first()
            
            if not exists:
                db.add(RolePermission(role_id=client_role.id, permission_id=perm.id))
                print(f"  + Assigned {p_code}")
            else:
                print(f"  . {p_code} already assigned")
        
        db.commit()
        print("Permissions updated successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_permissions()
