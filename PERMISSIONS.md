# Role-Based Permissions System Documentation

This document provides comprehensive documentation for the role-based access control (RBAC) system implemented in the backend.

## Overview

The system implements 6 distinct roles with granular permission control across all modules. Each role has specific CRUD permissions designed for their responsibilities.

## Roles

### 1. Super Admin

- **Code**: `SUPER_ADMIN`
- **Scope**: Global
- **Access**: Full unrestricted access to all system features
- **Permission**: `SUPER_ADMIN` permission grants all access automatically
- **Use Case**: System administrators, platform owners

### 2. Admin  

- **Code**: `ADMIN`
- **Scope**: Company
- **Access**: All features except system-level configuration
- **Permissions**: All permissions except `SUPER_ADMIN`
- **Use Case**: Company administrators, IT managers

### 3. Manager

- **Code**: `MANAGER`
- **Scope**: Company
- **Access**: Project, task, and team management with approval authority
- **Use Case**: Project managers, team leads

### 4. HR Manager

- **Code**: `HR`
- **Scope**: Company
- **Access**: Employee, leave, attendance, and payroll management
- **Use Case**: Human resources staff

### 5. Employee

- **Code**: `EMPLOYEE`
- **Scope**: Company
- **Access**: View own data, basic operations
- **Use Case**: Regular team members, staff

### 6. Client

- **Code**: `CLIENT`
- **Scope**: Company
- **Access**: View assigned projects, tasks, and invoices only
- **Use Case**: External clients, customers

## Permission Matrix

| Module | Permission | Super Admin | Admin | Manager | HR | Employee | Client |
|--------|-----------|:-----------:|:-----:|:-------:|:--:|:--------:|:------:|
| **Dashboard** |
| | view | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Users & Roles** |
| | view | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| | create/edit/delete | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| **Company & Branches** |
| | view | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| | create/edit/delete | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| **Departments** |
| | view | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| | create/edit | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| | delete | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| **Employees** |
| | view_all | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| | view own | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| | create/edit/delete | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| **Attendance** |
| | view_all | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| | view own | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| | mark | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| | edit | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| | approve | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| **Leave** |
| | view_all | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| | view own | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| | apply | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| | approve | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| | cancel | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| **Holidays** |
| | view | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| | manage | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| **Shifts** |
| | view | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| | manage | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| **Payroll** |
| | view_all | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| | view own | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| | manage | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| **Salary** |
| | view_all | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| | view own | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| | create/edit/delete | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| | approve | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| **Projects** |
| | view_all | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| | view assigned | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| | create/edit/delete | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Tasks** |
| | view_all | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| | view assigned | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| | create/edit/delete | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| | assign | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| | update status (own) | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| **Clients** |
| | view | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| | view own profile | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| | create/edit/delete | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Leads & Deals** |
| | view | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| | create/edit | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| | delete | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| **Invoices** |
| | view all | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| | view own | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| | create/edit/delete | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Timesheet** |
| | view_all | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| | view own | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| | create | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| | approve | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Reports** |
| | view/export/create | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| **Settings** |
| | view/edit | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| **Audit Logs** |
| | view |✓ | ✓ | ✗ | ✗ | ✗ | ✗ |

## How to Protect API Endpoints

### Basic Permission Checker

Use the `PermissionChecker` dependency on any endpoint:

```python
from app.api.deps import PermissionChecker

@router.post("/employees", response_model=EmployeeResponse)
def create_employee(
    data: EmployeeCreate,
    current_user: User = Depends(PermissionChecker("employee.create")),
    db: Session = Depends(get_db)
):
    # Only users with employee.create permission can reach here
    ...
```

### Multiple Permissions (OR Logic)

Use `require_any_permission` when user needs ANY of the listed permissions:

```python
from app.api.deps import require_any_permission

@router.get("/projects", response_model=List[ProjectResponse])
def list_projects(
    current_user: User = Depends(require_any_permission([
        "project.view",
        "project.view_all"
    ])),
    db: Session = Depends(get_db)
):
    # User needs either project.view OR project.view_all
    ...
```

### Multiple Permissions (AND Logic)

Use `require_all_permissions` when user needs ALL listed permissions:

```python
from app.api.deps import require_all_permissions

@router.put("/projects/{id}/finalize")
def finalize_project(
    project_id: int,
    current_user: User = Depends(require_all_permissions([
        "project.edit",
        "project.approve"
    ])),
    db: Session = Depends(get_db)
):
    # User must have both project.edit AND project.approve
    ...
```

### Admin Only

Use `get_current_active_superuser` for admin-only operations:

```python
from app.api.deps import get_current_active_superuser

@router.post("/settings/system")
def update_system_settings(
    current_user: User = Depends(get_current_active_superuser),
    db: Session = Depends(get_db)
):
    # Only SUPER_ADMIN and ADMIN roles can access
    ...
```

### Manual Permission Check

For complex logic, manually check permissions:

