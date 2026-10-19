from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_admin, get_current_user
from ..models import User
from ..schemas.common import Page
from ..schemas.user import UserPublic, UserRoleUpdate, UserUpdate
from ..services import users as users_service

router = APIRouter()


@router.get(
    "",
    response_model=Page[UserPublic],
    dependencies=[Depends(get_current_admin)],
)
async def list_users(
    db: AsyncSession = Depends(get_session),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[UserPublic]:
    users, total = await users_service.list_users(db, limit, offset)
    return Page[UserPublic](
        items=[UserPublic.model_validate(user) for user in users],
        total=total,
        limit=limit,
        offset=offset,
    )


# Declared before /{user_id} so "me" is not parsed as a UUID.
@router.get("/me", response_model=UserPublic)
async def read_me(
    current_user: User = Depends(get_current_user),
) -> User:
    return users_service.get_me(current_user)


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> User:
    return await users_service.get_user(db, user_id, current_user)


@router.patch("/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: UUID,
    req: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> User:
    return await users_service.update_user(
        db,
        user_id,
        current_user,
        req,
    )


@router.patch(
    "/{user_id}/role",
    response_model=UserPublic,
    dependencies=[Depends(get_current_admin)],
)
async def update_user_role(
    user_id: UUID,
    payload: UserRoleUpdate,
    db: AsyncSession = Depends(get_session),
) -> User:
    return await users_service.set_role(db, user_id, payload.role)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    await users_service.delete_user(db, user_id, current_user)
