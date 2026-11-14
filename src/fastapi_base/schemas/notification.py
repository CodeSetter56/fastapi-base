from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class NotificationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    actor_id: UUID | None = None
    title: str
    message: str
    type: str
    is_read: bool
    link: str | None = None
    created_at: datetime


class NotificationListPublic(BaseModel):
    items: list[NotificationPublic]
    total: int
    unread_count: int
