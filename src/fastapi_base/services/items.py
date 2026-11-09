from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from ..models import Bookmark, Item, Rating
from ..schemas.item import ItemCreate, ItemUpdate


async def enrich_item(db: AsyncSession, item: Item, current_user_id: UUID | None = None) -> Item:
    # Get rating stats
    rating_stats = await db.execute(
        select(func.avg(Rating.score), func.count(Rating.id)).filter_by(item_id=item.id)
    )
    avg_score, count = rating_stats.one()
    item.average_rating = float(avg_score) if avg_score is not None else 0.0
    item.rating_count = int(count) if count is not None else 0

    # Get bookmark status
    item.is_bookmarked = False
    if current_user_id is not None:
        bm = await db.execute(
            select(Bookmark).filter_by(user_id=current_user_id, item_id=item.id)
        )
        item.is_bookmarked = bm.scalar_one_or_none() is not None

    return item


async def list_items(
    db: AsyncSession,
    limit: int,
    offset: int,
    owner_id: UUID | None = None,
    category_id: UUID | None = None,
    current_user_id: UUID | None = None,
) -> tuple[list[Item], int]:
    stmt = select(Item)
    count_stmt = select(func.count()).select_from(Item)
    if owner_id is not None:
        stmt = stmt.filter_by(owner_id=owner_id)
        count_stmt = count_stmt.filter_by(owner_id=owner_id)
    if category_id is not None:
        stmt = stmt.filter_by(category_id=category_id)
        count_stmt = count_stmt.filter_by(category_id=category_id)

    total = await db.scalar(count_stmt) or 0
    result = await db.execute(
        stmt.order_by(
            col(Item.created_at).desc(),
            col(Item.id).desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    items = list(result.scalars().all())
    enriched = []
    for item in items:
        enriched.append(await enrich_item(db, item, current_user_id))
    return enriched, total


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
    current_user_id: UUID | None = None,
) -> Item:
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    return await enrich_item(db, item, current_user_id)


async def create_item(
    db: AsyncSession,
    owner_id: UUID,
    payload: ItemCreate,
) -> Item:
    item = Item(
        owner_id=owner_id,
        category_id=payload.category_id,
        title=payload.title,
        description=payload.description,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return await enrich_item(db, item, owner_id)


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
    return await enrich_item(db, item, owner_id)


async def delete_item(
    db: AsyncSession,
    item_id: UUID,
    owner_id: UUID,
) -> None:
    item = await _get_owned_item(db, item_id, owner_id)
    await db.delete(item)
    await db.commit()
