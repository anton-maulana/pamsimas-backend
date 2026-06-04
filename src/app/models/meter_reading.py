from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class MeterReading(Base):
    __tablename__ = "meter_reading"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True, init=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), index=True)
    reading_date: Mapped[date] = mapped_column(Date)
    current_meter: Mapped[float] = mapped_column(Float)
    previous_meter: Mapped[float | None] = mapped_column(Float, default=None)
    usage: Mapped[float | None] = mapped_column(Float, default=None)
    image_id: Mapped[int | None] = mapped_column(ForeignKey("image.id"), index=True, default=None)
    latitude: Mapped[float | None] = mapped_column(Float, default=None)
    longitude: Mapped[float | None] = mapped_column(Float, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
