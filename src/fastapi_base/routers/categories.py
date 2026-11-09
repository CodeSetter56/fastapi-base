from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_admin
from ..models import Category
from ..schemas.common import Page
from ..schemas.category import CategoryCreate, CategoryPublic, CategoryUpdate
from ..services import categories as categories_service

router = APIRouter()


@router.get("", response_model=Page[CategoryPublic])
async def list_categories(
    db: AsyncSession = Depends(get_session),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[CategoryPublic]:
    categories, total = await categories_service.list_categories(db, limit, offset)
    return Page[CategoryPublic](
        items=[CategoryPublic.model_validate(c) for c in categories],
        total=total, limit=limit, offset=offset
    )


@router.post("", response_model=CategoryPublic, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin)])
async def create_category(
    req: CategoryCreate,
    db: AsyncSession = Depends(get_session),
) -> Category:
    return await categories_service.create_category(db, req)


@router.get("/{category_id}", response_model=CategoryPublic)
async def get_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> Category:
    return await categories_service.get_category(db, category_id)


@router.patch("/{category_id}", response_model=CategoryPublic, dependencies=[Depends(get_current_admin)])
async def update_category(
    category_id: UUID,
    req: CategoryUpdate,
    db: AsyncSession = Depends(get_session),
) -> Category:
    return await categories_service.update_category(db, category_id, req)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> None:
    await categories_service.delete_category(db, category_id)
