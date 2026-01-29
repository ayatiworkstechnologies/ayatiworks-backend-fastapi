
import sys
from datetime import datetime, date, time, timedelta
from app.database import SessionLocal
from app.models.auth import User, Role, Permission, RolePermission
from app.models.company import Company, Branch
from app.models.employee import Employee, EmploymentStatus, EmploymentType
from app.models.organization import Department, Designation
from app.models.leave import LeaveType
from app.models.attendance import Shift
from app.core.permissions import get_all_permissions, PermissionCode
from app.core.security import hash_password

def seed_db():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("SEEDING DATABASE - COMPLETE DEMO DATA")
        print("=" * 60)
        
        # 1. Company
        print("\nStep 1: Creating Company...")
        company = db.query(Company).filter_by(code="DEMO").first()
        if not company:
            company = Company(
                name="Ayatoworks",
                code="DEMO",
                email="admin@ayatoworks.com",
                subscription_plan="enterprise",
                is_active=True
            )
            db.add(company)
            db.commit()
            db.refresh(company)
            print("  Created Company: Ayatoworks")
        else:
            # Update existing company
            company.name = "Ayatoworks"
            company.email = "admin@ayatoworks.com"
            db.commit()
            print("  Updated Company: Ayatoworks")
        
        # 2. Branch
        print("\nStep 2: Creating Branch...")
        branch = db.query(Branch).filter_by(code="HQ").first()
        if not branch:
            branch = Branch(
                company_id=company.id,
                name="Chennai HQ",
                code="HQ",
                city="Chennai",
                country="India",
                is_active=True
            )
            db.add(branch)
            db.commit()
            db.refresh(branch)
            print("  Created Branch: Chennai HQ")
        else:
            # Update existing branch
            branch.name = "Chennai HQ"
            branch.city = "Chennai"
            branch.country = "India"
            db.commit()
            print("  Updated Branch: Chennai HQ")
            
        # 3. Permissions
        print("\nStep 3: Seeding Permissions...")
        all_perms = get_all_permissions()
        if not any(p["code"] == PermissionCode.SUPER_ADMIN.value for p in all_perms):
            all_perms.append({"code": PermissionCode.SUPER_ADMIN.value, "name": "Super Admin Access", "module": "admin"})

        perm_map = {}
        perm_created = 0
        
        for p_data in all_perms:
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
                perm_created += 1
            perm_map[p_data["code"]] = perm.id
        
        print(f"  Permissions in database: {len(perm_map)} ({perm_created} newly created)")
            
        # 4. Roles
        print("\nStep 4: Creating Roles...")
        roles_data = [
            {"name": "Super Admin", "code": "SUPER_ADMIN", "scope": "global", "is_system": True},
            {"name": "Admin", "code": "ADMIN", "scope": "company", "is_system": True},
            {"name": "Manager", "code": "MANAGER", "scope": "company", "is_system": False},
            {"name": "HR Manager", "code": "HR", "scope": "company", "is_system": False},
            {"name": "Employee", "code": "EMPLOYEE", "scope": "company", "is_system": True},
            {"name": "Client", "code": "CLIENT", "scope": "company", "is_system": True},
        ]
        
        role_map = {}
        
        for r_data in roles_data:
            role = db.query(Role).filter_by(code=r_data["code"]).first()
            if not role:
                role = Role(
                    name=r_data["name"],
                    code=r_data["code"],
                    scope=r_data["scope"],
                    is_system=r_data["is_system"],
                    company_id=company.id if r_data["scope"] == "company" else None,
                    is_active=True
                )
                db.add(role)
                db.commit()
                db.refresh(role)
                print(f"  Created Role: {role.name}")
            else:
                print(f"  Role already exists: {r_data['name']}")
            role_map[r_data["code"]] = role
        
        # 5. Assign Permissions to Roles (Simplified for brevity, ensuring key roles have permissions)
        print("\nStep 5: Assigning Permissions...")
        
        # SUPER ADMIN & ADMIN
        for role_code in ["SUPER_ADMIN", "ADMIN"]:
            role = role_map[role_code]
            if role_code == "SUPER_ADMIN":
                # Super admin gets SUPER_ADMIN permission
                 if not db.query(RolePermission).filter_by(role_id=role.id, permission_id=perm_map[PermissionCode.SUPER_ADMIN.value]).first():
                    db.add(RolePermission(role_id=role.id, permission_id=perm_map[PermissionCode.SUPER_ADMIN.value]))
            else:
                # Admin gets ALL permissions except super_admin
                for p_code, p_id in perm_map.items():
                    if p_code != PermissionCode.SUPER_ADMIN.value:
                        if not db.query(RolePermission).filter_by(role_id=role.id, permission_id=p_id).first():
                            db.add(RolePermission(role_id=role.id, permission_id=p_id))
        
        # MANAGER - Key permissions
        manager_perms = [
            PermissionCode.DASHBOARD_VIEW, PermissionCode.PROJECT_VIEW_ALL, PermissionCode.TASK_VIEW_ALL, 
            PermissionCode.EMPLOYEE_VIEW, PermissionCode.TEAM_VIEW, PermissionCode.REPORT_VIEW
        ]
        for p_enum in manager_perms:
            if p_enum.value in perm_map:
                if not db.query(RolePermission).filter_by(role_id=role_map["MANAGER"].id, permission_id=perm_map[p_enum.value]).first():
                     db.add(RolePermission(role_id=role_map["MANAGER"].id, permission_id=perm_map[p_enum.value]))

        # EMPLOYEE - Basic permissions
        employee_perms = [
            PermissionCode.DASHBOARD_VIEW, PermissionCode.PROJECT_VIEW, PermissionCode.TASK_VIEW,
            PermissionCode.EMPLOYEE_VIEW, PermissionCode.LEAVE_VIEW, PermissionCode.LEAVE_APPLY,
            PermissionCode.ATTENDANCE_VIEW, PermissionCode.ATTENDANCE_MARK
        ]
        for p_enum in employee_perms:
             if p_enum.value in perm_map:
                if not db.query(RolePermission).filter_by(role_id=role_map["EMPLOYEE"].id, permission_id=perm_map[p_enum.value]).first():
                     db.add(RolePermission(role_id=role_map["EMPLOYEE"].id, permission_id=perm_map[p_enum.value]))

        db.commit()

        # 6. Departments & Designations
        print("\nStep 6: Creating Departments & Designations...")
        
        depts_data = {
            "Management": ["CEO", "CTO", "CFO", "COO", "Director"],
            "Engineering": ["VP of Engineering", "Engineering Manager", "Tech Lead", "Senior Backend Developer", "Senior Frontend Developer", "Backend Developer", "Frontend Developer", "DevOps Engineer", "QA Engineer"],
            "Design": ["Head of Design", "Senior Product Designer", "UI/UX Designer", "Graphic Designer"],
            "Product": ["Head of Product", "Senior Product Manager", "Product Manager", "Business Analyst"],
            "Marketing": ["Head of Marketing", "Marketing Manager", "Content Strategist", "SEO Specialist", "Social Media Manager"],
            "Sales": ["Head of Sales", "Sales Manager", "Account Executive", "Sales Representative"],
            "HR": ["Head of HR", "HR Manager", "Talent Acquisition Specialist", "HR Executive"],
            "Finance": ["Finance Manager", "Senior Accountant", "Accountant"],
            "Operations": ["Operations Manager", "Office Administrator"]
        }
        
        dept_map = {}
        desig_map = {}
        
        for d_name, designations in depts_data.items():
            # Create Department
            dept = db.query(Department).filter_by(name=d_name, company_id=company.id).first()
            if not dept:
                dept = Department(name=d_name, code=d_name[:3].upper(), company_id=company.id)
                db.add(dept)
                db.commit()
                db.refresh(dept)
                print(f"  Created Dept: {d_name}")
            else:
                print(f"  Dept exists: {d_name}")
            dept_map[d_name] = dept
            
            # Create Designations
            for des_name in designations:
                 desig = db.query(Designation).filter_by(name=des_name, department_id=dept.id).first()
                 if not desig:
                     # Generate a somewhat unique code
                     code_prefix = d_name[:3].upper()
                     code_suffix = "".join([w[0] for w in des_name.split() if w[0].isupper()])
                     code = f"{code_prefix}-{code_suffix}"[:10]
                     
                     desig = Designation(
                         name=des_name, 
                         code=code, 
                         department_id=dept.id
                     )
                     db.add(desig)
                     db.commit()
                     db.refresh(desig)
                     # print(f"    + Designation: {des_name}") # Optional logging
                 desig_map[des_name] = desig
                 
        # 7. Create Users AND Employees
        print("\nStep 7: Creating Users & Employees...")
        
        # Define users to create
        users_to_create = [
            {
                "email": "admin@ayatoworks.com", "password": "admin123", "role": "SUPER_ADMIN", 
                "first": "Super", "last": "Admin", "dept": "Management", "desig": "CEO"
            },
            {
                "email": "admin1@ayatoworks.com", "password": "admin123", "role": "ADMIN", 
                "first": "Tech", "last": "Admin", "dept": "Management", "desig": "CTO"
            },
           
        ]
        
        for u_data in users_to_create:
            # 1. Create User
            user = db.query(User).filter_by(email=u_data["email"]).first()
            if not user:
                user = User(
                    email=u_data["email"],
                    password_hash=hash_password(u_data["password"]),
                    first_name=u_data["first"],
                    last_name=u_data["last"],
                    role_id=role_map[u_data["role"]].id,
                    company_id=company.id,
                    branch_id=branch.id,
                    is_active=True,
                    is_verified=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                print(f"  Created User: {user.email}")
            
            # 2. Create Employee Profile (if not exists)
            employee = db.query(Employee).filter_by(user_id=user.id).first()
            if not employee:
                # Find department and designation IDs
                dept = dept_map.get(u_data["dept"])
                desig = desig_map.get(u_data["desig"])
                
                employee = Employee(
                    user_id=user.id,
                    employee_code=f"EMP{user.id:03d}",
                    company_id=company.id,
                    branch_id=branch.id,
                    department_id=dept.id if dept else None,
                    designation_id=desig.id if desig else None,
                    joining_date=date.today() - timedelta(days=365), # Joined 1 year ago
                    employment_status=EmploymentStatus.ACTIVE.value, # Status is stored as string in model, using value
                    employment_type=EmploymentType.FULL_TIME.value
                )
                db.add(employee)
                db.commit()
                print(f"    -> Linked Employee Profile: {u_data['dept']} / {u_data['desig']}")
        
        # 8. Create Client User & Profile
        print("\nStep 8: Creating Client...")
        client_email = "client@demo.com"
        client_user = db.query(User).filter_by(email=client_email).first()
        if not client_user:
             client_user = User(
                email=client_email,
                password_hash=hash_password("client123"),
                first_name="Demo",
                last_name="Client",
                role_id=role_map["CLIENT"].id,
                company_id=company.id,
                branch_id=branch.id,
                is_active=True,
                is_verified=True
            )
             db.add(client_user)
             db.commit()
             db.refresh(client_user)
             print(f"  Created User: {client_email}")
        
        # Client Profile
        from app.models.client import Client
        client_profile = db.query(Client).filter_by(email=client_email).first()
        if not client_profile:
             client_profile = Client(
                 name="Acme Corp",
                 email=client_email,
                 phone="555-0199",
                 company_id=company.id,
                 address="123 Client St",
                 status="active",
                 user_id=client_user.id # Link to user if your model supports it, otherwise separate
             )
             db.add(client_profile)
             db.commit()
             print("    -> Created Client Profile: Acme Corp")

        print("\n" + "=" * 60)
        print("DATABASE SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nDEMO CREDENTIALS:")
        print("-" * 60) 
        print(f"  {'ROLE':<15} | {'EMAIL':<25} | {'PASSWORD'}")
        print("-" * 60)
        for u in users_to_create:
             print(f"  {u['role']:<15} | {u['email']:<25} | {u['password']}")
        print(f"  {'CLIENT':<15} | {'client@demo.com':<25} | client123")
        print("-" * 60)
    except Exception as e:
        print(f"\nError seeding database: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
