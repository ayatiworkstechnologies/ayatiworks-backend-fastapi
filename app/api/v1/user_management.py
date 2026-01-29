"""
User management API routes - Complete CRUD for users table.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_active_user, PermissionChecker
from app.models.auth import User, Role
from app.schemas.auth import UserResponse, UserCreate, UserUpdate
from app.core.security import hash_password

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    role_id: Optional[int] = None,
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
