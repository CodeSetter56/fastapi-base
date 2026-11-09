from datetime import UTC, datetime
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from ..models import CartItem, Item
from ..schemas.cart import CartItemCreate, CartItemUpdate, CartSummary


async def get_cart(db: AsyncSession, user_id: UUID) -> CartSummary:
    result = await db.execute(
        select(CartItem, Item)
        .join(Item, CartItem.item_id == Item.id)
        .filter(CartItem.user_id == user_id)
        .order_by(col(CartItem.created_at).desc())
    )
    rows = result.all()

    cart_items = []
    total_items = 0
    for cart_item, item in rows:
        total_items += cart_item.quantity
        # attach item
        cart_item.item = item
        cart_items.append(cart_item)

    return CartSummary(items=cart_items, total_items=total_items)


async def add_to_cart(
    db: AsyncSession,
    user_id: UUID,
    payload: CartItemCreate,
) -> CartItem:
    item = await db.get(Item, payload.item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    result = await db.execute(
        select(CartItem).filter_by(user_id=user_id, item_id=payload.item_id)
    )
    cart_item = result.scalar_one_or_none()

    if cart_item is not None:
        cart_item.quantity += payload.quantity
        cart_item.updated_at = datetime.now(UTC)
    else:
        cart_item = CartItem(
            user_id=user_id,
            item_id=payload.item_id,
            quantity=payload.quantity,
        )
        db.add(cart_item)

    await db.commit()
    await db.refresh(cart_item)
    # attach item object
    cart_item.item = item
    return cart_item


async def update_cart_item(
    db: AsyncSession,
    user_id: UUID,
    item_id: UUID,
    payload: CartItemUpdate,
) -> CartItem:
    result = await db.execute(
        select(CartItem).filter_by(user_id=user_id, item_id=item_id)
    )
    cart_item = result.scalar_one_or_none()
    if cart_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    cart_item.quantity = payload.quantity
    cart_item.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(cart_item)

    item = await db.get(Item, item_id)
    cart_item.item = item
    return cart_item


async def remove_from_cart(
    db: AsyncSession,
    user_id: UUID,
    item_id: UUID,
) -> None:
    result = await db.execute(
        select(CartItem).filter_by(user_id=user_id, item_id=item_id)
    )
    cart_item = result.scalar_one_or_none()
    if cart_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    await db.delete(cart_item)
    await db.commit()


async def clear_cart(db: AsyncSession, user_id: UUID) -> None:
    result = await db.execute(select(CartItem).filter_by(user_id=user_id))
    for cart_item in result.scalars().all():
        await db.delete(cart_item)
    await db.commit()
