from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from ..core.schemas import PersistentDeletion, TimestampSchema


class CustomerBase(BaseModel):
    name: str
    rt_rw: Annotated[str, Field(alias="rtRw")]
    address: str
    phone_number: Annotated[str, Field(alias="phoneNumber")]

    meter_number: Annotated[str, Field(alias="meterNumber")]
    meter_image_id: Annotated[int | None, Field(default=None, alias="meterImageId")]

    officer_id: Annotated[int | None, Field(default=None, alias="officerId")]

    status: str = "ACTIVE"

    latitude: float | None = None
    longitude: float | None = None


class CustomerRead(BaseModel):
    id: int
    name: str
    rt_rw: Annotated[str, Field(alias="rtRw")]
    address: str
    phone_number: Annotated[str, Field(alias="phoneNumber")]

    meter_number: Annotated[str, Field(alias="meterNumber")]
    meter_image_id: Annotated[int | None, Field(alias="meterImageId")]

    officer_id: Annotated[int | None, Field(alias="officerId")]

    status: str

    latitude: float | None
    longitude: float | None
    created_at: datetime
    
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CustomerCreate(CustomerBase):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class CustomerCreateInternal(CustomerCreate):
    pass


class CustomerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str | None = None
    rt_rw: Annotated[str | None, Field(default=None, alias="rtRw")]
    address: str | None = None
    phone_number: Annotated[str | None, Field(default=None, alias="phoneNumber")]

    meter_number: Annotated[str | None, Field(default=None, alias="meterNumber")]
    meter_image_id: Annotated[int | None, Field(default=None, alias="meterImageId")]

    officer_id: Annotated[int | None, Field(default=None, alias="officerId")]

    status: str | None = None

    latitude: float | None = None
    longitude: float | None = None


class CustomerUpdateInternal(CustomerUpdate):
    updated_at: datetime


class CustomerDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_deleted: bool
    deleted_at: datetime
