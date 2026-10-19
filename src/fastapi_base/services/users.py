from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, UserRole
from ..schemas.user import UserUpdate
from ..security import hash_password


async def list_users(
    db: AsyncSession,
    limit: int,
    offset: int,
) -> tuple[list[User], int]:
    total = await db.scalar(select(func.count()).select_from(User)) or 0
    result = await db.execute(
        select(User)
        .order_by(desc("created_at"))
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), total


def get_me(current_user: User) -> User:
    return current_user


async def _get_user(db: AsyncSession, user_id: UUID) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def _ensure_self_or_admin(current_user: User, user_id: UUID) -> None:
    if current_user.id != user_id and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own account",
        )


async def _admin_count(db: AsyncSession) -> int:
    return (
        await db.scalar(
            select(func.count())
            .select_from(User)
            .filter_by(role=UserRole.admin.value)
        )
        or 0
    )


async def _ensure_not_last_admin(
    db: AsyncSession,
    user: User,
) -> None:
    if user.role == UserRole.admin and await _admin_count(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot remove the last admin",
        )


async def get_user(
    db: AsyncSession,
    user_id: UUID,
    current_user: User,
) -> User:
    _ensure_self_or_admin(current_user, user_id)
    return await _get_user(db, user_id)


async def update_user(
    db: AsyncSession,
    user_id: UUID,
    current_user: User,
    payload: UserUpdate,
) -> User:
    _ensure_self_or_admin(current_user, user_id)
    user = await _get_user(db, user_id)

    data = payload.model_dump(exclude_unset=True)
    if "email" in data:
        user.email = str(data["email"])
    if "password" in data:
        user.password_hash = hash_password(data["password"])
        # Changing the password revokes every previously issued token.
        user.token_version += 1

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


async def set_role(
    db: AsyncSession,
    user_id: UUID,
    role: UserRole,
) -> User:
    user = await _get_user(db, user_id)
    if user.role == UserRole.admin and role != UserRole.admin:
        await _ensure_not_last_admin(db, user)

    user.role = role.value
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(
    db: AsyncSession,
    user_id: UUID,
    current_user: User,
) -> None:
    _ensure_self_or_admin(current_user, user_id)
    user = await _get_user(db, user_id)
    await _ensure_not_last_admin(db, user)

    await db.delete(user)
    await db.commit()
