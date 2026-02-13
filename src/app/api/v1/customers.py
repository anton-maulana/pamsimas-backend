from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, HTTPException
from fastcrud import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException
from ...crud.crud_customer import crud_customer
from ...schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate

router = APIRouter(tags=["customers"], prefix="/customers")


@router.post("", response_model=CustomerRead, status_code=201)
async def create_customer(
    customer: CustomerCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Create a new customer"""
    created_customer = await crud_customer.create(db=db, object=customer, schema_to_select=CustomerRead)

    if created_customer is None:
        raise NotFoundException("Failed to create customer")

    return created_customer


@router.get("", response_model=PaginatedListResponse[CustomerRead])
async def get_customers(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 10,
) -> dict[str, Any]:
    """Get all customers with pagination"""
    offset = compute_offset(page, items_per_page)

    customers = await crud_customer.get_multi(
        db=db,
        offset=offset,
        limit=items_per_page,
        schema_to_select=CustomerRead,
        is_deleted=False,
    )

    count = await crud_customer.count(db=db, is_deleted=False)

    return paginated_response(crud_data=customers, page=page, items_per_page=items_per_page)


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(
    customer_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Get a specific customer by ID"""
    customer = await crud_customer.get(db=db, id=customer_id, is_deleted=False, schema_to_select=CustomerRead)

    if customer is None:
        raise NotFoundException("Customer not found")

    return customer


@router.put("/{customer_id}", response_model=CustomerRead)
async def update_customer(
    customer_id: int,
    customer_update: CustomerUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Update a customer"""
    db_customer = await crud_customer.get(db=db, id=customer_id, is_deleted=False)

    if db_customer is None:
        raise NotFoundException("Customer not found")

    updated_customer = await crud_customer.update(
        db=db,
        object=customer_update,
        id=customer_id,
        schema_to_select=CustomerRead,
    )

    if updated_customer is None:
        raise NotFoundException("Failed to update customer")

    return updated_customer


@router.delete("/{customer_id}", status_code=204)
async def delete_customer(
    customer_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> None:
    """Delete (soft delete) a customer"""
    db_customer = await crud_customer.get(db=db, id=customer_id, is_deleted=False)

    if db_customer is None:
        raise NotFoundException("Customer not found")

    await crud_customer.delete(db=db, id=customer_id)
