"""
Authentication endpoints for user login and token management.

WHY: Provides OAuth2-compatible authentication for API access.
HOW: Uses OAuth2PasswordBearer with token-based authentication.
     NOTE: Currently uses fake in-memory storage for demo purposes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


class Token(BaseModel):
    """OAuth2 token response model."""

    access_token: str
    token_type: str


# Dummy user store for demonstration
# TODO: Replace with real database-backed user store
fake_users_db = {
    "alice": {
        "username": "alice",
        "full_name": "Alice Wonderland",
        "hashed_password": "fakehashedsecret",
    }
}


def fake_hash_password(password: str) -> str:
    """
    Fake password hashing for demo purposes.

    WHY: Placeholder for actual password hashing implementation.
    HOW: Prepends 'fakehashed' to password (NOT SECURE).

    Args:
        password: Plain text password.

    Returns:
        str: Fake hashed password.

    WARNING: This is not secure! Replace with bcrypt/passlib in production.
    """
    return "fakehashed" + password


@router.post(
    "/token",
    response_model=Token,
    summary="OAuth2 token endpoint",
    description="Authenticates user and returns an access token for API access.",
)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> dict:
    """
    Authenticate user and issue access token.

    WHY: OAuth2-compatible login endpoint for token-based authentication.
    HOW: Validates credentials against fake_users_db and returns token.

    Args:
        form_data: OAuth2 form with username and password fields.

    Returns:
        dict: Access token and token type.

    Raises:
        HTTPException: 401 if credentials are invalid.
    """
    user_dict = fake_users_db.get(form_data.username)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    hashed_password = fake_hash_password(form_data.password)
    if hashed_password != user_dict["hashed_password"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": user_dict["username"], "token_type": "bearer"}


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Dependency to extract and validate current user from token.

    WHY: Reusable dependency for protected endpoints that need user context.
    HOW: Looks up user by token in fake_users_db.

    Args:
        token: JWT token from Authorization header.

    Returns:
        dict: User data dictionary.

    Raises:
        HTTPException: 401 if token is invalid or user not found.
    """
    user = fake_users_db.get(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
