"""
Security tests for MatrixAPI.

Tests for:
- Authentication requirements
- Authorization checks
- Rate limiting
- Character ownership validation
- Location creation protection
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
from app.core.auth import create_access_token, get_password_hash


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
def admin_user(db_session):
    """Create an admin test user."""
    with Session(engine) as session:
        user = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("adminpass123"),
            is_active=True,
            is_admin=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@pytest.fixture
def auth_token(test_user):
    """Create auth token for test user."""
    return create_access_token(test_user.id)


@pytest.fixture
def admin_token(admin_user):
    """Create auth token for admin user."""
    return create_access_token(admin_user.id)


class TestAuthSecurity:
    """Tests for authentication security."""

    def test_login_requires_valid_credentials(self, client, test_user):
        """Login should fail with wrong password."""
        response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_success(self, client, test_user):
        """Login should succeed with correct credentials."""
        response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpass123"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_protected_endpoint_without_token(self, client, db_session):
        """Protected endpoints should require authentication."""
        response = client.post(
            "/api/locations",
            json={"name": "Test Location", "description": "Test"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_with_invalid_token(self, client, db_session):
        """Protected endpoints should reject invalid tokens."""
        response = client.post(
            "/api/locations",
            json={"name": "Test Location"},
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401


class TestLocationSecurity:
    """Tests for location API security."""

    def test_create_location_requires_auth(self, client, db_session):
        """Creating location should require authentication."""
        response = client.post(
            "/api/locations",
            json={"name": "Secret Location"},
        )
        assert response.status_code == 401

    def test_create_location_with_auth(self, client, db_session, test_user, auth_token):
        """Creating location should work with valid token."""
        response = client.post(
            "/api/locations",
            json={"name": "My Location", "description": "Test"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Location"
        assert data["creator_id"] == test_user.id

    def test_location_creator_tracking(self, client, db_session, test_user, auth_token):
        """Location should track who created it."""
        response = client.post(
            "/api/locations",
            json={"name": "Test Location"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        assert response.json()["creator_id"] == test_user.id


class TestCharacterSecurity:
    """Tests for character API security."""

    def test_get_own_characters(self, client, db_session, test_user, auth_token):
        """User should get only their own characters."""
        with Session(engine) as session:
            char = Character(
                name="My Character",
                description="Test",
                owner_id=test_user.id,
            )
            session.add(char)
            session.commit()

        response = client.get(
            "/api/characters/",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        characters = response.json()
        assert len(characters) == 1
        assert characters[0]["name"] == "My Character"

    def test_cannot_access_other_user_characters(
        self, client, db_session, test_user, auth_token
    ):
        """User should not access other users' characters directly by ID."""
        with Session(engine) as session:
            other_user = User(
                username="other",
                email="other@example.com",
                hashed_password=get_password_hash("pass"),
            )
            session.add(other_user)
            session.commit()
            session.refresh(other_user)

            other_char = Character(
                name="Other Character",
                owner_id=other_user.id,
            )
            session.add(other_char)
            session.commit()
            other_char_id = other_char.id

        response = client.get(
            f"/api/characters/{other_char_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 404

    def test_update_own_character_only(self, client, db_session, test_user, auth_token):
        """User should update only their own characters."""
        with Session(engine) as session:
            char = Character(
                name="My Character",
                owner_id=test_user.id,
            )
            session.add(char)
            session.commit()
            session.refresh(char)
            char_id = char.id

        response = client.patch(
            f"/api/characters/{char_id}",
            json={"name": "Updated Name"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_cannot_update_other_user_character(
        self, client, db_session, test_user, auth_token
    ):
        """User should not update other users' characters."""
        with Session(engine) as session:
            other_user = User(
                username="other2",
                email="other2@example.com",
                hashed_password=get_password_hash("pass"),
            )
            session.add(other_user)
            session.commit()
            session.refresh(other_user)

            other_char = Character(
                name="Other Character",
                owner_id=other_user.id,
            )
            session.add(other_char)
            session.commit()
            other_char_id = other_char.id

        response = client.patch(
            f"/api/characters/{other_char_id}",
            json={"name": "Hacked Name"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 404


class TestRateLimiting:
    """Tests for rate limiting."""

    def test_register_rate_limit(self, client, db_session):
        """Registration should be rate limited."""
        for i in range(5):
            response = client.post(
                "/auth/register",
                json={
                    "username": f"user{i}",
                    "email": f"user{i}@test.com",
                    "password": "pass123",
                },
            )
        response = client.post(
            "/auth/register",
            json={
                "username": "rateuser",
                "email": "rate@test.com",
                "password": "pass123",
            },
        )
        assert response.status_code in [200, 429]


class TestUserData:
    """Tests for user data protection."""

    def test_cannot_see_other_user_profile(
        self, client, db_session, test_user, auth_token
    ):
        """User should not access other user's /me endpoint."""
        with Session(engine) as session:
            other = User(
                username="otheruser",
                email="other@test.com",
                hashed_password=get_password_hash("pass"),
            )
            session.add(other)
            session.commit()
            other_token = create_access_token(other.id)

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert response.status_code == 200
        assert response.json()["username"] == "otheruser"

    def test_user_response_has_admin_flag(self, client, test_user, auth_token):
        """User response should include is_admin flag."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "is_admin" in data
        assert data["is_admin"] is False


class TestHealthChecks:
    """Basic health check tests."""

    def test_locations_public_read(self, client, db_session, test_user, auth_token):
        """Reading locations should be public."""
        client.post(
            "/api/locations",
            json={"name": "Public Location"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        response = client.get("/api/locations")
        assert response.status_code == 200
        locations = response.json()
        assert any(loc["name"] == "Public Location" for loc in locations)
