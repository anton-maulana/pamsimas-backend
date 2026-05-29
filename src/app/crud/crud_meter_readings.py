from fastcrud import FastCRUD

from ..models.meter_reading import MeterReading
from ..schemas.meter_reading import (
    MeterReadingCreateInternal,
    MeterReadingDelete,
    MeterReadingRead,
    MeterReadingUpdate,
    MeterReadingUpdateInternal,
)

CRUDMeterReading = FastCRUD[
    MeterReading,
    MeterReadingCreateInternal,
    MeterReadingUpdate,
    MeterReadingUpdateInternal,
    MeterReadingDelete,
    MeterReadingRead,
]
crud_meter_readings = CRUDMeterReading(MeterReading)
