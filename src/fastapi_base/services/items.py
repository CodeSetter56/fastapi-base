from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from ..models import Item
from ..schemas.item import ItemCreate, ItemUpdate


async def list_items(
    db: AsyncSession,
    owner_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[Item], int]:
    total = (
        await db.scalar(
            select(func.count())
            .select_from(Item)
            .filter_by(owner_id=owner_id)
        )
        or 0
    )
    result = await db.execute(
        select(Item)
        .filter_by(owner_id=owner_id)
        .order_by(
            col(Item.created_at).desc(),
            col(Item.id).desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), total


async def _get_owned_item(
    db: AsyncSession,
    item_id: UUID,
    owner_id: UUID,
) -> Item:
    result = await db.execute(
        select(Item).filter_by(id=item_id, owner_id=owner_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    return item


async def get_item(
    db: AsyncSession,
    item_id: UUID,
    owner_id: UUID,
) -> Item:
    return await _get_owned_item(db, item_id, owner_id)


async def create_item(
    db: AsyncSession,
    owner_id: UUID,
    payload: ItemCreate,
) -> Item:
    item = Item(
        owner_id=owner_id,
        title=payload.title,
        description=payload.description,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_item(
    db: AsyncSession,
    item_id: UUID,
    owner_id: UUID,
    payload: ItemUpdate,
) -> Item:
    item = await _get_owned_item(db, item_id, owner_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    item.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(item)
    return item


async def delete_item(
    db: AsyncSession,
    item_id: UUID,
    owner_id: UUID,
) -> None:
    item = await _get_owned_item(db, item_id, owner_id)
    await db.delete(item)
    await db.commit()
