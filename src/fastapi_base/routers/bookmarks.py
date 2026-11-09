from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_user
from ..models import User
from ..schemas.common import Page
from ..schemas.item import ItemOut
from ..services import bookmarks as bookmarks_service

router = APIRouter()


@router.get("", response_model=Page[ItemOut])
async def list_bookmarks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[ItemOut]:
    items, total = await bookmarks_service.list_bookmarks(db, current_user.id, limit, offset)
    return Page[ItemOut](
        items=[ItemOut.model_validate(i) for i in items],
        total=total, limit=limit, offset=offset
    )


@router.post("/{item_id}", status_code=status.HTTP_201_CREATED)
async def add_bookmark(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    await bookmarks_service.add_bookmark(db, current_user.id, item_id)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_bookmark(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    await bookmarks_service.remove_bookmark(db, current_user.id, item_id)
