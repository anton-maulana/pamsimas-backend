import uuid as uuid_pkg
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import UUID, DateTime, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from ..core.db.database import Base


class ImageStatus(str, Enum):
    TEMPORARY = "temporary"
    USED = "used"


class Image(Base):
    __tablename__ = "image"

    id: Mapped[int] = mapped_column("id", autoincrement=True, nullable=False, unique=True, primary_key=True, init=False)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column()
    mime_type: Mapped[str] = mapped_column(String(100))
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), default_factory=uuid7, unique=True)
    status: Mapped[str] = mapped_column(SQLEnum(ImageStatus), default=ImageStatus.TEMPORARY, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
