from datetime import datetime
import uuid as uuid_pkg

from pydantic import BaseModel, EmailStr, Field


class CustomerBase(BaseModel):
    """Base customer schema"""

    name: str = Field(..., min_length=1, max_length=100)
    address: str = Field(..., min_length=1, max_length=255)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    meter_number: str = Field(..., min_length=1, max_length=50)
    meter_location: str | None = Field(None, max_length=100)
    status: str = Field(default="active")


class CustomerCreate(CustomerBase):
    """Schema for creating a customer"""

    pass


class CustomerUpdate(BaseModel):
    """Schema for updating a customer"""

    name: str | None = None
    address: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    meter_location: str | None = None
    status: str | None = None


class CustomerRead(CustomerBase):
    """Schema for reading customer data"""

    id: int
    uuid: uuid_pkg.UUID
    is_deleted: bool
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None

    class Config:
        from_attributes = True
