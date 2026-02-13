import uuid as uuid_pkg
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from ..core.db.database import Base


class Bill(Base):
    """Monthly billing record for each customer"""

    __tablename__ = "bill"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True, init=False)

    # Customer reference
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), index=True)

    # Billing period
    billing_month: Mapped[int] = mapped_column(Integer)  # Month (1-12)
    billing_year: Mapped[int] = mapped_column(Integer)  # Year (e.g., 2026)

    # Meter readings
    meter_start: Mapped[int] = mapped_column(Integer)  # Beginning meter reading (m³)
    meter_end: Mapped[int] = mapped_column(Integer)  # End meter reading (m³)
    usage: Mapped[int] = mapped_column(Integer)  # Calculated usage (meter_end - meter_start)

    # Billing amount
    amount: Mapped[float] = mapped_column(Numeric(10, 2))  # Bill amount in currency units
    status: Mapped[str] = mapped_column(String(20), default="unpaid")  # unpaid, paid, overdue

    # Additional info
    notes: Mapped[str | None] = mapped_column(String(500), default=None)

    # Tracking
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), default_factory=uuid7, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
