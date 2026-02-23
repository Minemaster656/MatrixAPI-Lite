"""
Integration tests for characters router.

Tests for:
- Character creation
- Character retrieval
- Character updates
- Character deletion
- Ownership validation
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
def auth_token(test_user):
    """Create auth token for test user."""
    return create_access_token(test_user.id)


class TestCharacterCreation:
    """Tests for character creation."""

    def test_create_character_success(self, client, db_session, test_user, auth_token):
        """Creating character should succeed with valid data."""
        response = client.post(
            "/api/characters/",
            json={"name": "My Hero", "description": "A brave warrior"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Hero"
        assert data["description"] == "A brave warrior"
        assert data["owner_id"] == test_user.id

    def test_create_character_no_auth(self, client, db_session):
        """Creating character should require authentication."""
        response = client.post(
            "/api/characters/",
            json={"name": "Hero"},
        )
        assert response.status_code == 401

    def test_create_character_empty_name(self, client, test_user, auth_token):
        """Creating character should fail with empty name."""
        response = client.post(
            "/api/characters/",
            json={"name": ""},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 422


class TestCharacterRetrieval:
    """Tests for getting characters."""

    def test_get_my_characters(self, client, db_session, test_user, auth_token):
        """Getting my characters should return user's characters."""
        with Session(engine) as session:
            char = Character(name="Character1", owner_id=test_user.id)
            session.add(char)
            session.commit()

        response = client.get(
            "/api/characters/",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Character1"

    def test_get_my_characters_empty(self, client, test_user, auth_token):
        """Getting characters when none exist should return empty list."""
        response = client.get(
            "/api/characters/",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_get_character_by_id(self, client, db_session, test_user, auth_token):
        """Getting specific character should work for owner."""
        with Session(engine) as session:
            char = Character(name="MyChar", owner_id=test_user.id)
            session.add(char)
            session.commit()
            session.refresh(char)
            char_id = char.id

        response = client.get(
            f"/api/characters/{char_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "MyChar"

    def test_get_character_not_owner(self, client, db_session, test_user, auth_token):
        """Getting other user's character should fail."""
        with Session(engine) as session:
            other = User(
                username="other",
                email="other@example.com",
                hashed_password=get_password_hash("pass"),
            )
            session.add(other)
            session.commit()
            session.refresh(other)

            char = Character(name="OtherChar", owner_id=other.id)
            session.add(char)
            session.commit()
            session.refresh(char)
            char_id = char.id

        response = client.get(
            f"/api/characters/{char_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 404

    def test_get_character_nonexistent(self, client, test_user, auth_token):
        """Getting nonexistent character should return 404."""
        response = client.get(
            "/api/characters/99999",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 404


class TestCharacterUpdate:
    """Tests for updating characters."""

    def test_update_character(self, client, db_session, test_user, auth_token):
        """Updating character should work for owner."""
        with Session(engine) as session:
            char = Character(name="OldName", owner_id=test_user.id)
            session.add(char)
            session.commit()
            session.refresh(char)
            char_id = char.id

        response = client.patch(
            f"/api/characters/{char_id}",
            json={"name": "NewName", "description": "New description"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "NewName"
        assert data["description"] == "New description"

    def test_update_character_not_owner(
        self, client, db_session, test_user, auth_token
    ):
        """Updating other user's character should fail."""
        with Session(engine) as session:
            other = User(
                username="other2",
                email="other2@example.com",
                hashed_password=get_password_hash("pass"),
            )
            session.add(other)
            session.commit()
            session.refresh(other)

            char = Character(name="OtherChar", owner_id=other.id)
            session.add(char)
            session.commit()
            session.refresh(char)
            char_id = char.id

        response = client.patch(
            f"/api/characters/{char_id}",
            json={"name": "Hacked"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 404


class TestCharacterDeletion:
    """Tests for deleting characters."""

    def test_delete_character(self, client, db_session, test_user, auth_token):
        """Deleting character should work for owner."""
        with Session(engine) as session:
            char = Character(name="ToDelete", owner_id=test_user.id)
            session.add(char)
            session.commit()
            session.refresh(char)
            char_id = char.id

        response = client.delete(
            f"/api/characters/{char_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 204

        with Session(engine) as session:
            char = session.get(Character, char_id)
            assert char is None

    def test_delete_character_not_owner(
        self, client, db_session, test_user, auth_token
    ):
        """Deleting other user's character should fail."""
        with Session(engine) as session:
            other = User(
                username="other3",
                email="other3@example.com",
                hashed_password=get_password_hash("pass"),
            )
            session.add(other)
            session.commit()
            session.refresh(other)

            char = Character(name="OtherChar", owner_id=other.id)
            session.add(char)
            session.commit()
            session.refresh(char)
            char_id = char.id

        response = client.delete(
            f"/api/characters/{char_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 404


class TestDefaultAvatar:
    """Tests for default avatar assignment."""

    def test_default_avatar_assigned(self, client, test_user, auth_token):
        """Character should get default avatar on creation."""
        response = client.post(
            "/api/characters/",
            json={"name": "TestChar"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["avatar_url"] is not None
        assert "/static/assets/img/builtin_avatars/" in data["avatar_url"]
