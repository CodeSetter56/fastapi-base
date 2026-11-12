from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_base.db import get_session
from fastapi_base.deps import get_current_user
from fastapi_base.models import User
from fastapi_base.schemas.file_attachment import FileAttachmentOut
from fastapi_base.services.storage import storage_service

router = APIRouter(prefix="/storage", tags=["Storage"])


async def _enrich(attachment, *, include_urls: bool = True) -> FileAttachmentOut:
    """Build a FileAttachmentOut with presigned URLs."""
    data = FileAttachmentOut.model_validate(attachment)
    if include_urls:
        data.presigned_url = await storage_service.generate_presigned_url(attachment.file_key)
        if attachment.thumb_key:
            data.thumb_presigned_url = await storage_service.generate_presigned_url(attachment.thumb_key)
    return data


# ── Upload ──────────────────────────────────────────────────────

@router.post(
    "/upload/{owner_type}/{owner_id}",
    response_model=FileAttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    owner_type: str,
    owner_id: UUID,
    file: UploadFile = File(...),
    label: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if owner_type not in ("user", "item"):
        raise HTTPException(status_code=400, detail="owner_type must be 'user' or 'item'")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    attachment = await storage_service.attach_file(
        db,
        file_content=content,
        original_filename=file.filename,
        content_type=file.content_type,
        owner_type=owner_type,
        owner_id=owner_id,
        uploaded_by=current_user.id,
        label=label,
    )
    return await _enrich(attachment)


# ── List files for an owner ────────────────────────────────────

@router.get(
    "/files/{owner_type}/{owner_id}",
    response_model=list[FileAttachmentOut],
)
async def list_files(
    owner_type: str,
    owner_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    attachments = await storage_service.list_attachments(db, owner_type=owner_type, owner_id=owner_id)
    return [await _enrich(a) for a in attachments]


# ── Get presigned URL for a single attachment ──────────────────

@router.get(
    "/files/{attachment_id}/url",
    response_model=FileAttachmentOut,
)
async def get_file_url(
    attachment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    attachment = await storage_service.get_attachment(db, attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return await _enrich(attachment)


# ── Delete ─────────────────────────────────────────────────────

@router.delete(
    "/files/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_file(
    attachment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    attachment = await storage_service.get_attachment(db, attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Only the uploader or an admin can delete
    if attachment.uploaded_by != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed to delete this file")

    await storage_service.delete_attachment(db, attachment)
