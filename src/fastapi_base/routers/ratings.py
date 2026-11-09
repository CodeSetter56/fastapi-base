from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_user
from ..models import Rating, User
from ..schemas.common import Page
from ..schemas.rating import RatingCreate, RatingPublic
from ..services import ratings as ratings_service

router = APIRouter()


@router.get("/{item_id}/ratings", response_model=Page[RatingPublic])
async def list_item_ratings(
    item_id: UUID,
    db: AsyncSession = Depends(get_session),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[RatingPublic]:
    ratings, total = await ratings_service.list_item_ratings(db, item_id, limit, offset)
    return Page[RatingPublic](
        items=[RatingPublic.model_validate(r) for r in ratings],
        total=total, limit=limit, offset=offset
    )


@router.post("/{item_id}/ratings", response_model=RatingPublic, status_code=status.HTTP_201_CREATED)
async def upsert_rating(
    item_id: UUID,
    req: RatingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Rating:
    return await ratings_service.upsert_rating(db, item_id, current_user.id, req)


@router.delete("/{item_id}/ratings", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rating(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    await ratings_service.delete_rating(db, item_id, current_user.id)
