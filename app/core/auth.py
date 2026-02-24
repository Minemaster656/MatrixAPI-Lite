"""
JWT authentication utilities.

WHY: Provides secure token-based authentication with session management.
HOW: Uses python-jose for JWT encoding/decoding with HS256 algorithm.
     Tokens include expiration and can be refreshed automatically.
     Uses Argon2id for password hashing (winner of PHC, resistant to GPU attacks).
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_DAYS,
    TOKEN_REFRESH_THRESHOLD_DAYS,
)

ph = PasswordHasher()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    WHY: Secure password validation without exposing the hash algorithm.
    HOW: Uses Argon2id for constant-time comparison.

    Args:
        plain_password: The password to verify.
        hashed_password: The stored hash to compare against.

    Returns:
        bool: True if password matches, False otherwise.
    """
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password for secure storage.

    WHY: Never store plain text passwords.
    HOW: Uses Argon2id with automatic salt generation.

    Args:
        password: The plain text password to hash.

    Returns:
        str: The Argon2id hash of the password.
    """
    return ph.hash(password)


def create_access_token(
    subject: str | int,
    expires_delta: Optional[timedelta] = None,
    extra_data: Optional[dict[str, Any]] = None,
) -> str:
    """
    Create a JWT access token.

    WHY: Generates secure tokens for API authentication.
    HOW: Encodes user ID and expiration into JWT with secret key.

    Args:
        subject: The user ID to encode in the token.
        expires_delta: Custom expiration time (default: 7 days).
        extra_data: Additional claims to include in the token.

    Returns:
        str: The encoded JWT token.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if extra_data:
        to_encode.update(extra_data)

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and validate a JWT access token.

    WHY: Extracts user data from token for authentication.
    HOW: Decodes JWT and validates expiration and signature.

    Args:
        token: The JWT token to decode.

    Returns:
        Optional[dict]: The decoded payload, or None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def should_refresh_token(
    payload: dict[str, Any], refresh_threshold_days: int = 3
) -> bool:
    """
    Check if token should be refreshed (auto-renewal).

    WHY: Provides seamless session extension without forcing re-login.
    HOW: Checks if token expires within the threshold period.

    Args:
        payload: The decoded JWT payload.
        refresh_threshold_days: Days before expiry to trigger refresh.

    Returns:
        bool: True if token should be refreshed.
    """
    exp = payload.get("exp")
    if not exp:
        return False

    expiration = datetime.fromtimestamp(exp, tz=timezone.utc)
    threshold = datetime.now(timezone.utc) + timedelta(days=refresh_threshold_days)

    return expiration <= threshold
