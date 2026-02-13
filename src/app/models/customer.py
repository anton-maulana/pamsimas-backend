import uuid as uuid_pkg
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from ..core.db.database import Base


class Customer(Base):
    """Customer model for PAMSIMAS water billing system"""

    __tablename__ = "customer"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True, init=False)

    # Customer identification
    name: Mapped[str] = mapped_column(String(100), index=True)
    address: Mapped[str] = mapped_column(String(255))
    meter_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    # Optional customer info
    phone: Mapped[str | None] = mapped_column(String(20), default=None)
    email: Mapped[str | None] = mapped_column(String(100), unique=True, index=True, default=None)
    meter_location: Mapped[str | None] = mapped_column(String(100), default=None)

    # Customer status
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, inactive, suspended
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)

    # Tracking
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), default_factory=uuid7, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
