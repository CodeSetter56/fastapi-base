from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_user
from ..models import Comment, User
from ..schemas.common import Page
from ..schemas.comment import CommentCreate, CommentUpdate, CommentPublic
from ..services import comments as comments_service

router = APIRouter()


@router.get("/items/{item_id}/comments", response_model=Page[CommentPublic])
async def list_item_comments(
    item_id: UUID,
    db: AsyncSession = Depends(get_session),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[CommentPublic]:
    comments, total = await comments_service.list_item_comments(db, item_id, limit, offset)
    return Page[CommentPublic](
        items=[CommentPublic.model_validate(c) for c in comments],
        total=total, limit=limit, offset=offset
    )


@router.post("/items/{item_id}/comments", response_model=CommentPublic, status_code=status.HTTP_201_CREATED)
async def create_comment(
    item_id: UUID,
    req: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Comment:
    return await comments_service.create_comment(db, item_id, current_user.id, req)


@router.put("/comments/{comment_id}", response_model=CommentPublic)
async def update_comment(
    comment_id: UUID,
    req: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Comment:
    return await comments_service.update_comment(db, comment_id, current_user.id, req)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    await comments_service.delete_comment(db, comment_id, current_user)
