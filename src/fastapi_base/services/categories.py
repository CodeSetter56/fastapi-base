from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from ..models import Category
from ..schemas.category import CategoryCreate, CategoryUpdate


async def list_categories(
    db: AsyncSession,
    limit: int,
    offset: int,
) -> tuple[list[Category], int]:
    total = await db.scalar(select(func.count()).select_from(Category)) or 0
    result = await db.execute(
        select(Category)
        .order_by(col(Category.name).asc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), total


async def get_category(db: AsyncSession, category_id: UUID) -> Category:
    category = await db.get(Category, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return category


async def create_category(db: AsyncSession, payload: CategoryCreate) -> Category:
    category = Category(name=payload.name, slug=payload.slug)
    db.add(category)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category with this slug already exists",
        ) from None
    await db.refresh(category)
    return category


async def update_category(
    db: AsyncSession,
    category_id: UUID,
    payload: CategoryUpdate,
) -> Category:
    category = await get_category(db, category_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category with this slug already exists",
        ) from None
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, category_id: UUID) -> None:
    category = await get_category(db, category_id)
    await db.delete(category)
    await db.commit()
