"""
Test fixtures and configuration.
"""

import pytest
import tempfile
from pathlib import Path
from typing import Generator
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db
from app.models.auth import User, Role
from app.core.security import hash_password
from app.services.auth_service import AuthService


# Test database URL (SQLite for speed)
# Use the OS temp directory to avoid filesystem I/O issues in certain workspaces.
TEST_DB_PATH = Path(tempfile.gettempdir()) / f"ayatiworks_tech_test_{uuid4().hex}.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH.as_posix()}"

engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create test database tables."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    try:
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()
    except PermissionError:
        pass


@pytest.fixture
def db() -> Generator:
    """Get test database session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def client(db) -> TestClient:
    """Get test client with database override."""
    app.dependency_overrides[get_db] = lambda: db
    storage = getattr(app.state.limiter, "_storage", None)
    if storage and hasattr(storage, "reset"):
        storage.reset()
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def test_role(db) -> Role:
    """Create test role."""
    suffix = uuid4().hex[:8]
    role = Role(
        name="Test Role",
        code=f"test_role_{suffix}",
        description="Test role for unit tests",
        is_active=True
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@pytest.fixture
def test_user(db, test_role) -> User:
    """Create test user."""
    suffix = uuid4().hex[:8]
    user = User(
        email=f"test_{suffix}@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Test",
        last_name="User",
        role_id=test_role.id,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user, db) -> dict:
    """Get authentication headers for test user."""
    auth_service = AuthService(db)
    access_token, refresh_token, _ = auth_service.create_tokens(test_user)
    auth_service.create_session(
        user=test_user,
        access_token=access_token,
        refresh_token=refresh_token,
        ip_address="testclient",
        user_agent="pytest",
    )
    return {"Authorization": f"Bearer {access_token}"}
