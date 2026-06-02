import uuid as uuid_pkg
from datetime import datetime

from pydantic import BaseModel, Field


class BillBase(BaseModel):
    """Base bill schema"""

    customer_id: int
    billing_month: int = Field(..., ge=1, le=12)
    billing_year: int = Field(..., ge=2000, le=2100)
    meter_start: int = Field(..., ge=0)
    meter_end: int = Field(..., ge=0)
    usage: int = Field(..., ge=0)
    amount: float = Field(..., gt=0)
    status: str = Field(default="unpaid")
    notes: str | None = None


class BillCreate(BillBase):
    """Schema for creating a bill"""

    pass


class BillUpdate(BaseModel):
    """Schema for updating a bill"""

    meter_end: int | None = None
    usage: int | None = None
    amount: float | None = None
    status: str | None = None
    notes: str | None = None


class BillRead(BillBase):
    """Schema for reading bill data"""

    id: int
    uuid: uuid_pkg.UUID
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True
