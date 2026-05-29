import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...core.config import settings
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import BadRequestException, NotFoundException
from ...crud.crud_images import crud_images
from ...schemas.image import ImageCreateInternal, ImageDelete, ImageRead, ImageUpdate, ImageUpdateInternal

router = APIRouter(tags=["images"])

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path(settings.BASE_DIR) / "uploads" / "images"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=ImageRead, status_code=201)
async def upload_image(
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Upload an image file. Status is set to 'temporary' by default."""
    
    # Validate file
    if not file.filename:
        raise BadRequestException("Filename is required")
    
    # Allowed MIME types
    allowed_mime_types = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}
    if file.content_type not in allowed_mime_types:
        raise BadRequestException(f"File type {file.content_type} is not allowed. Allowed types: {allowed_mime_types}")
    
    # Max file size: 10MB
    MAX_FILE_SIZE = 10 * 1024 * 1024
    file_size = 0
    file_content = b""
    
    # Read file content
    while True:
        chunk = await file.read(1024)
        if not chunk:
            break
        file_size += len(chunk)
        if file_size > MAX_FILE_SIZE:
            raise BadRequestException(f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / 1024 / 1024}MB")
        file_content += chunk
    
    # Generate unique filename
    file_extension = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    try:
        with open(file_path, "wb") as f:
            f.write(file_content)
    except Exception as e:
        raise BadRequestException(f"Failed to save file: {str(e)}")
    
    # Save to database
    relative_path = f"/uploads/images/{unique_filename}"
    image_create = ImageCreateInternal(
        filename=file.filename,
        file_path=relative_path,
        file_size=file_size,
        mime_type=file.content_type,
        uploaded_by_user_id=current_user["id"],
    )
    
    created_image = await crud_images.create(db=db, object=image_create, schema_to_select=ImageRead)
    
    if created_image is None:
        raise BadRequestException("Failed to save image metadata to database")
    
    return created_image


@router.get("/{image_id}/download")
async def download_image(
    image_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> FileResponse:
    """Download an image by its ID."""
    
    image = await crud_images.get(db=db, id=image_id, is_deleted=False, schema_to_select=ImageRead)
    if not image:
        raise NotFoundException("Image not found")
    
    # Construct full file path
    file_path = UPLOAD_DIR / Path(image["file_path"]).name
    
    if not file_path.exists():
        raise NotFoundException("Image file not found on disk")
    
    return FileResponse(
        path=file_path,
        filename=image["filename"],
        media_type=image["mime_type"],
    )


@router.get("/{image_id}", response_model=ImageRead)
async def get_image(
    image_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Get image metadata by ID."""
    
    image = await crud_images.get(db=db, id=image_id, is_deleted=False, schema_to_select=ImageRead)
    if not image:
        raise NotFoundException("Image not found")
    
    return image


@router.get("", response_model=list[ImageRead])
async def list_user_images(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    skip: int = 0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List all images uploaded by the current user."""

    images_data = await crud_images.get_multi(
        db=db,
        uploaded_by_user_id=current_user["id"],
        is_deleted=False,
        offset=skip,
        limit=limit,
        schema_to_select=ImageRead,
    )

    return images_data["data"]


@router.patch("/{image_id}", response_model=ImageRead)
async def update_image_status(
    image_id: int,
    image_update: ImageUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Update image status (e.g., mark as 'used')."""

    image = await crud_images.get(db=db, id=image_id, is_deleted=False, schema_to_select=ImageRead)
    if not image:
        raise NotFoundException("Image not found")

    if image["uploaded_by_user_id"] != current_user["id"]:
        raise NotFoundException("Image not found")

    update_data = ImageUpdateInternal(
        status=image_update.status,
        updated_at=datetime.now(UTC),
    )

    updated_image = await crud_images.update(
        db=db,
        object=update_data,
        is_deleted=False,
        id=image_id,
        schema_to_select=ImageRead,
    )

    if not updated_image:
        raise BadRequestException("Failed to update image")

    return updated_image


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> None:
    """Soft delete an image."""

    image = await crud_images.get(db=db, id=image_id, is_deleted=False, schema_to_select=ImageRead)
    if not image:
        raise NotFoundException("Image not found")

    if image["uploaded_by_user_id"] != current_user["id"]:
        raise NotFoundException("Image not found")

    await crud_images.delete(db=db, id=image_id)
