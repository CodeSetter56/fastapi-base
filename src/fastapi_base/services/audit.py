from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import AuditLog


async def log_audit(
    db: AsyncSession,
    action: str,
    user_id: UUID | None = None,
    ip_address: str | None = None,
    details: str | None = None,
) -> None:
    audit = AuditLog(
        user_id=user_id,
        action=action,
        ip_address=ip_address,
        details=details,
    )
    db.add(audit)
    await db.commit()
