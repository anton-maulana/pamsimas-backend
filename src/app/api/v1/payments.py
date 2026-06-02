from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastcrud import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException
from ...crud.crud_bill import crud_bill
from ...crud.crud_payment import crud_payment
from ...schemas.payment import PaymentCreate, PaymentRead, PaymentUpdate

router = APIRouter(tags=["payments"], prefix="/payments")


@router.post("", response_model=PaymentRead, status_code=201)
async def create_payment(
    payment: PaymentCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Record a payment for a bill"""
    # Verify bill exists
    bill = await crud_bill.get(db=db, id=payment.bill_id)
    if bill is None:
        raise NotFoundException("Bill not found")

    created_payment = await crud_payment.create(db=db, object=payment, schema_to_select=PaymentRead)

    if created_payment is None:
        raise NotFoundException("Failed to create payment")

    return created_payment


@router.get("", response_model=PaginatedListResponse[PaymentRead])
async def get_payments(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 10,
    bill_id: int | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """Get payments with optional filtering"""
    offset = compute_offset(page, items_per_page)

    filters = {}
    if bill_id:
        filters["bill_id"] = bill_id
    if status:
        filters["status"] = status

    payments = await crud_payment.get_multi(
        db=db,
        offset=offset,
        limit=items_per_page,
        schema_to_select=PaymentRead,
        **filters,
    )

    return paginated_response(crud_data=payments, page=page, items_per_page=items_per_page)


@router.get("/{payment_id}", response_model=PaymentRead)
async def get_payment(
    payment_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Get a specific payment"""
    payment = await crud_payment.get(db=db, id=payment_id, schema_to_select=PaymentRead)

    if payment is None:
        raise NotFoundException("Payment not found")

    return payment


@router.put("/{payment_id}", response_model=PaymentRead)
async def update_payment(
    payment_id: int,
    payment_update: PaymentUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Update a payment"""
    db_payment = await crud_payment.get(db=db, id=payment_id)

    if db_payment is None:
        raise NotFoundException("Payment not found")

    updated_payment = await crud_payment.update(
        db=db,
        object=payment_update,
        id=payment_id,
        schema_to_select=PaymentRead,
    )

    if updated_payment is None:
        raise NotFoundException("Failed to update payment")

    return updated_payment


@router.delete("/{payment_id}", status_code=204)
async def delete_payment(
    payment_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> None:
    """Delete a payment"""
    db_payment = await crud_payment.get(db=db, id=payment_id)

    if db_payment is None:
        raise NotFoundException("Payment not found")

    await crud_payment.delete(db=db, id=payment_id)
