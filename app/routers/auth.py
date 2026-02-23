"""
Authentication API endpoints.

WHY: Provides user registration, login, and token management.
HOW: Uses JWT for stateless authentication with bcrypt password hashing.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlmodel import Session, select

from app.core.auth import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    should_refresh_token,
    verify_password,
)
from app.core.db import engine
from app.models.models import User
from app.schemas.schemas import Token, UserCreate, UserLogin, UserRead, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()

limiter = Limiter(key_func=get_remote_address)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> User:
    """
    Dependency to extract and validate current user from JWT.

    WHY: Reusable authentication check for protected endpoints.
    HOW: Decodes JWT, validates, and fetches user from database.
         Auto-refreshes tokens that are close to expiration.

    Args:
        credentials: Bearer token from Authorization header.

    Returns:
        User: The authenticated user.

    Raises:
        HTTPException: 401 if token is invalid or user not found.
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_raw = payload.get("sub")
    if not user_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: int = int(user_id_raw)

    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user


async def get_admin_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to verify current user is an administrator.

    WHY: Restricts admin-only endpoints.
    HOW: Checks is_admin flag after basic authentication.

    Args:
        user: The authenticated user from get_current_user.

    Returns:
        User: The authenticated admin user.

    Raises:
        HTTPException: 403 if user is not admin.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def get_current_user_with_refresh(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> tuple[User, str | None]:
    """
    Dependency that returns user and optionally a refreshed token.

    WHY: Enables auto-renewal of sessions for active users.
    HOW: Checks if token should be refreshed and generates new one.

    Args:
        credentials: Bearer token from Authorization header.

    Returns:
        tuple: (User, new_token or None)

    Raises:
        HTTPException: 401 if authentication fails.
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_raw = payload.get("sub")
    if not user_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: int = int(user_id_raw)

    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        new_token = None
        if should_refresh_token(payload) and user.id is not None:
            new_token = create_access_token(user.id)

        return user, new_token


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
)
@limiter.limit("3/minute")
def register(request: Request, user_data: UserCreate) -> User:
    """
    Register a new user account.

    WHY: Allows new users to create accounts for platform access.
    HOW: Validates uniqueness of username/email, hashes password, creates user.

    Args:
        user_data: Registration data with username, email, password.

    Returns:
        User: The created user (without password).

    Raises:
        HTTPException: 400 if username or email already exists.
    """
    with Session(engine) as session:
        existing = session.exec(
            select(User).where(
                (User.username == user_data.username) | (User.email == user_data.email)
            )
        ).first()

        if existing:
            if existing.username == user_data.username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )

        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@router.post(
    "/login",
    response_model=Token,
    summary="User login",
)
@limiter.limit("5/minute")
def login(request: Request, user_data: UserLogin) -> dict:
    """
    Authenticate user and issue access token.

    WHY: Provides JWT token for API authentication.
    HOW: Validates credentials against stored hash, generates JWT.

    Args:
        user_data: Login credentials (username, password).

    Returns:
        dict: Access token and token type.

    Raises:
        HTTPException: 401 if credentials are invalid.
    """
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.username == user_data.username)
        ).first()

        if not user or not verify_password(user_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user.id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User ID is missing",
            )

        access_token = create_access_token(user.id)
        return {"access_token": access_token, "token_type": "bearer"}


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current user",
)
def get_me(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get current authenticated user's profile.

    WHY: Allows client to verify authentication and get user data.
    HOW: Returns user from JWT token validation.

    Args:
        user: The authenticated user from dependency.

    Returns:
        User: Current user's profile.
    """
    return user


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
)
def refresh_token(
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Refresh access token.

    WHY: Allows proactive token renewal before expiration.
    HOW: Issues new token for authenticated user.

    Args:
        user: The authenticated user from dependency.

    Returns:
        dict: New access token and token type.
    """
    if user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User ID is missing",
        )
    access_token = create_access_token(user.id)
    return {"access_token": access_token, "token_type": "bearer"}


@router.patch(
    "/me",
    response_model=UserRead,
    summary="Update current user",
)
def update_me(
    update_data: UserUpdate,
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Update current user's profile.

    WHY: Allows users to update their profile information.
    HOW: Partial update of provided fields.

    Args:
        update_data: Fields to update (partial).
        user: The authenticated user from dependency.

    Returns:
        User: The updated user.
    """
    with Session(engine) as session:
        db_user = session.get(User, user.id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(db_user, key, value)

        db_user.updated_at = datetime.now(timezone.utc)
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user
