from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_user, bearer_scheme
from ..models import Item, User
from ..schemas.common import Page
from ..schemas.item import ItemCreate, ItemOut, ItemUpdate
from ..services import items as items_service
from ..token.security import decode_token
from ..token.cookies import ACCESS_COOKIE
from fastapi import Request

router = APIRouter()


async def get_optional_current_user(
    request: Request,
    credentials=Depends(bearer_scheme),
    db: AsyncSession = Depends(get_session),
) -> User | None:
    token = credentials.credentials if credentials is not None else request.cookies.get(ACCESS_COOKIE)
    if not token:
        return None
    try:
        claims = decode_token(token)
        if claims.get("type") != "access":
            return None
        user_id = UUID(claims["sub"])
        user = await db.get(User, user_id)
        if user and user.is_active and claims.get("ver") == user.token_version:
            return user
    except Exception:
        pass
    return None


@router.get("", response_model=Page[ItemOut])
async def list_items(
    owner_id: UUID | None = None,
    category_id: UUID | None = None,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_session),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[ItemOut]:
    items, total = await items_service.list_items(
        db,
        limit,
        offset,
        owner_id=owner_id,
        category_id=category_id,
        current_user_id=current_user.id if current_user else None,
    )
    return Page[ItemOut](
        items=[ItemOut.model_validate(i) for i in items],
        total=total, limit=limit, offset=offset
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
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_session),
) -> Item:
    return await items_service.get_item(db, item_id, current_user.id if current_user else None)


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
