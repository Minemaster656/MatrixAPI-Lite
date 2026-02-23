"""
Integration tests for locations router.

Tests for:
- Location creation
- Location retrieval (list and single)
- Location messages retrieval
- Public access to locations
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select, delete

from main import app
from app.core.db import engine
from app.models.models import User, Location
from app.core.auth import create_access_token, get_password_hash
from app.services.message_store import message_store
from app.schemas.schemas import MessageCreate


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Create fresh database session for each test."""
    with Session(engine) as session:
        session.exec(delete(Location))
        session.exec(delete(User))
        session.commit()
    yield
    with Session(engine) as session:
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
    return create_access_token(test_user.id)


class TestLocationCreation:
    """Tests for location creation."""

    def test_create_location_success(self, client, db_session, test_user, auth_token):
        """Creating location should succeed with auth."""
        response = client.post(
            "/api/locations",
            json={
                "name": "New Location",
                "description": "A new place",
                "background_url": "https://example.com/bg.jpg",
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Location"
        assert data["creator_id"] == test_user.id

    def test_create_location_no_auth(self, client, db_session):
        """Creating location should require authentication."""
        response = client.post(
            "/api/locations",
            json={"name": "Secret Location"},
        )
        assert response.status_code == 401

    def test_create_location_invalid_token(self, client, db_session):
        """Creating location should reject invalid token."""
        response = client.post(
            "/api/locations",
            json={"name": "Location"},
            headers={"Authorization": "Bearer invalid"},
        )
        assert response.status_code == 401


class TestLocationRetrieval:
    """Tests for getting locations."""

    def test_get_locations_public(self, client, db_session, test_user, auth_token):
        """Getting locations should be public."""
        client.post(
            "/api/locations",
            json={"name": "Public Location"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        response = client.get("/api/locations")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(loc["name"] == "Public Location" for loc in data)

    def test_get_locations_empty(self, client, db_session):
        """Getting locations when none exist should work."""
        response = client.get("/api/locations")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_single_location(self, client, db_session, test_user, auth_token):
        """Getting single location should work."""
        client.post(
            "/api/locations",
            json={"name": "Test Location"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        response = client.get("/api/locations/1")
        assert response.status_code == 200
        assert response.json()["name"] == "Test Location"

    def test_get_single_location_nonexistent(self, client, db_session):
        """Getting nonexistent location should return 404."""
        response = client.get("/api/locations/99999")
        assert response.status_code == 404


class TestLocationMessages:
    """Tests for location messages."""

    def test_get_messages_empty(self, client, db_session, test_user, auth_token):
        """Getting messages for location with none should return empty."""
        client.post(
            "/api/locations",
            json={"name": "Test Loc"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        response = client.get("/api/locations/1/messages")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_messages_with_data(self, client, db_session, test_user, auth_token):
        """Getting messages should return stored messages."""
        client.post(
            "/api/locations",
            json={"name": "Test Loc"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        message_store.add_message(
            MessageCreate(
                text="Hello",
                character_name="Hero",
                location_id=1,
            )
        )

        response = client.get("/api/locations/1/messages")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["text"] == "Hello"

    def test_get_messages_custom_limit(self, client, db_session, test_user, auth_token):
        """Getting messages should respect limit parameter."""
        client.post(
            "/api/locations",
            json={"name": "Test Loc"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        for i in range(50):
            message_store.add_message(
                MessageCreate(
                    text=f"Message {i}",
                    character_name="Hero",
                    location_id=1,
                )
            )

        response = client.get("/api/locations/1/messages?limit=10")
        assert response.status_code == 200
        assert len(response.json()) == 10
