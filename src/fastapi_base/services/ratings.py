from datetime import UTC, datetime
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from ..models import Item, Rating
from ..schemas.rating import RatingCreate, RatingUpdate


async def list_item_ratings(
    db: AsyncSession,
    item_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[Rating], int]:
    # Ensure item exists
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    total = await db.scalar(
        select(func.count()).select_from(Rating).filter_by(item_id=item_id)
    ) or 0
    result = await db.execute(
        select(Rating)
        .filter_by(item_id=item_id)
        .order_by(col(Rating.created_at).desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), total


async def upsert_rating(
    db: AsyncSession,
    item_id: UUID,
    user_id: UUID,
    payload: RatingCreate,
) -> Rating:
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    result = await db.execute(
        select(Rating).filter_by(item_id=item_id, user_id=user_id)
    )
    rating = result.scalar_one_or_none()

    if rating is not None:
        rating.score = payload.score
        rating.review_text = payload.review_text
        rating.updated_at = datetime.now(UTC)
    else:
        rating = Rating(
            item_id=item_id,
            user_id=user_id,
            score=payload.score,
            review_text=payload.review_text,
        )
        db.add(rating)

    await db.commit()
    await db.refresh(rating)
    return rating


async def delete_rating(
    db: AsyncSession,
    item_id: UUID,
    user_id: UUID,
) -> None:
    result = await db.execute(
        select(Rating).filter_by(item_id=item_id, user_id=user_id)
    )
    rating = result.scalar_one_or_none()
    if rating is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rating not found")

    await db.delete(rating)
    await db.commit()
