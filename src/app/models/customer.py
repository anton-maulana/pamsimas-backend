from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .image import Image
    from .user import User

from ..core.db.database import Base


class Customer(Base):
    __tablename__ = "customer"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rt: Mapped[str] = mapped_column(String(5), nullable=False)
    rw: Mapped[str] = mapped_column(String(5), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)

    meter_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)

    officer_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), index=True, default=None)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")
    latitude: Mapped[float | None] = mapped_column(Float, default=None)
    longitude: Mapped[float | None] = mapped_column(Float, default=None)
    meter_image_id: Mapped[int | None] = mapped_column(ForeignKey("image.id"), index=True, default=None)

    officer: Mapped["User"] = relationship("User", foreign_keys=[officer_id], init=False)
    meter_image: Mapped["Image"] = relationship("Image", foreign_keys=[meter_image_id], init=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
