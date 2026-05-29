import uuid as uuid_pkg
from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from ..core.schemas import PersistentDeletion, TimestampSchema, UUIDSchema


class ImageStatus(str, Enum):
    TEMPORARY = "temporary"
    USED = "used"


class ImageBase(BaseModel):
    filename: Annotated[str, Field(examples=["image.jpg"])]
    file_size: Annotated[int, Field(gt=0, examples=[1024000])]
    mime_type: Annotated[str, Field(examples=["image/jpeg"])]
    status: Annotated[ImageStatus, Field(default=ImageStatus.TEMPORARY, examples=["temporary"])]


class Image(TimestampSchema, ImageBase, UUIDSchema, PersistentDeletion):
    file_path: Annotated[str, Field(examples=["/uploads/images/image.jpg"])]
    uploaded_by_user_id: int


class ImageRead(BaseModel):
    id: int
    uuid: uuid_pkg.UUID
    filename: Annotated[str, Field(examples=["image.jpg"])]
    file_path: Annotated[str, Field(examples=["/uploads/images/image.jpg"])]
    file_size: Annotated[int, Field(examples=[1024000])]
    mime_type: Annotated[str, Field(examples=["image/jpeg"])]
    status: ImageStatus
    uploaded_by_user_id: int
    created_at: datetime


class ImageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: Annotated[str, Field(examples=["image.jpg"])]
    file_size: Annotated[int, Field(gt=0, examples=[1024000])]
    mime_type: Annotated[str, Field(examples=["image/jpeg"])]
    status: Annotated[ImageStatus, Field(default=ImageStatus.TEMPORARY)]


class ImageCreateInternal(ImageCreate):
    file_path: str
    uploaded_by_user_id: int


class ImageUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Annotated[ImageStatus | None, Field(examples=["used"], default=None)]


class ImageUpdateInternal(ImageUpdate):
    updated_at: datetime


class ImageDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_deleted: bool
    deleted_at: datetime
