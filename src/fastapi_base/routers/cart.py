from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_user
from ..models import CartItem, User
from ..schemas.cart import CartItemCreate, CartItemPublic, CartItemUpdate, CartSummary
from ..services import cart as cart_service

router = APIRouter()


@router.get("", response_model=CartSummary)
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> CartSummary:
    return await cart_service.get_cart(db, current_user.id)


@router.post("", response_model=CartItemPublic, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    req: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> CartItem:
    return await cart_service.add_to_cart(db, current_user.id, req)


@router.patch("/{item_id}", response_model=CartItemPublic)
async def update_cart_item(
    item_id: UUID,
    req: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> CartItem:
    return await cart_service.update_cart_item(db, current_user.id, item_id, req)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_cart(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    await cart_service.remove_from_cart(db, current_user.id, item_id)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    await cart_service.clear_cart(db, current_user.id)
