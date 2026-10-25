from uuid import UUID

from fastapi import HTTPException, status
from jwt import InvalidTokenError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, UserRole
from ..schemas.auth import LoginRequest, TokenPair
from ..schemas.user import UserCreate
from ..security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def _token_pair(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id, user.token_version),
        refresh_token=create_refresh_token(user.id, user.token_version),
    )


async def register(
    db: AsyncSession,
    payload: UserCreate,
) -> User:
    # Bootstrap: the first account in an empty database becomes the admin.
    user_count = await db.scalar(select(func.count()).select_from(User)) or 0
    user = User(
        email=str(payload.email),
        password_hash=hash_password(payload.password),
        role=UserRole.admin.value if user_count == 0 else UserRole.user.value,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from None
    await db.refresh(user)
    return user


async def login(
    db: AsyncSession,
    payload: LoginRequest,
) -> TokenPair:
    result = await db.execute(select(User).filter_by(email=str(payload.email)))
    user = result.scalar_one_or_none()

    # Always verify password to mitigate timing attacks (use dummy hash if user not found)
    if user is None:
        # Use a dummy hash that matches the hash length but is invalid for any password
        dummy_hash = "$2b$12$dummyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        verify_password(payload.password, dummy_hash)
        user = None  # Ensure user remains None
    else:
        # User exists, verify the actual password
        if not verify_password(payload.password, user.password_hash):
            user = None  # Treat as not found to avoid leaking existence via timing

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return _token_pair(user)


async def refresh(
    db: AsyncSession,
    refresh_token: str,
) -> TokenPair:
    try:
        claims = decode_token(refresh_token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    if claims.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(claims["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    if claims.get("ver") != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is no longer valid",
        )

    return _token_pair(user)


async def logout(
    db: AsyncSession,
    user: User,
) -> None:
    user.token_version += 1
    await db.commit()
