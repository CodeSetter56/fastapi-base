from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from ..db import get_session
from ..deps import get_current_admin
from ..models import AuditLog
from ..schemas.audit import AuditLogPublic
from ..schemas.common import Page

router = APIRouter()


@router.get("", response_model=Page[AuditLogPublic], dependencies=[Depends(get_current_admin)])
async def list_audit_logs(
    db: AsyncSession = Depends(get_session),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[AuditLogPublic]:
    total = await db.scalar(select(func.count()).select_from(AuditLog)) or 0
    result = await db.execute(
        select(AuditLog)
        .order_by(col(AuditLog.created_at).desc())
        .limit(limit)
        .offset(offset)
    )
    logs = list(result.scalars().all())
    return Page[AuditLogPublic](
        items=[AuditLogPublic.model_validate(l) for l in logs],
        total=total, limit=limit, offset=offset
    )
