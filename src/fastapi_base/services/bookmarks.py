from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from ..models import Bookmark, Item
from ..schemas.item import ItemOut
from .items import to_item_out


async def list_bookmarks(
    db: AsyncSession,
    user_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[ItemOut], int]:
    count_stmt = select(func.count()).select_from(Bookmark).filter_by(user_id=user_id)
    total = await db.scalar(count_stmt) or 0

    result = await db.execute(
        select(Item)
        .join(Bookmark, col(Bookmark.item_id) == col(Item.id))
        .filter(col(Bookmark.user_id) == user_id)
        .order_by(col(Bookmark.created_at).desc())
        .limit(limit)
        .offset(offset)
    )
    items = list(result.scalars().all())
    enriched = []
    for item in items:
        enriched.append(await to_item_out(db, item, user_id))
    return enriched, total


async def add_bookmark(db: AsyncSession, user_id: UUID, item_id: UUID) -> None:
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    existing = await db.execute(
        select(Bookmark).filter_by(user_id=user_id, item_id=item_id)
    )
    if existing.scalar_one_or_none() is not None:
        return  # already bookmarked

    bookmark = Bookmark(user_id=user_id, item_id=item_id)
    db.add(bookmark)
    await db.commit()


async def remove_bookmark(db: AsyncSession, user_id: UUID, item_id: UUID) -> None:
    existing = await db.execute(
        select(Bookmark).filter_by(user_id=user_id, item_id=item_id)
    )
    bookmark = existing.scalar_one_or_none()
    if bookmark is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")

    await db.delete(bookmark)
    await db.commit()
