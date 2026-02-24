"""
Tests for Pydantic schemas validation.

Tests for:
- User schema validation
- Character schema validation
- Location schema validation
- Message schema validation
- Token schema validation
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import datetime
from pydantic import ValidationError
from app.schemas.schemas import (
    CharacterCreate,
    CharacterRead,
    CharacterUpdate,
    LocationCreate,
    LocationRead,
    MessageCreate,
    MessageRead,
    Token,
    UserCreate,
    UserLogin,
    UserRead,
    UserUpdate,
)


class TestUserSchemas:
    """Tests for user-related schemas."""

    def test_user_create_valid(self):
        """UserCreate should accept valid data."""
        user = UserCreate(
            username="testuser",
            email="test@example.com",
            password="password123",
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_user_create_invalid_email(self):
        """UserCreate should reject invalid email."""
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="not-an-email",
                password="password123",
            )

    def test_user_create_short_username(self):
        """UserCreate should reject short username."""
        with pytest.raises(ValidationError):
            UserCreate(
                username="ab",
                email="test@example.com",
                password="password123",
            )

    def test_user_create_short_password(self):
        """UserCreate should reject short password."""
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="12345",
            )

    def test_user_login_valid(self):
        """UserLogin should accept valid data."""
        login = UserLogin(username="testuser", password="password")
        assert login.username == "testuser"

    def test_user_read_from_model(self):
        """UserRead should work with ORM model attributes."""
        user = UserRead(
            id="uuid-1234",
            username="testuser",
            email="test@example.com",
            avatar_url=None,
            is_active=True,
            is_admin=False,
            created_at=datetime.now(),
        )
        assert user.id == "uuid-1234"
        assert user.username == "testuser"

    def test_user_update_partial(self):
        """UserUpdate should allow partial updates."""
        update = UserUpdate(avatar_url="/new/avatar.png")
        assert update.avatar_url == "/new/avatar.png"

    def test_user_update_avatar_url_sanitization(self):
        """UserUpdate should sanitize dangerous URLs."""
        update = UserUpdate(avatar_url="javascript:alert('xss')")
        assert update.avatar_url is None

    def test_user_update_avatar_url_static(self):
        """UserUpdate should allow static paths."""
        update = UserUpdate(avatar_url="/static/avatars/test.png")
        assert update.avatar_url == "/static/avatars/test.png"


class TestCharacterSchemas:
    """Tests for character-related schemas."""

    def test_character_create_valid(self):
        """CharacterCreate should accept valid data."""
        char = CharacterCreate(
            name="My Character",
            description="A brave hero",
        )
        assert char.name == "My Character"
        assert char.description == "A brave hero"

    def test_character_create_default_description(self):
        """CharacterCreate should have empty default description."""
        char = CharacterCreate(name="Char")
        assert char.name == "Char"
        assert char.description == ""

    def test_character_create_empty_name(self):
        """CharacterCreate should reject empty name."""
        with pytest.raises(ValidationError):
            CharacterCreate(name="")

    def test_character_create_long_name(self):
        """CharacterCreate should reject too long name."""
        with pytest.raises(ValidationError):
            CharacterCreate(name="x" * 101)

    def test_character_read_from_model(self):
        """CharacterRead should work with model data."""
        char = CharacterRead(
            id="char-uuid-1234",
            name="Hero",
            description="Description",
            owner_id="user-uuid-5678",
            avatar_url="/avatar.png",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert char.id == "char-uuid-1234"
        assert char.owner_id == "user-uuid-5678"

    def test_character_update_partial(self):
        """CharacterUpdate should allow partial updates."""
        update = CharacterUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.description is None

    def test_character_update_multiple_fields(self):
        """CharacterUpdate should allow multiple fields."""
        update = CharacterUpdate(
            name="New Name",
            description="New desc",
            avatar_url="/new.png",
        )
        assert update.name == "New Name"
        assert update.description == "New desc"
        assert update.avatar_url == "/new.png"

    def test_character_update_avatar_url_sanitization(self):
        """CharacterUpdate should sanitize dangerous URLs."""
        update = CharacterUpdate(avatar_url="javascript:alert('xss')")
        assert update.avatar_url is None

    def test_character_update_accepts_https_url(self):
        """CharacterUpdate should accept valid https URLs."""
        update = CharacterUpdate(avatar_url="https://example.com/avatar.jpg")
        assert update.avatar_url == "https://example.com/avatar.jpg"

    def test_character_update_accepts_static_path(self):
        """CharacterUpdate should accept static paths."""
        update = CharacterUpdate(avatar_url="/static/assets/avatar.png")
        assert update.avatar_url == "/static/assets/avatar.png"

    def test_character_update_rejects_data_url(self):
        """CharacterUpdate should reject data: URLs."""
        update = CharacterUpdate(avatar_url="data:image/png;base64,abc123")
        assert update.avatar_url is None

    def test_character_update_accepts_usr_path(self):
        """CharacterUpdate should accept /usr/ paths."""
        update = CharacterUpdate(avatar_url="/usr/avatars/my_avatar.png")
        assert update.avatar_url == "/usr/avatars/my_avatar.png"


class TestLocationSchemas:
    """Tests for location-related schemas."""

    def test_location_create_valid(self):
        """LocationCreate should accept valid data."""
        loc = LocationCreate(
            name="Tavern",
            description="A cozy place",
            background_url="https://example.com/bg.jpg",
        )
        assert loc.name == "Tavern"
        assert loc.background_url == "https://example.com/bg.jpg"

    def test_location_create_default_values(self):
        """LocationCreate should have default values."""
        loc = LocationCreate(name="Forest")
        assert loc.name == "Forest"
        assert loc.description == ""
        assert loc.background_url is None

    def test_location_create_empty_name(self):
        """LocationCreate should reject empty name."""
        with pytest.raises(ValidationError):
            LocationCreate(name="")

    def test_location_read_from_model(self):
        """LocationRead should work with model data."""
        loc = LocationRead(
            id="loc-uuid-1234",
            name="Tavern",
            description="Description",
            background_url=None,
            creator_id="user-uuid-5678",
            created_at=datetime.now(),
        )
        assert loc.id == "loc-uuid-1234"
        assert loc.creator_id == "user-uuid-5678"

    def test_location_background_url_sanitization(self):
        """LocationCreate should sanitize dangerous URLs."""
        loc = LocationCreate(name="Test", background_url="javascript:alert('xss')")
        assert loc.background_url is None


class TestMessageSchemas:
    """Tests for message-related schemas."""

    def test_message_create_valid(self):
        """MessageCreate should accept valid data."""
        msg = MessageCreate(
            text="Hello world!",
            location_id="loc-uuid-1234",
        )
        assert msg.text == "Hello world!"

    def test_message_create_empty_text(self):
        """MessageCreate should reject empty text."""
        with pytest.raises(ValidationError):
            MessageCreate(
                text="",
                location_id="loc-uuid-1234",
            )

    def test_message_create_long_text(self):
        """MessageCreate should reject too long text."""
        with pytest.raises(ValidationError):
            MessageCreate(
                text="x" * 5001,
                location_id="loc-uuid-1234",
            )

    def test_message_read_from_model(self):
        """MessageRead should work with model data."""
        msg = MessageRead(
            id=1,
            text="Hello",
            character_name="Hero",
            location_id="loc-uuid-1234",
            created_at=datetime.now(),
        )
        assert msg.id == 1
        assert msg.text == "Hello"


class TestTokenSchemas:
    """Tests for token-related schemas."""

    def test_token_valid(self):
        """Token should accept valid data."""
        token = Token(
            access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
            token_type="bearer",
        )
        assert token.access_token.startswith("eyJ")

    def test_token_default_type(self):
        """Token should have default bearer type."""
        token = Token(access_token="test_token")
        assert token.token_type == "bearer"
