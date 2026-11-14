from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=5000)
    parent_id: UUID | None = None


class CommentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=5000)


class CommentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_id: UUID
    user_id: UUID
    parent_id: UUID | None = None
    content: str
    created_at: datetime
    updated_at: datetime
