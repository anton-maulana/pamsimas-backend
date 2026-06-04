from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import BadRequestException, NotFoundException
from ...crud.crud_customers import crud_customers
from ...crud.crud_images import crud_images
from ...crud.crud_meter_readings import crud_meter_readings
from ...schemas.image import ImageRead
from ...schemas.meter_reading import (
    MeterReadingCreate,
    MeterReadingCreateInternal,
    MeterReadingRead,
    MeterReadingUpdate,
    MeterReadingUpdateInternal,
)

router = APIRouter(tags=["meter-readings"])


@router.post("", response_model=MeterReadingRead, status_code=201)
async def create_meter_reading(
    reading_in: MeterReadingCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    # Validate customer exists
    customer = await crud_customers.get(db=db, id=reading_in.customer_id, is_deleted=False)
    if not customer:
        raise NotFoundException("Customer not found")

    # Validate image exists and mark it as used
    if reading_in.image_id is not None:
        image = await crud_images.get(db=db, id=reading_in.image_id, is_deleted=False, schema_to_select=ImageRead)
        if not image:
            raise NotFoundException("Image not found")
        if image["uploaded_by_user_id"] != current_user["id"]:
            raise BadRequestException("Image does not belong to current user")

    # Compute usage automatically
    internal = MeterReadingCreateInternal(**reading_in.model_dump())
    created = await crud_meter_readings.create(db=db, object=internal, schema_to_select=MeterReadingRead)

    # Update customer's current meter reading
    from ...schemas.customer import CustomerUpdateInternal
    await crud_customers.update(
        db=db,
        object=CustomerUpdateInternal(meter_number=str(reading_in.current_meter), updated_at=datetime.now(UTC)),
        id=reading_in.customer_id,
        is_deleted=False,
    )

    # Mark image as used after successful creation
    if reading_in.image_id is not None:
        from ...schemas.image import ImageStatus, ImageUpdateInternal
        await crud_images.update(
            db=db,
            object=ImageUpdateInternal(status=ImageStatus.USED, updated_at=datetime.now(UTC)),
            id=reading_in.image_id,
        )

    return created


@router.get("", response_model=list[MeterReadingRead])
async def list_meter_readings(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    customer_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    filters: dict[str, Any] = {"is_deleted": False}
    if customer_id is not None:
        filters["customer_id"] = customer_id

    result = await crud_meter_readings.get_multi(
        db=db,
        offset=skip,
        limit=limit,
        schema_to_select=MeterReadingRead,
        **filters,
    )
    return result["data"]


@router.get("/{reading_id}", response_model=MeterReadingRead)
async def get_meter_reading(
    reading_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    reading = await crud_meter_readings.get(db=db, id=reading_id, is_deleted=False, schema_to_select=MeterReadingRead)
    if not reading:
        raise NotFoundException("Meter reading not found")
    return reading


@router.patch("/{reading_id}", response_model=MeterReadingRead)
async def update_meter_reading(
    reading_id: int,
    reading_in: MeterReadingUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    reading = await crud_meter_readings.get(db=db, id=reading_id, is_deleted=False, schema_to_select=MeterReadingRead)
    if not reading:
        raise NotFoundException("Meter reading not found")

    if reading_in.image_id is not None:
        image = await crud_images.get(db=db, id=reading_in.image_id, is_deleted=False, schema_to_select=ImageRead)
        if not image:
            raise NotFoundException("Image not found")

    # Build update with current values for usage computation
    current = reading_in.current_meter if reading_in.current_meter is not None else reading["current_meter"]
    previous = reading_in.previous_meter if reading_in.previous_meter is not None else reading["previous_meter"]

    update_data = MeterReadingUpdateInternal(
        **reading_in.model_dump(),
        current_meter=current,
        previous_meter=previous,
        updated_at=datetime.now(UTC),
    )
    updated = await crud_meter_readings.update(
        db=db,
        object=update_data,
        id=reading_id,
        is_deleted=False,
        schema_to_select=MeterReadingRead,
    )
    return updated


@router.delete("/{reading_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meter_reading(
    reading_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> None:
    reading = await crud_meter_readings.get(db=db, id=reading_id, is_deleted=False)
    if not reading:
        raise NotFoundException("Meter reading not found")
    await crud_meter_readings.delete(db=db, id=reading_id)
