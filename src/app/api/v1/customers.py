from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_superuser, get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import BadRequestException, DuplicateValueException, NotFoundException
from ...crud.crud_customers import crud_customers
from ...crud.crud_images import crud_images
from ...schemas.customer import CustomerCreate, CustomerCreateInternal, CustomerRead, CustomerUpdate, CustomerUpdateInternal
from ...schemas.image import ImageRead, ImageStatus, ImageUpdateInternal

router = APIRouter(tags=["customers"])


@router.post("", response_model=CustomerRead, status_code=201)
async def create_customer(
    customer_in: CustomerCreate,
    current_user: Annotated[dict, Depends(get_current_superuser)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    if customer_in.meter_number:
        existing = await crud_customers.get(db=db, meter_number=customer_in.meter_number, is_deleted=False)
        if existing:
            raise DuplicateValueException("Meter number already registered")

    if customer_in.meter_image_id is not None:
        image = await crud_images.get(db=db, id=customer_in.meter_image_id, is_deleted=False, schema_to_select=ImageRead)
        if not image:
            raise NotFoundException("Image not found")

    internal = CustomerCreateInternal(**customer_in.model_dump())
    created = await crud_customers.create(db=db, object=internal, schema_to_select=CustomerRead)

    if customer_in.meter_image_id is not None:
        await crud_images.update(
            db=db,
            object=ImageUpdateInternal(status=ImageStatus.USED, updated_at=datetime.now(UTC)),
            id=customer_in.meter_image_id,
        )

    return created


@router.get("", response_model=list[CustomerRead])
async def list_customers(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    skip: int = 0,
    limit: int = 100,
    rt_rw: str | None = None,
    status: str | None = None,
    officer_id: int | None = None,
    meter_number: str | None = None,
) -> list[dict[str, Any]]:
    filters = {"is_deleted": False}
    if rt_rw is not None:
        filters["rt_rw"] = rt_rw
    if status is not None:
        filters["status"] = status
    if officer_id is not None:
        filters["officer_id"] = officer_id
    if meter_number is not None:
        filters["meter_number"] = meter_number

    result = await crud_customers.get_multi(
        db=db,
        offset=skip,
        limit=limit,
        schema_to_select=CustomerRead,
        **filters
    )
    return result["data"]


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(
    customer_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    customer = await crud_customers.get(db=db, id=customer_id, is_deleted=False, schema_to_select=CustomerRead)
    if not customer:
        raise NotFoundException("Customer not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerRead)
async def update_customer(
    customer_id: int,
    customer_in: CustomerUpdate,
    current_user: Annotated[dict, Depends(get_current_superuser)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    customer = await crud_customers.get(db=db, id=customer_id, is_deleted=False, schema_to_select=CustomerRead)
    if not customer:
        raise NotFoundException("Customer not found")

    if customer_in.meter_number:
        existing = await crud_customers.get(db=db, meter_number=customer_in.meter_number, is_deleted=False)
        if existing and existing["id"] != customer_id:
            raise DuplicateValueException("Meter number already registered")

    if customer_in.meter_image_id is not None:
        image = await crud_images.get(db=db, id=customer_in.meter_image_id, is_deleted=False, schema_to_select=ImageRead)
        if not image:
            raise NotFoundException("Image not found")

    update_data = CustomerUpdateInternal(**customer_in.model_dump(), updated_at=datetime.now(UTC))
    updated = await crud_customers.update(
        db=db, object=update_data, id=customer_id, is_deleted=False, schema_to_select=CustomerRead
    )

    if customer_in.meter_image_id is not None:
        await crud_images.update(
            db=db,
            object=ImageUpdateInternal(status=ImageStatus.USED, updated_at=datetime.now(UTC)),
            id=customer_in.meter_image_id,
        )

    return updated


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    current_user: Annotated[dict, Depends(get_current_superuser)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> None:
    customer = await crud_customers.get(db=db, id=customer_id, is_deleted=False)
    if not customer:
        raise NotFoundException("Customer not found")
    await crud_customers.delete(db=db, id=customer_id)
