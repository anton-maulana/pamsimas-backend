from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastcrud import PaginatedListResponse, paginated_response
from sqlalchemy import func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import DuplicateValueException, NotFoundException
from ...crud.crud_customers import crud_customers
from ...crud.crud_images import crud_images
from ...models.customer import Customer
from ...schemas.customer import (
    CustomerCreate,
    CustomerCreateInternal,
    CustomerRead,
    CustomerUpdate,
    CustomerUpdateInternal,
)
from ...schemas.image import ImageRead, ImageStatus, ImageUpdateInternal

router = APIRouter(tags=["customers"])


@router.post("", response_model=CustomerRead, status_code=201)
async def create_customer(
    customer_in: CustomerCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    if customer_in.meter_number:
        existing = await crud_customers.get(db=db, meter_number=customer_in.meter_number, is_deleted=False)
        if existing:
            raise DuplicateValueException("Meter number already registered")

    if customer_in.meter_image_id is not None:
        image = await crud_images.get(
            db=db, id=customer_in.meter_image_id, is_deleted=False, schema_to_select=ImageRead
        )
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


@router.get("", response_model=PaginatedListResponse[CustomerRead])
async def list_customers(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 20,
    search: str | None = None,
    rt: str | None = None,
    rw: str | None = None,
    status: str | None = None,
    officer_id: int | None = None,
    meter_number: str | None = None,
    unbilled_month: int | None = None,
    unbilled_year: int | None = None,
) -> dict[str, Any]:
    offset = (page - 1) * items_per_page

    # Handle unbilled customers query
    if unbilled_month is not None and unbilled_year is not None:
        # Get list of customer ids who have bills in this period
        from ...models.bill import Bill
        billed_stmt = select(Bill.customer_id).where(
            Bill.billing_month == unbilled_month,
            Bill.billing_year == unbilled_year
        )
        # Select customers who are NOT in that list
        stmt = (
            select(Customer)
            .where(Customer.is_deleted == False)
            .where(Customer.id.not_in(billed_stmt))
        )
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Customer.name.ilike(search_term),
                    Customer.meter_number.ilike(search_term),
                    Customer.address.ilike(search_term),
                )
            )
        if rt is not None:
            stmt = stmt.where(Customer.rt == rt)
        if rw is not None:
            stmt = stmt.where(Customer.rw == rw)
        if status is not None:
            stmt = stmt.where(Customer.status == status)

        stmt = stmt.order_by(Customer.name).offset(offset).limit(items_per_page)
        result = await db.execute(stmt)
        rows = result.unique().scalars().all()
        data = [CustomerRead.model_validate(row).model_dump(by_alias=True) for row in rows]

        # Count total
        count_stmt = select(func.count(Customer.id)).where(
            Customer.is_deleted == False,
            Customer.id.not_in(billed_stmt)
        )
        if search:
            count_term = f"%{search}%"
            count_stmt = count_stmt.where(
                or_(
                    Customer.name.ilike(count_term),
                    Customer.meter_number.ilike(count_term),
                    Customer.address.ilike(count_term),
                )
            )
        if rt is not None:
            count_stmt = count_stmt.where(Customer.rt == rt)
        if rw is not None:
            count_stmt = count_stmt.where(Customer.rw == rw)
        if status is not None:
            count_stmt = count_stmt.where(Customer.status == status)
            
        total_count_result = await db.execute(count_stmt)
        total_count = total_count_result.scalar() or 0

        return paginated_response(
            crud_data={"data": data, "total_count": total_count}, page=page, items_per_page=items_per_page
        )

    # If there's a search query, use raw SQLAlchemy for LIKE filtering
    if search:
        search_term = f"%{search}%"
        stmt = (
            select(Customer)
            .where(Customer.is_deleted == False)  # noqa: E712
            .where(
                or_(
                    Customer.name.ilike(search_term),
                    Customer.meter_number.ilike(search_term),
                    Customer.address.ilike(search_term),
                )
            )
        )
        if rt is not None:
            stmt = stmt.where(Customer.rt == rt)
        if rw is not None:
            stmt = stmt.where(Customer.rw == rw)
        if status is not None:
            stmt = stmt.where(Customer.status == status)
        if officer_id is not None:
            stmt = stmt.where(Customer.officer_id == officer_id)
        if meter_number is not None:
            stmt = stmt.where(Customer.meter_number == meter_number)

        stmt = stmt.order_by(Customer.name).offset(offset).limit(items_per_page)
        result = await db.execute(stmt)
        rows = result.unique().scalars().all()
        data = [CustomerRead.model_validate(row).model_dump(by_alias=True) for row in rows]

        # Count total for paginated response
        count_stmt = select(Customer).where(not_(Customer.is_deleted))
        if search:
            count_stmt = count_stmt.where(
                or_(
                    Customer.name.ilike(search_term),
                    Customer.meter_number.ilike(search_term),
                    Customer.address.ilike(search_term),
                )
            )
        if rt is not None:
            count_stmt = count_stmt.where(Customer.rt == rt)
        if rw is not None:
            count_stmt = count_stmt.where(Customer.rw == rw)
        if status is not None:
            count_stmt = count_stmt.where(Customer.status == status)
        if officer_id is not None:
            count_stmt = count_stmt.where(Customer.officer_id == officer_id)
        if meter_number is not None:
            count_stmt = count_stmt.where(Customer.meter_number == meter_number)

        count_stmt = select(func.count()).select_from(count_stmt.subquery())
        total_count_result = await db.execute(count_stmt)
        total_count = total_count_result.scalar() or 0

        return paginated_response(
            crud_data={"data": data, "total_count": total_count}, page=page, items_per_page=items_per_page
        )

    # Without search – use FastCRUD
    filters: dict[str, Any] = {"is_deleted": False}
    if rt is not None:
        filters["rt"] = rt
    if rw is not None:
        filters["rw"] = rw
    if status is not None:
        filters["status"] = status
    if officer_id is not None:
        filters["officer_id"] = officer_id
    if meter_number is not None:
        filters["meter_number"] = meter_number

    result = await crud_customers.get_multi(
        db=db,
        offset=offset,
        limit=items_per_page,
        schema_to_select=CustomerRead,
        sort_columns=["name"],
        **filters,
    )
    return paginated_response(crud_data=result, page=page, items_per_page=items_per_page)


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
    current_user: Annotated[dict, Depends(get_current_user)],
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
        image = await crud_images.get(
            db=db, id=customer_in.meter_image_id, is_deleted=False, schema_to_select=ImageRead
        )
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
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> None:
    customer = await crud_customers.get(db=db, id=customer_id, is_deleted=False)
    if not customer:
        raise NotFoundException("Customer not found")
    await crud_customers.delete(db=db, id=customer_id)
