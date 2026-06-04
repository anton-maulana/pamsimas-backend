from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MeterReadingBase(BaseModel):
    customer_id: Annotated[int, Field(gt=0, examples=[1])]
    reading_date: Annotated[date, Field(examples=["2026-05-06"])]
    current_meter: Annotated[float, Field(ge=0, examples=[1250.5])]
    previous_meter: Annotated[float | None, Field(ge=0, default=None, examples=[1100.2])]
    image_id: Annotated[int | None, Field(default=None, examples=[1])]
    latitude: Annotated[float | None, Field(default=None, examples=[-6.2088])]
    longitude: Annotated[float | None, Field(default=None, examples=[106.8456])]


class MeterReadingRead(BaseModel):
    id: int
    customer_id: int
    reading_date: date
    current_meter: float
    previous_meter: float | None
    usage: float | None
    image_id: int | None
    latitude: float | None
    longitude: float | None
    created_at: datetime


class MeterReadingCreate(MeterReadingBase):
    model_config = ConfigDict(extra="forbid")


class MeterReadingCreateInternal(MeterReadingCreate):
    usage: int | None = None

    @model_validator(mode="after")
    def compute_usage(self) -> "MeterReadingCreateInternal":
        if self.previous_meter is not None:
            self.usage = max(0, self.current_meter - self.previous_meter)
        return self


class MeterReadingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reading_date: Annotated[date | None, Field(default=None)]
    current_meter: Annotated[float | None, Field(ge=0, default=None)]
    previous_meter: Annotated[float | None, Field(ge=0, default=None)]
    image_id: Annotated[int | None, Field(default=None)]
    latitude: Annotated[float | None, Field(default=None)]
    longitude: Annotated[float | None, Field(default=None)]


class MeterReadingUpdateInternal(MeterReadingUpdate):
    usage: int | None = None
    updated_at: datetime

    @model_validator(mode="after")
    def compute_usage(self) -> "MeterReadingUpdateInternal":
        if self.previous_meter is not None and self.current_meter is not None:
            self.usage = max(0, self.current_meter - self.previous_meter)
        return self


class MeterReadingDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_deleted: bool
    deleted_at: datetime
