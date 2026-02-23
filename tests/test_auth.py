"""
Tests for authentication utilities.

Tests for:
- Password hashing and verification
- JWT token creation and decoding
- Token refresh logic
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from app.core.auth import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    should_refresh_token,
    verify_password,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_get_password_hash_returns_string(self):
        """Hashing should return a non-empty string."""
        result = get_password_hash("testpassword")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_is_different_from_password(self):
        """Hash should be different from the original password."""
        password = "mypassword123"
        result = get_password_hash(password)
        assert result != password

    def test_verify_password_correct(self):
        """Verification should succeed with correct password."""
        password = "securepassword"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Verification should fail with wrong password."""
        password = "correctpassword"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """Verification should fail with empty password."""
        password = "somepassword"
        hashed = get_password_hash(password)
        assert verify_password("", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Same password should produce different hashes (salt)."""
        password = "samepassword"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """Tests for JWT token functions."""

    def test_create_token_with_user_id(self):
        """Token creation should work with integer user ID."""
        token = create_access_token(123)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_with_string(self):
        """Token creation should work with string user ID."""
        token = create_access_token("user_456")
        assert isinstance(token, str)

    def test_decode_valid_token(self):
        """Decoding valid token should return payload."""
        user_id = 999
        token = create_access_token(user_id)
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_invalid_token(self):
        """Decoding invalid token should return None."""
        result = decode_access_token("invalid.token.here")
        assert result is None

    def test_decode_tampered_token(self):
        """Decoding tampered token should return None."""
        token = create_access_token(1)
        tampered = token[:-5] + "xxxxx"
        result = decode_access_token(tampered)
        assert result is None

    def test_token_contains_expiration(self):
        """Token should contain expiration time."""
        token = create_access_token(1)
        payload = decode_access_token(token)
        assert "exp" in payload

    def test_token_with_custom_expiration(self):
        """Token should respect custom expiration time."""
        custom_delta = timedelta(hours=1)
        token = create_access_token(1, expires_delta=custom_delta)
        payload = decode_access_token(token)
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert exp_time > now
        assert exp_time < now + timedelta(hours=2)

    def test_token_with_extra_data(self):
        """Token should include extra data in payload."""
        extra = {"role": "admin", "scope": "full"}
        token = create_access_token(1, extra_data=extra)
        payload = decode_access_token(token)
        assert payload["role"] == "admin"
        assert payload["scope"] == "full"


class TestTokenRefresh:
    """Tests for token refresh logic."""

    def test_should_refresh_token_expiring_soon(self):
        """Should refresh token that's close to expiration."""
        expiring_soon = datetime.now(timezone.utc) + timedelta(days=1)
        payload = {"exp": expiring_soon.timestamp()}
        assert should_refresh_token(payload, refresh_threshold_days=3) is True

    def test_should_refresh_token_far_expiration(self):
        """Should not refresh token with plenty of time left."""
        far_future = datetime.now(timezone.utc) + timedelta(days=10)
        payload = {"exp": far_future.timestamp()}
        assert should_refresh_token(payload, refresh_threshold_days=3) is False

    def test_should_refresh_token_expired(self):
        """Should refresh already expired token."""
        past = datetime.now(timezone.utc) - timedelta(days=1)
        payload = {"exp": past.timestamp()}
        assert should_refresh_token(payload) is True

    def test_should_refresh_token_missing_exp(self):
        """Should return False when exp is missing."""
        payload = {"sub": "123"}
        assert should_refresh_token(payload) is False