```python
from app.api.deps import get_current_active_user, get_user_permissions
from app.core.permissions import check_permission

@router.get("/data")
def get_data(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    user_perms = get_user_permissions(current_user, db)
    
    if check_permission(user_perms, "data.view_all"):
        # Return all data
        return db.query(Data).all()
    elif check_permission(user_perms, "data.view"):
        # Return only user's data
        return db.query(Data).filter_by(user_id=current_user.id).all()
    else:
        raise HTTPException(status_code=403, detail="Access denied")
```

## Creating Custom Roles

### Via API

```bash
# Create a role
POST /api/v1/roles
{
  "name": "Sales Manager",
  "code": "SALES_MGR",
  "description": "Sales team manager role",
  "scope": "company",
  "company_id": 1,
  "permission_ids": [1, 2, 3, 15, 16, 17]
}

# Update role permissions
PUT /api/v1/roles/7/permissions
{
  "add_permission_ids": [20, 21],
  "remove_permission_ids": [3]
}
```

### Via Database Seed

```python
# Add to roles_data in seed.py
{"name": "Sales Manager", "code": "SALES_MGR", "scope": "company", "is_system": False}

# Assign permissions
sales_mgr_role = role_map["SALES_MGR"]
sales_mgr_perms = [
    Permission Code.CLIENT_VIEW,
    PermissionCode.LEAD_VIEW, PermissionCode.LEAD_CREATE, PermissionCode.LEAD_EDIT,
    PermissionCode.DEAL_VIEW, PermissionCode.DEAL_CREATE, PermissionCode.DEAL_EDIT,
]
for p_enum in sales_mgr_perms:
    # Add to role...
```

## Testing Different Roles

### Test User Credentials

After running `python seed.py`, these test users are available:

```
SUPER_ADMIN    | admin@demo.com       | admin123
ADMIN          | admin2@demo.com      | admin123
MANAGER        | manager@demo.com     | manager123
HR             | hr@demo.com          | hr123
EMPLOYEE       | employee@demo.com    | employee123
CLIENT         | client@demo.com      | client123
```

### Login and Test

```bash
# Login as manager
POST /api/v1/auth/login
{
  "email": "manager@demo.com",
  "password": "manager123"
}

# Use returned token
GET /api/v1/projects
Authorization: Bearer <token>

# Should succeed - Manager has project.view_all

GET /api/v1/employees/create
Authorization: Bearer <token>

# Should fail - Manager does not have employee.create
```

### Check User Permissions

```bash
# Get my permissions
GET /api/v1/permissions/my-permissions
Authorization: Bearer <token>

# Check specific permission
POST /api/v1/permissions/check
{
  "permission_code": "project.create"
}
```

## Permission Codes Reference

### Format

Permissions follow the format: `{module}.{action}`

### Common Actions

- `view` - View own data
- `view_all` - View all records
- `view_own` - View own records (for clients)
- `create` - Create new records
- `edit` - Modify existing records
- `delete` - Delete records
- `manage` - Full management access
- `approve` - Approval authority
- `assign` - Assignment capability

### Full List

See `app/core/permissions.py` PermissionCode enum for complete list.

## Best Practices

1. **Principle of Least Privilege**: Assign minimum permissions needed
2. **Use Permission Checks**: Always protect endpoints with appropriate permission checks
3. **Test Thoroughly**: Test with each role to ensure proper access control
4. **Document Custom Roles**: Document any custom roles and their purpose
5. **Protect System Roles**: Never delete or significantly alter system roles
6. **Review Regularly**: Periodically review and audit role permissions
7. **Separate Concerns**: Use different permissions for different operations (view vs edit)

## Troubleshooting

### User Can't Access Endpoint

1. Check if user has required permission
2. Verify user's role has the permission assigned  
3. Check if permission is active in database
4. Ensure token is valid and not expired

### Permission Not Working

1. Verify permission code spelling
2. Check PermissionChecker is applied to endpoint
3. Ensure permission exists in database
4. Check role_permissions table for assignment

### Can't Create Custom Role

1. Ensure you're logged in as Admin/Super Admin
2. Check role code is unique
3. Verify permission IDs are valid

## API Endpoints

### Permissions

- `GET /api/v1/permissions/all` - List all permissions grouped by module
- `GET /api/v1/permissions/my-permissions` - Get current user's permissions
- `GET /api/v1/permissions/role/{role_id}` - Get role's permissions
- `POST /api/v1/permissions/check` - Check if user has permission
- `POST /api/v1/permissions` - Create permission (Admin only)
- `PUT /api/v1/permissions/{id}` - Update permission (Admin only)

### Roles

- `GET /api/v1/roles` - List all roles
- `GET /api/v1/roles/{id}` - Get role with permissions
- `POST /api/v1/roles` - Create custom role (Admin only)
- `PUT /api/v1/roles/{id}` - Update role (Admin only)
- `PUT /api/v1/roles/{id}/permissions` - Update role permissions (Admin only)
- `DELETE /api/v1/roles/{id}` - Delete role (Admin only, not system roles)

## Future Enhancements

- [ ] Resource-based permissions (e.g., project owner has edit rights)
- [ ] Temporary permission grants with expiration
- [ ] Permission groups/categories for easier management
- [ ] Permission inheritance between roles
- [ ] Audit trail for permission changes
- [ ] UI for visual permission matrix management
