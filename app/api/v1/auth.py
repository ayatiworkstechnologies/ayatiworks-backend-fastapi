"""
Authentication API routes.
Login, logout, refresh token, 2FA.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_current_user
from app.core.exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    PermissionDeniedError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    TokenExpiredError,
)
from app.database import get_db
from app.models.auth import User
from app.schemas.auth import (
    ChangePasswordRequest,
    Enable2FARequest,
    LoginRequest,
    LoginResponse,
    OTPRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    RoleListResponse,
    SetPasswordRequest,
    Token,
    UserCreate,
    UserResponse,
)
from app.services.auth_service import AuthService

# Rate limiter for auth endpoints
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Public self-registration.

    The account is created without role assignments and remains unverified until
    an administrator completes onboarding.
    """
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    auth_service = AuthService(db)
    user = auth_service.register_user(data)
    user.is_active = True
    user.is_verified = False
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """Send a password reset code/link when the account exists."""
    user = db.query(User).filter(
        User.email == data.email,
        User.is_deleted == False,
    ).first()

    if user and user.is_active:
        auth_service = AuthService(db)
        reset_code = auth_service.generate_and_save_otp(user, purpose="reset_password")

        origin = request.headers.get("origin") or "http://localhost:3000"
        reset_url = f"{origin.rstrip('/')}/reset-password?token={reset_code}"

        try:
            from app.services.email_service import email_service

            email_service.send_password_reset_email(
                to_email=user.email,
                user_name=user.full_name,
                reset_code=reset_code,
                reset_url=reset_url,
            )
        except Exception:
            # Keep response generic; logs from the email service capture details.
            pass

    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    data: SetPasswordRequest,
    db: Session = Depends(get_db)
):
    """Reset password using the code sent by forgot-password."""
    auth_service = AuthService(db)

    from app.models.auth import OTPCode

    reset_record = db.query(OTPCode).filter(
        OTPCode.code == data.token,
        OTPCode.purpose == "reset_password",
        OTPCode.is_used == False,
    ).first()

    if not reset_record or not reset_record.is_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user = db.query(User).filter(
        User.id == reset_record.user_id,
        User.is_deleted == False,
    ).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    if not auth_service.verify_otp(user.id, data.token, purpose="reset_password"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    auth_service.change_password(user, data.new_password)

    return {"message": "Password reset successfully"}


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")  # Prevent brute force: max 5 attempts per minute per IP
async def login(
    request: Request,
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    Returns access token and user info.
    """
    auth_service = AuthService(db)

    user = auth_service.authenticate_user(data.email, data.password)

    if not user:
        raise InvalidCredentialsError()

    if not user.is_active:
        raise PermissionDeniedError("Account is disabled")

    # Check if 2FA is enabled
    if user.is_2fa_enabled:
        # Generate and send OTP
        otp = auth_service.generate_and_save_otp(user, purpose="login")
        from app.services.email_service import email_service

        sent = email_service.send_otp_email(
            to_email=user.email,
            user_name=user.full_name,
            otp_code=otp,
            ip_address=request.client.host if request.client else None,
            device_info=request.headers.get("user-agent"),
            expiry_minutes=auth_service.get_otp_expiry_minutes(),
        )
        if not sent:
            raise ServiceUnavailableError("email")

        raise AuthenticationError(
            message="2FA required. OTP sent to email.",
            status_code=status.HTTP_202_ACCEPTED,
            error_code="2FA_REQUIRED"
        )

    # Create tokens
    access_token, refresh_token, expires_in = auth_service.create_tokens(user)

    # Create session
    auth_service.create_session(
        user=user,
        access_token=access_token,
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    # Get permissions
    permissions = auth_service.get_user_permissions(user)

    # Build role response
    role_response = None
    if user.role:
        role_response = RoleListResponse(
            id=user.role.id,
            name=user.role.name,
            code=user.role.code,
            description=user.role.description,
            scope=user.role.scope,
            is_active=user.role.is_active,
            is_system=user.role.is_system,
            permission_count=len(user.role.permissions)
        )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            avatar=user.avatar,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_2fa_enabled=user.is_2fa_enabled,
            role_id=user.role_id,
            company_id=user.company_id,
            branch_id=user.branch_id,
            employee_id=user.employee_id,
            last_login=user.last_login,
            role=role_response,
            permissions=permissions
        ),
        permissions=permissions
    )


@router.post("/login/2fa", response_model=LoginResponse)
async def login_2fa(
    request: Request,
    data: OTPRequest,
    db: Session = Depends(get_db)
):
    """
    Complete login with 2FA OTP verification.
    """
    auth_service = AuthService(db)

    user = db.query(User).filter(
        User.email == data.email,
        User.is_deleted == False
    ).first()

    if not user:
        raise ResourceNotFoundError("User", data.email)

    if not auth_service.verify_otp(user.id, data.otp, purpose="login"):
        raise InvalidCredentialsError("Invalid or expired OTP")

    # Create tokens
    access_token, refresh_token, expires_in = auth_service.create_tokens(user)

    # Create session
    auth_service.create_session(
        user=user,
        access_token=access_token,
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    permissions = auth_service.get_user_permissions(user)

    user_response = UserResponse.model_validate(user)
    user_response.permissions = permissions

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=user_response,
        permissions=permissions
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout and invalidate current session."""
    auth_service = AuthService(db)

    # Get token from header
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header else None

    if token:
        auth_service.invalidate_session(token)

    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=Token)
async def refresh_token(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    auth_service = AuthService(db)

    result = auth_service.refresh_access_token(data.refresh_token)

    if not result:
        raise TokenExpiredError()

    new_access_token, expires_in = result

    return Token(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=expires_in
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user profile."""
    # Get permissions
    auth_service = AuthService(db)
    permissions = auth_service.get_user_permissions(current_user)

    # Construct response with permissions
    response = UserResponse.model_validate(current_user)
    response.permissions = permissions

    return response


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change current user's password."""
    from app.core.security import verify_password

    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    auth_service = AuthService(db)
    auth_service.change_password(current_user, data.new_password)

    return {"message": "Password changed successfully"}


@router.post("/2fa/enable")
async def enable_2fa(
    data: Enable2FARequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Enable 2FA for current user."""
    from app.core.security import verify_password

    if not verify_password(data.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is incorrect"
        )

    current_user.is_2fa_enabled = True
    db.commit()

    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
async def disable_2fa(
    data: Enable2FARequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Disable 2FA for current user."""
    from app.core.security import verify_password

    if not verify_password(data.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is incorrect"
        )

    current_user.is_2fa_enabled = False
    current_user.two_fa_secret = None
    db.commit()

    return {"message": "2FA disabled successfully"}

