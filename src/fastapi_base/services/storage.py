import io
import mimetypes
import uuid
from typing import Any, AsyncContextManager, cast
import aioboto3
from PIL import Image
from fastapi_base.config import settings


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

    async def upload_file(
        self, file_content: bytes, original_filename: str, content_type: str | None = None
    ) -> dict[str, Any]:
        await self.ensure_bucket_exists()

        if not content_type:
            content_type, _ = mimetypes.guess_type(original_filename)
            content_type = content_type or "application/octet-stream"

        file_id = uuid.uuid4()
        ext = original_filename.split(".")[-1] if "." in original_filename else "bin"
        file_key = f"uploads/{file_id}/{original_filename}"
        thumb_key: str | None = None

        # Check if file is an image and generate thumbnail if so
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
            # Upload original
            await client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=file_content,
                ContentType=content_type,
            )

            # Upload thumbnail if generated
            if is_image and thumb_key:
                await client.put_object(
                    Bucket=self.bucket_name,
                    Key=thumb_key,
                    Body=thumb_content,
                    ContentType=content_type,
                )

        return {
            "file_id": str(file_id),
            "file_key": file_key,
            "thumb_key": thumb_key,
            "filename": original_filename,
            "content_type": content_type,
            "size_bytes": len(file_content),
            "is_image": is_image,
        }

    async def generate_presigned_url(self, file_key: str, expiration: int = 3600) -> str:
        async with self._get_client() as client:
            url: str = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_key},
                ExpiresIn=expiration,
            )
            return url

    async def delete_file(self, file_key: str) -> None:
        async with self._get_client() as client:
            try:
                await client.delete_object(Bucket=self.bucket_name, Key=file_key)
            except Exception:
                pass


storage_service = StorageService()
