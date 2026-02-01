"""
User management API routes - Complete CRUD for users table.
"""


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import PermissionChecker, get_current_user
from app.core.security import hash_password
from app.database import get_db
from app.models.auth import Role, User
from app.schemas.auth import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    is_active: bool | None = None,
    role_id: int | None = None,
    current_user: User = Depends(PermissionChecker("user.view")),
    db: Session = Depends(get_db)
):
    """
    List all users from the users table.
    Requires user.view permission.
    """
    query = db.query(User).filter(User.is_deleted == False)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    if role_id is not None:
        query = query.filter(User.role_id == role_id)

    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

    return [UserResponse.model_validate(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(PermissionChecker("user.view")),
    db: Session = Depends(get_db)
):
    """
    Get user by ID.
    Requires user.view permission.
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse.model_validate(user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    current_user: User = Depends(PermissionChecker("user.create")),
    db: Session = Depends(get_db)
):
    """
    Create a new user account.
    Requires user.create permission.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Validate role exists if provided
    if data.role_id:
        role = db.query(Role).filter(Role.id == data.role_id).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )

    # Create user
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        role_id=data.role_id,
        company_id=data.company_id,
        branch_id=data.branch_id,
        is_active=True,
        is_verified=False,
        created_by=current_user.id
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(PermissionChecker("user.edit")),
    db: Session = Depends(get_db)
):
    """
    Update user account details.
    Requires user.edit permission.
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check email uniqueness if changing
    if data.email and data.email != user.email:
        existing = db.query(User).filter(User.email == data.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )

    # Validate role if changing
    if data.role_id:
        role = db.query(Role).filter(Role.id == data.role_id).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)

    # Handle password separately
    if 'password' in update_data and update_data['password']:
        update_data['password_hash'] = hash_password(update_data.pop('password'))

    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_by = current_user.id
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(PermissionChecker("user.delete")),
    db: Session = Depends(get_db)
):
    """
    Soft delete a user account.
    Requires user.delete permission.
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    # Soft delete
    user.soft_delete(current_user.id)
    db.commit()

    return {"message": "User deleted successfully"}


@router.patch("/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_user: User = Depends(PermissionChecker("user.edit")),
    db: Session = Depends(get_db)
):
    """
    Activate a user account.
    Requires user.edit permission.
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_active = True
    user.updated_by = current_user.id
    db.commit()

    return {"message": "User activated successfully"}


@router.patch("/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(PermissionChecker("user.edit")),
    db: Session = Depends(get_db)
):
    """
    Deactivate a user account.
    Requires user.edit permission.
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent self-deactivation
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )

    user.is_active = False
    user.updated_by = current_user.id
    db.commit()

    return {"message": "User deactivated successfully"}


@router.patch("/{user_id}/role")
async def update_user_role(
    user_id: int,
    role_id: int,
    current_user: User = Depends(PermissionChecker("user.edit")),
    db: Session = Depends(get_db)
):
    """
    Update user's role.
    Requires user.edit permission.
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Validate role exists
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    user.role_id = role_id
    user.updated_by = current_user.id
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.patch("/{user_id}/verify")
async def verify_user(
    user_id: int,
    current_user: User = Depends(PermissionChecker("user.edit")),
    db: Session = Depends(get_db)
):
    """
    Mark user as verified.
    Requires user.edit permission.
    """
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user.is_verified = True
    user.updated_by = current_user.id
    db.commit()

    return {"message": "User verified successfully"}


@router.post("/bulk-delete")
async def bulk_delete_users(
    user_ids: list[int],
    current_user: User = Depends(PermissionChecker("user.delete")),
    db: Session = Depends(get_db)
):
    """
    Bulk delete multiple user accounts.
    Requires user.delete permission.
    """
    if not user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user IDs provided"
        )

    # Prevent self-deletion
    if current_user.id in user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    users = db.query(User).filter(
        User.id.in_(user_ids),
        User.is_deleted == False
    ).all()

    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No users found"
        )

    deleted_count = 0
    for user in users:
        user.soft_delete(current_user.id)
        deleted_count += 1

    db.commit()

    return {"message": f"{deleted_count} users deleted successfully", "count": deleted_count}


@router.post("/bulk-activate")
async def bulk_activate_users(
    user_ids: list[int],
    current_user: User = Depends(PermissionChecker("user.edit")),
    db: Session = Depends(get_db)
):
    """
    Bulk activate multiple user accounts.
    Requires user.edit permission.
    """
    if not user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user IDs provided"
        )

    users = db.query(User).filter(
        User.id.in_(user_ids),
        User.is_deleted == False
    ).all()

    activated_count = 0
    for user in users:
        user.is_active = True
        user.updated_by = current_user.id
        activated_count += 1

    db.commit()

    return {"message": f"{activated_count} users activated successfully", "count": activated_count}


@router.post("/bulk-deactivate")
async def bulk_deactivate_users(
    user_ids: list[int],
    current_user: User = Depends(PermissionChecker("user.edit")),
    db: Session = Depends(get_db)
):
    """
    Bulk deactivate multiple user accounts.
    Requires user.edit permission.
    """
    if not user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user IDs provided"
        )

    # Prevent self-deactivation
    if current_user.id in user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )

    users = db.query(User).filter(
        User.id.in_(user_ids),
        User.is_deleted == False
    ).all()

    deactivated_count = 0
    for user in users:
        user.is_active = False
        user.updated_by = current_user.id
        deactivated_count += 1

    db.commit()

    return {"message": f"{deactivated_count} users deactivated successfully", "count": deactivated_count}


# ============== Avatar Upload Endpoint ==============
import os
import uuid
from datetime import datetime
from fastapi import File, Request, UploadFile
from app.config import get_settings

_settings = get_settings()
AVATARS_DIR = os.path.join(_settings.UPLOAD_DIR, "avatars")
os.makedirs(AVATARS_DIR, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload avatar image for the current user.
    Updates the user's avatar field with the new image URL.
    """
    return await _save_avatar(current_user, file, db)


@router.post("/{user_id}/avatar")
async def upload_user_avatar(
    user_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(PermissionChecker("user.edit")),
    db: Session = Depends(get_db)
):
    """
    Upload avatar image for a specific user (Admin function).
    Requires user.edit permission.
    """
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return await _save_avatar(user, file, db)


async def _save_avatar(user: User, file: UploadFile, db: Session):
    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_AVATAR_SIZE // (1024 * 1024)}MB"
        )

    # Generate unique filename
    unique_id = uuid.uuid4().hex[:12]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"avatar_{user.id}_{timestamp}_{unique_id}{ext}"
    file_path = os.path.join(AVATARS_DIR, unique_filename)

    # Delete old avatar if exists
    if user.avatar:
        old_filename = os.path.basename(user.avatar)
        old_path = os.path.join(AVATARS_DIR, old_filename)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass  # Ignore deletion errors

    # Save new file
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Update user avatar field
    avatar_url = f"/uploads/avatars/{unique_filename}"
    user.avatar = avatar_url
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "avatar": avatar_url,
        "message": "Avatar updated successfully"
    }


@router.delete("/avatar")
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete the current user's avatar.
    """
    if not current_user.avatar:
        raise HTTPException(status_code=404, detail="No avatar to delete")

    # Delete file
    filename = os.path.basename(current_user.avatar)
    file_path = os.path.join(AVATARS_DIR, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass  # Ignore deletion errors

    # Clear avatar field
    current_user.avatar = None
    db.commit()

    return {"success": True, "message": "Avatar deleted successfully"}
