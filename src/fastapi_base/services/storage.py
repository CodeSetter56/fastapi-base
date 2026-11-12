import io
import mimetypes
import uuid
from typing import Any, AsyncContextManager, cast

import aioboto3
from PIL import Image
from sqlmodel import col
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_base.config import settings
from fastapi_base.models import FileAttachment


class StorageService:
    def __init__(self) -> None:
        self.endpoint_url = settings.s3_endpoint_url
        self.access_key_id = settings.s3_access_key_id
        self.secret_access_key = settings.s3_secret_access_key
        self.bucket_name = settings.s3_bucket_name
        self.region_name = settings.s3_region_name

    def _get_session(self) -> aioboto3.Session:
        return aioboto3.Session(
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region_name,
        )

    def _get_client(self) -> AsyncContextManager[Any]:
        return cast(
            AsyncContextManager[Any],
            self._get_session().client("s3", endpoint_url=self.endpoint_url),
        )

    async def ensure_bucket_exists(self) -> None:
        async with self._get_client() as client:
            try:
                await client.head_bucket(Bucket=self.bucket_name)
            except Exception:
                try:
                    if self.region_name == "us-east-1":
                        await client.create_bucket(Bucket=self.bucket_name)
                    else:
                        await client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={
                                "LocationConstraint": self.region_name
                            },
                        )
                except Exception:
                    pass  # Bucket might already exist or be owned by us

    # ── S3 operations ──────────────────────────────────────────────

    async def upload_to_s3(
        self,
        file_content: bytes,
        original_filename: str,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """Upload a file to S3 and return metadata dict (no DB write)."""
        await self.ensure_bucket_exists()

        if not content_type:
            content_type, _ = mimetypes.guess_type(original_filename)
            content_type = content_type or "application/octet-stream"

        file_id = uuid.uuid4()
        file_key = f"uploads/{file_id}/{original_filename}"
        thumb_key: str | None = None
        thumb_content: bytes | None = None

        # Generate thumbnail for images
        is_image = content_type.startswith("image/")
        if is_image:
            try:
                img = Image.open(io.BytesIO(file_content))
                img.thumbnail((300, 300))
                thumb_io = io.BytesIO()
                img_format = img.format if img.format else "JPEG"
                img.save(thumb_io, format=img_format, quality=85)
                thumb_content = thumb_io.getvalue()
                thumb_key = f"uploads/{file_id}/thumb_{original_filename}"
            except Exception:
                is_image = False

        async with self._get_client() as client:
            await client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=file_content,
                ContentType=content_type,
            )
            if is_image and thumb_key and thumb_content:
                await client.put_object(
                    Bucket=self.bucket_name,
                    Key=thumb_key,
                    Body=thumb_content,
                    ContentType=content_type,
                )

        return {
            "file_key": file_key,
            "thumb_key": thumb_key,
            "filename": original_filename,
            "content_type": content_type,
            "size_bytes": len(file_content),
        }

    async def generate_presigned_url(self, file_key: str, expiration: int = 3600) -> str:
        async with self._get_client() as client:
            url: str = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_key},
                ExpiresIn=expiration,
            )
            return url

    async def delete_from_s3(self, file_key: str) -> None:
        async with self._get_client() as client:
            try:
                await client.delete_object(Bucket=self.bucket_name, Key=file_key)
            except Exception:
                pass

    # ── DB + S3 combined operations ────────────────────────────────

    async def attach_file(
        self,
        db: AsyncSession,
        *,
        file_content: bytes,
        original_filename: str,
        content_type: str | None,
        owner_type: str,
        owner_id: uuid.UUID,
        uploaded_by: uuid.UUID,
        label: str | None = None,
    ) -> FileAttachment:
        """Upload to S3 and create a FileAttachment row."""
        meta = await self.upload_to_s3(file_content, original_filename, content_type)

        attachment = FileAttachment(
            owner_type=owner_type,
            owner_id=owner_id,
            label=label,
            file_key=meta["file_key"],
            thumb_key=meta["thumb_key"],
            filename=meta["filename"],
            content_type=meta["content_type"],
            size_bytes=meta["size_bytes"],
            uploaded_by=uploaded_by,
        )
        db.add(attachment)
        await db.commit()
        await db.refresh(attachment)
        return attachment

    async def list_attachments(
        self,
        db: AsyncSession,
        *,
        owner_type: str,
        owner_id: uuid.UUID,
    ) -> list[FileAttachment]:
        result = await db.execute(
            select(FileAttachment)
            .where(col(FileAttachment.owner_type == owner_type) & col(FileAttachment.owner_id == owner_id))
            .order_by(col(FileAttachment.created_at))
        )
        return list(result.scalars().all())

    async def get_attachment(self, db: AsyncSession, attachment_id: uuid.UUID) -> FileAttachment | None:
        return await db.get(FileAttachment, attachment_id)

    async def delete_attachment(self, db: AsyncSession, attachment: FileAttachment) -> None:
        """Delete from S3 and remove the DB row."""
        await self.delete_from_s3(attachment.file_key)
        if attachment.thumb_key:
            await self.delete_from_s3(attachment.thumb_key)
        await db.delete(attachment)
        await db.commit()


storage_service = StorageService()
