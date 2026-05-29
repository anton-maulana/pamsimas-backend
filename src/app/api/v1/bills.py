from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastcrud import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException
from ...crud.crud_bill import crud_bill
from ...crud.crud_customer import crud_customer
from ...schemas.bill import BillCreate, BillRead, BillUpdate

router = APIRouter(tags=["bills"], prefix="/bills")


@router.post("", response_model=BillRead, status_code=201)
async def create_bill(
    bill: BillCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Create a new bill"""
    # Verify customer exists
    customer = await crud_customer.get(db=db, id=bill.customer_id, is_deleted=False)
    if customer is None:
        raise NotFoundException("Customer not found")

    created_bill = await crud_bill.create(db=db, object=bill, schema_to_select=BillRead)

    if created_bill is None:
        raise NotFoundException("Failed to create bill")

    return created_bill


@router.get("", response_model=PaginatedListResponse[BillRead])
async def get_bills(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 10,
    customer_id: int | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """Get bills with optional filtering"""
    offset = compute_offset(page, items_per_page)

    filters = {}
    if customer_id:
        filters["customer_id"] = customer_id
    if status:
        filters["status"] = status

    bills = await crud_bill.get_multi(
        db=db,
        offset=offset,
        limit=items_per_page,
        schema_to_select=BillRead,
        **filters,
    )

    count = await crud_bill.count(db=db, **filters)

    return paginated_response(crud_data=bills, page=page, items_per_page=items_per_page)


@router.get("/{bill_id}", response_model=BillRead)
async def get_bill(
    bill_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Get a specific bill"""
    bill = await crud_bill.get(db=db, id=bill_id, schema_to_select=BillRead)

    if bill is None:
        raise NotFoundException("Bill not found")

    return bill


@router.put("/{bill_id}", response_model=BillRead)
async def update_bill(
    bill_id: int,
    bill_update: BillUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Update a bill"""
    db_bill = await crud_bill.get(db=db, id=bill_id)

    if db_bill is None:
        raise NotFoundException("Bill not found")

    updated_bill = await crud_bill.update(
        db=db,
        object=bill_update,
        id=bill_id,
        schema_to_select=BillRead,
    )

    if updated_bill is None:
        raise NotFoundException("Failed to update bill")

    return updated_bill


@router.delete("/{bill_id}", status_code=204)
async def delete_bill(
    bill_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> None:
    """Delete a bill"""
    db_bill = await crud_bill.get(db=db, id=bill_id)

    if db_bill is None:
        raise NotFoundException("Bill not found")

    await crud_bill.delete(db=db, id=bill_id)
