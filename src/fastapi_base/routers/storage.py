from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from fastapi_base.models import User
from fastapi_base.deps import get_current_user
from fastapi_base.services.storage import storage_service

router = APIRouter(prefix="/storage", tags=["Storage"])


class FileUploadResponse(BaseModel):
    file_id: str
    file_key: str
    thumb_key: str | None
    filename: str
    content_type: str
    size_bytes: int
    is_image: bool
    presigned_url: str


class PresignedUrlResponse(BaseModel):
    file_key: str
    presigned_url: str


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        metadata = await storage_service.upload_file(
            file_content=content,
            original_filename=file.filename,
            content_type=file.content_type,
        )
        presigned_url = await storage_service.generate_presigned_url(
            metadata["file_key"]
        )
        return FileUploadResponse(**metadata, presigned_url=presigned_url)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to upload file: {str(e)}"
        )


@router.get("/presigned-url", response_model=PresignedUrlResponse)
async def get_presigned_url(
    file_key: str,
    current_user: User = Depends(get_current_user),
):
    try:
        url = await storage_service.generate_presigned_url(file_key)
        return PresignedUrlResponse(file_key=file_key, presigned_url=url)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"File not found or error generating URL: {str(e)}",
        )


@router.delete("/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_key: str,
    current_user: User = Depends(get_current_user),
):
    try:
        await storage_service.delete_file(file_key)
        if "thumb_" not in file_key:
            parts = file_key.split("/")
            if len(parts) >= 3:
                thumb_key = f"{parts[0]}/{parts[1]}/thumb_{parts[2]}"
                await storage_service.delete_file(thumb_key)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete file: {str(e)}"
        )
