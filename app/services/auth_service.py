"""
Authentication service.
Handles login, token management, and session handling.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_otp,
    hash_password,
    verify_password,
)
from app.models.auth import OTPCode, RolePermission, User, UserSession
from app.schemas.auth import UserCreate


class AuthService:
    """Authentication service class."""

    def __init__(self, db: Session):
        self.db = db

    def authenticate_user(self, email: str, password: str) -> User | None:
        """
        Authenticate user with email and password.

        Returns:
            User object if authentication successful, None otherwise
        """
        user = self.db.query(User).filter(
            User.email == email,
            User.is_deleted == False
        ).first()

        if not user:
            return None

        # Check if account is locked
        if user.is_locked():
            return None

        # Verify password
        if not verify_password(password, user.password_hash):
            # Increment failed attempts
            user.login_attempts += 1

            # Lock account if too many attempts
            if user.login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(
                    minutes=settings.LOCKOUT_DURATION_MINUTES
                )

            self.db.commit()
            return None

        # Reset login attempts on successful login
        user.login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        self.db.commit()

        return user

    def create_tokens(self, user: User) -> tuple[str, str, int]:
        """
        Create access and refresh tokens for user.

        Returns:
            Tuple of (access_token, refresh_token, expires_in)
        """
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role_id": user.role_id,
            "company_id": user.company_id
        }

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds

        return access_token, refresh_token, expires_in

    def create_session(
        self,
        user: User,
        access_token: str,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> UserSession:
        """Create a new user session."""
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        session = UserSession(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        return session

    def invalidate_session(self, token: str) -> bool:
        """Invalidate a session by token."""
        session = self.db.query(UserSession).filter(
            UserSession.access_token == token
        ).first()

        if session:
            session.is_valid = False
            self.db.commit()
            return True

        return False

    def invalidate_all_sessions(self, user_id: int) -> int:
        """Invalidate all sessions for a user."""
        result = self.db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_valid == True
        ).update({"is_valid": False})

        self.db.commit()
        return result

    def refresh_access_token(self, refresh_token: str) -> tuple[str, int] | None:
        """
        Refresh access token using refresh token.

        Returns:
            Tuple of (new_access_token, expires_in) or None if invalid
        """
        payload = decode_token(refresh_token)

        if not payload or payload.get("type") != "refresh":
            return None

        # Check if session is still valid
        session = self.db.query(UserSession).filter(
            UserSession.refresh_token == refresh_token,
            UserSession.is_valid == True,
            UserSession.expires_at > datetime.utcnow()
        ).first()

        if not session:
            return None

        # Get user
        user = self.db.query(User).filter(User.id == int(payload["sub"])).first()
        if not user or not user.is_active:
            return None

        # Create new access token
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role_id": user.role_id,
            "company_id": user.company_id
        }

        new_access_token = create_access_token(token_data)
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        # Update session
        session.access_token = new_access_token
        self.db.commit()

        return new_access_token, expires_in

    def get_user_permissions(self, user: User) -> list[str]:
        """Get all permission codes for a user."""
        if not user.role_id:
            return []

        role_permissions = self.db.query(RolePermission).filter(
            RolePermission.role_id == user.role_id
        ).all()

        permissions = []
        for rp in role_permissions:
            if rp.permission:
                permissions.append(rp.permission.code)

        return permissions

    def generate_and_save_otp(self, user: User, purpose: str = "login") -> str:
        """Generate OTP and save to database."""
        # Invalidate any existing OTPs
        self.db.query(OTPCode).filter(
            OTPCode.user_id == user.id,
            OTPCode.purpose == purpose,
            OTPCode.is_used == False
        ).update({"is_used": True})

        # Generate new OTP
        otp = generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

        otp_record = OTPCode(
            user_id=user.id,
            code=otp,
            purpose=purpose,
            expires_at=expires_at
        )

        self.db.add(otp_record)
        self.db.commit()

        return otp

    def verify_otp(self, user_id: int, code: str, purpose: str = "login") -> bool:
        """Verify OTP code."""
        otp_record = self.db.query(OTPCode).filter(
            OTPCode.user_id == user_id,
            OTPCode.code == code,
            OTPCode.purpose == purpose,
            OTPCode.is_used == False,
            OTPCode.expires_at > datetime.utcnow()
        ).first()

        if otp_record:
            otp_record.is_used = True
            otp_record.used_at = datetime.utcnow()
            self.db.commit()
            return True

        return False

    def register_user(self, user_data: UserCreate) -> User:
        """Register a new user."""
        user = User(
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            role_id=user_data.role_id,
            company_id=user_data.company_id,
            branch_id=user_data.branch_id
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return user

    def change_password(self, user: User, new_password: str) -> bool:
        """Change user password."""
        user.password_hash = hash_password(new_password)
        user.password_changed_at = datetime.utcnow()

        # Invalidate all sessions
        self.invalidate_all_sessions(user.id)

        self.db.commit()
        return True

