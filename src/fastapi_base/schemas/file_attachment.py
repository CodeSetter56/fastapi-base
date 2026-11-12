from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FileAttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_type: str
    owner_id: UUID
    label: str | None
    file_key: str
    thumb_key: str | None
    filename: str
    content_type: str
    size_bytes: int
    uploaded_by: UUID
    presigned_url: str | None = None
    thumb_presigned_url: str | None = None
    created_at: datetime
