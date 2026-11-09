from datetime import UTC, datetime
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from ..models import CartItem, Item
from ..schemas.cart import CartItemCreate, CartItemPublic, CartItemUpdate, CartSummary
from .items import to_item_out


async def get_cart(db: AsyncSession, user_id: UUID) -> CartSummary:
    result = await db.execute(
        select(CartItem, Item)
        .join(Item, col(CartItem.item_id) == col(Item.id))
        .filter(col(CartItem.user_id) == user_id)
        .order_by(col(CartItem.created_at).desc())
    )
    rows = result.all()

    cart_item_publics = []
    total_items = 0
    for cart_item, item in rows:
        total_items += cart_item.quantity
        item_out = await to_item_out(db, item, user_id)
        cart_item_publics.append(
            CartItemPublic(
                id=cart_item.id,
                user_id=cart_item.user_id,
                item_id=cart_item.item_id,
                quantity=cart_item.quantity,
                item=item_out,
                created_at=cart_item.created_at,
                updated_at=cart_item.updated_at,
            )
        )

    return CartSummary(items=cart_item_publics, total_items=total_items)


async def add_to_cart(
    db: AsyncSession,
    user_id: UUID,
    payload: CartItemCreate,
) -> CartItemPublic:
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

    item_out = await to_item_out(db, item, user_id)
    return CartItemPublic(
        id=cart_item.id,
        user_id=cart_item.user_id,
        item_id=cart_item.item_id,
        quantity=cart_item.quantity,
        item=item_out,
        created_at=cart_item.created_at,
        updated_at=cart_item.updated_at,
    )


async def update_cart_item(
    db: AsyncSession,
    user_id: UUID,
    item_id: UUID,
    payload: CartItemUpdate,
) -> CartItemPublic:
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
    item_out = await to_item_out(db, item, user_id) if item else None
    return CartItemPublic(
        id=cart_item.id,
        user_id=cart_item.user_id,
        item_id=cart_item.item_id,
        quantity=cart_item.quantity,
        item=item_out,
        created_at=cart_item.created_at,
        updated_at=cart_item.updated_at,
    )


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
