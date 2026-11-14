from datetime import UTC, datetime
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from ..models import Notification, User


async def create_notification(
    db: AsyncSession,
    *,
    user_id: UUID,
    actor_id: UUID | None = None,
    title: str,
    message: str,
    type: str,
    link: str | None = None,
) -> Notification:
    # Don't notify yourself if actor_id == user_id (optional, but good practice)
    if actor_id and actor_id == user_id:
        return None  # type: ignore

    notification = Notification(
        user_id=user_id,
        actor_id=actor_id,
        title=title,
        message=message,
        type=type,
        link=link,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification


async def list_user_notifications(
    db: AsyncSession,
    user_id: UUID,
    limit: int,
    offset: int,
    unread_only: bool = False,
) -> tuple[list[Notification], int, int]:
    query = select(Notification).filter_by(user_id=user_id)
    if unread_only:
        query = query.filter_by(is_read=False)

    total = await db.scalar(
        select(func.count()).select_from(query.subquery())
    ) or 0

    unread_count = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .filter_by(user_id=user_id, is_read=False)
    ) or 0

    result = await db.execute(
        query.order_by(col(Notification.created_at).desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), total, unread_count


async def mark_notification_as_read(
    db: AsyncSession,
    notification_id: UUID,
    user_id: UUID,
) -> Notification:
    notification = await db.get(Notification, notification_id)
    if notification is None or notification.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return notification


async def mark_all_notifications_as_read(
    db: AsyncSession,
    user_id: UUID,
) -> None:
    result = await db.execute(
        select(Notification).filter_by(user_id=user_id, is_read=False)
    )
    notifications = result.scalars().all()
    for n in notifications:
        n.is_read = True
    await db.commit()


async def delete_notification(
    db: AsyncSession,
    notification_id: UUID,
    user_id: UUID,
) -> None:
    notification = await db.get(Notification, notification_id)
    if notification is None or notification.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    await db.delete(notification)
    await db.commit()
