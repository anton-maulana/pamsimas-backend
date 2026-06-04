import uuid as uuid_pkg
from datetime import datetime

from pydantic import BaseModel, Field


class PaymentBase(BaseModel):
    """Base payment schema"""

    bill_id: int
    amount_paid: float = Field(..., gt=0)
    payment_method: str = Field(..., min_length=1, max_length=50)
    reference_number: str | None = Field(None, max_length=100)
    status: str = Field(default="completed")
    notes: str | None = None


class PaymentCreate(PaymentBase):
    """Schema for creating a payment"""

    pass


class CumulativePaymentCreate(BaseModel):
    """Schema for cumulative payments across multiple bills"""

    customer_id: int
    amount_paid: float = Field(..., gt=0)
    payment_method: str = Field(..., min_length=1, max_length=50)
    reference_number: str | None = Field(None, max_length=100)
    notes: str | None = None


class PaymentUpdate(BaseModel):
    """Schema for updating a payment"""

    amount_paid: float | None = None
    payment_method: str | None = None
    reference_number: str | None = None
    status: str | None = None
    notes: str | None = None


class PaymentRead(PaymentBase):
    """Schema for reading payment data"""

    id: int
    uuid: uuid_pkg.UUID
    payment_date: datetime
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True
