from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class AuditLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    action: str
    ip_address: str | None
    details: str | None
    created_at: datetime
