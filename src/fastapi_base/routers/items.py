from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_user
from ..models import Item, User
from ..schemas.common import Page
from ..schemas.item import ItemCreate, ItemOut, ItemUpdate
from ..services import items as items_service

router = APIRouter()


@router.get("", response_model=Page[ItemOut])
async def list_items(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[ItemOut]:
    items, total = await items_service.list_items(
        db,
        current_user.id,
        limit,
        offset,
    )
    return Page[ItemOut](
        items=[ItemOut.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
async def create_item(
    req: ItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Item:
    return await items_service.create_item(db, current_user.id, req)


@router.get("/{item_id}", response_model=ItemOut)
async def get_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Item:
    return await items_service.get_item(db, item_id, current_user.id)


@router.patch("/{item_id}", response_model=ItemOut)
async def update_item(
    item_id: UUID,
    payload: ItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Item:
    return await items_service.update_item(
        db,
        item_id,
        current_user.id,
        payload,
    )


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    await items_service.delete_item(db, item_id, current_user.id)
