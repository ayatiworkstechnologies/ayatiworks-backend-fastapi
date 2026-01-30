import sys
from app.database import SessionLocal
from app.models.auth import Role, Permission, RolePermission
from app.models.meta import MetaCredential, MetaCampaign, MetaLead # Ensure models created
from app.database import engine, Base

def fix_meta_permissions():
    # 1. Create Tables
    print("Creating Meta Ads Tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Fixing Meta Permissions...")
        
        # Get Client Role
        client_role = db.query(Role).filter_by(code="CLIENT").first()
        if not client_role:
            print("Error: CLIENT role not found!")
            return

        # Ensure Permissions Exist in DB
        new_perms = [
            {"code": "meta.view", "name": "View Meta Ads", "module": "meta"},
            {"code": "meta.manage", "name": "Manage Meta Ads", "module": "meta"},
        ]
        
        for p_data in new_perms:
            perm = db.query(Permission).filter_by(code=p_data["code"]).first()
            if not perm:
                perm = Permission(
                    name=p_data["name"],
                    code=p_data["code"],
                    module=p_data["module"],
                    description=f"Permission to {p_data['name']}",
                    is_active=True
                )
                db.add(perm)
                db.commit()
                db.refresh(perm)
                print(f"  + Created Permission: {p_data['code']}")

        # Assign to Client Role
        perms_to_assign = ["meta.view", "meta.manage"]
        target_roles = ["CLIENT", "ADMIN", "SUPER_ADMIN"]
        
        for role_code in target_roles:
            role = db.query(Role).filter_by(code=role_code).first()
            if not role:
                print(f"Warning: Role {role_code} not found")
                continue
                
            for p_code in perms_to_assign:
                perm = db.query(Permission).filter_by(code=p_code).first()
                if not db.query(RolePermission).filter_by(role_id=role.id, permission_id=perm.id).first():
                    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
                    print(f"  + Assigned {p_code} to {role_code}")
                else:
                    print(f"  . {p_code} already assigned to {role_code}")
        
        db.commit()
        print("Meta Permissions updated successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_meta_permissions()
