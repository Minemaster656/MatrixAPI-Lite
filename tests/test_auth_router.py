"""
Integration tests for authentication router.

Tests for:
- User registration
- User login
- Token refresh
- User profile updates
- Authentication edge cases
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select, delete

from main import app
from app.core.db import engine
from app.models.models import User, Character, Location
from app.core.auth import get_password_hash


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Create fresh database session for each test."""
    with Session(engine) as session:
        session.exec(delete(Character))
        session.exec(delete(Location))
        session.exec(delete(User))
        session.commit()
    yield
    with Session(engine) as session:
        session.exec(delete(Character))
        session.exec(delete(Location))
        session.exec(delete(User))
        session.commit()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    with Session(engine) as session:
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=get_password_hash("testpass123"),
            is_active=True,
            is_admin=False,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@pytest.fixture
def auth_token(test_user):
    """Create auth token for test user."""
    from app.core.auth import create_access_token

    return create_access_token(test_user.id)


class TestRegistration:
    """Tests for user registration."""

    def test_register_success(self, client, db_session):
        """Registration should succeed with valid data."""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "securepass123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "id" in data

    def test_register_duplicate_username(self, client, db_session, test_user):
        """Registration should fail with duplicate username."""
        response = client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "other@example.com",
                "password": "pass123",
            },
        )
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]

    def test_register_duplicate_email(self, client, db_session, test_user):
        """Registration should fail with duplicate email."""
        response = client.post(
            "/auth/register",
            json={
                "username": "otheruser",
                "email": "test@example.com",
                "password": "pass123",
            },
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client, db_session):
        """Registration should fail with invalid email."""
        response = client.post(
            "/auth/register",
            json={
                "username": "user",
                "email": "not-an-email",
                "password": "pass123",
            },
        )
        assert response.status_code == 422

    def test_register_short_password(self, client, db_session):
        """Registration should fail with short password."""
        response = client.post(
            "/auth/register",
            json={
                "username": "user",
                "email": "user@example.com",
                "password": "123",
            },
        )
        assert response.status_code == 422


class TestLogin:
    """Tests for user login."""

    def test_login_success(self, client, test_user):
        """Login should succeed with correct credentials."""
        response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        """Login should fail with wrong password."""
        response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client, db_session):
        """Login should fail with nonexistent user."""
        response = client.post(
            "/auth/login",
            json={"username": "nonexistent", "password": "password"},
        )
        assert response.status_code == 401

    def test_login_inactive_user(self, client, db_session):
        """Login should fail for inactive user."""
        with Session(engine) as session:
            user = User(
                username="inactive",
                email="inactive@example.com",
                hashed_password=get_password_hash("pass"),
                is_active=False,
            )
            session.add(user)
            session.commit()

        response = client.post(
            "/auth/login",
            json={"username": "inactive", "password": "pass"},
        )
        assert response.status_code == 401


class TestUserProfile:
    """Tests for user profile endpoints."""

    def test_get_me(self, client, test_user, auth_token):
        """Get current user should return user data."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_get_me_no_token(self, client, db_session):
        """Get me should require authentication."""
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client, db_session):
        """Get me should reject invalid token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401

    def test_update_me(self, client, test_user, auth_token):
        """Update me should update user data."""
        response = client.patch(
            "/auth/me",
            json={"avatar_url": "/new/avatar.png"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["avatar_url"] == "/new/avatar.png"


class TestTokenRefresh:
    """Tests for token refresh."""

    def test_refresh_token(self, client, test_user, auth_token):
        """Token refresh should return new token."""
        response = client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_invalid_token(self, client, db_session):
        """Token refresh should fail with invalid token."""
        response = client.post(
            "/auth/refresh",
            headers={"Authorization": "Bearer invalid"},
        )
        assert response.status_code == 401
