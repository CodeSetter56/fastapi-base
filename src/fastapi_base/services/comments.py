from datetime import UTC, datetime
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from ..models import Comment, Item, User, UserRole
from ..schemas.comment import CommentCreate, CommentUpdate
from . import notifications as notifications_service


async def list_item_comments(
    db: AsyncSession,
    item_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[Comment], int]:
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    total = await db.scalar(
        select(func.count()).select_from(Comment).filter_by(item_id=item_id)
    ) or 0

    result = await db.execute(
        select(Comment)
        .filter_by(item_id=item_id)
        .order_by(col(Comment.created_at).asc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), total


async def create_comment(
    db: AsyncSession,
    item_id: UUID,
    user_id: UUID,
    payload: CommentCreate,
) -> Comment:
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    parent_comment = None
    if payload.parent_id:
        parent_comment = await db.get(Comment, payload.parent_id)
        if parent_comment is None or parent_comment.item_id != item_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent comment not found or does not belong to this item",
            )

    comment = Comment(
        item_id=item_id,
        user_id=user_id,
        parent_id=payload.parent_id,
        content=payload.content,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    actor = await db.get(User, user_id)
    actor_name = actor.username or actor.email if actor else "Someone"

    # Notify item owner if commenter is not the owner
    if item.owner_id != user_id:
        await notifications_service.create_notification(
            db,
            user_id=item.owner_id,
            actor_id=user_id,
            title="New comment on your item",
            message=f"{actor_name} commented on your item '{item.title}'",
            type="comment",
            link=f"/items/{item.id}",
        )

    # Notify parent comment author if replying and different from item owner and actor
    if parent_comment and parent_comment.user_id != user_id and parent_comment.user_id != item.owner_id:
        await notifications_service.create_notification(
            db,
            user_id=parent_comment.user_id,
            actor_id=user_id,
            title="New reply to your comment",
            message=f"{actor_name} replied to your comment on '{item.title}'",
            type="comment_reply",
            link=f"/items/{item.id}",
        )

    return comment


async def update_comment(
    db: AsyncSession,
    comment_id: UUID,
    user_id: UUID,
    payload: CommentUpdate,
) -> Comment:
    comment = await db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )
    if comment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this comment",
        )

    comment.content = payload.content
    comment.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(comment)
    return comment


async def delete_comment(
    db: AsyncSession,
    comment_id: UUID,
    current_user: User,
) -> None:
    comment = await db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    # Allow comment author, item owner, or admin to delete comment
    item = await db.get(Item, comment.item_id)
    is_owner = item and item.owner_id == current_user.id
    if comment.user_id != current_user.id and not is_owner and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this comment",
        )

    await db.delete(comment)
    await db.commit()
