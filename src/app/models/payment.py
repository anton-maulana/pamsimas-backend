import uuid as uuid_pkg
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from ..core.db.database import Base


class Payment(Base):
    """Payment records for bills"""

    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True, init=False)

    # Bill reference
    bill_id: Mapped[int] = mapped_column(ForeignKey("bill.id"), index=True)

    # Payment details
    amount_paid: Mapped[float] = mapped_column(Numeric(10, 2))  # Amount paid in currency units
    payment_method: Mapped[str] = mapped_column(String(50))  # cash, bank_transfer, check, etc.
    reference_number: Mapped[str | None] = mapped_column(String(100), unique=True, default=None)  # Transaction ID

    # Payment status
    status: Mapped[str] = mapped_column(String(20), default="completed")  # completed, pending, failed
    notes: Mapped[str | None] = mapped_column(String(500), default=None)

    # Tracking
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), default_factory=uuid7, unique=True)
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
