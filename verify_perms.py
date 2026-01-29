from app.database import SessionLocal, engine
from app.models.auth import Permission, Role, RolePermission
from sqlalchemy.orm import joinedload
import logging

# Disable SQL logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

def check_perms():
    db = SessionLocal()
    try:
        # Check permissions existence
        print("checking permissions...")
        perms = db.query(Permission).filter(Permission.module == "team").all()
        print(f"Found {len(perms)} team permissions:")
        for p in perms:
            print(f" - {p.code} ({p.name})")

        print("\nChecking Role Assignments:")
        roles = db.query(Role).all()
        for role in roles:
            # Get permissions for this role
            role_perms = db.query(RolePermission).filter(RolePermission.role_id == role.id).all()
            perm_ids = [rp.permission_id for rp in role_perms]
            
            # Count team perms
            team_perms_count = 0
            has_team_perms = []
            
            for p in perms:
                if p.id in perm_ids:
                    team_perms_count += 1
                    has_team_perms.append(p.code.replace('team.', ''))
            
            if team_perms_count > 0:
                print(f"Role: {role.name} ({role.code}) has {team_perms_count} team perms: {', '.join(has_team_perms)}")
            else:
                 if role.code in ['ADMIN', 'MANAGER', 'HR', 'EMPLOYEE']:
                    print(f"Role: {role.name} ({role.code}) has NO team perms!")

    except Exception as e:
        print(e)
    finally:
        db.close()

if __name__ == "__main__":
    check_perms()
