from typing import Annotated, Any
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastcrud import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException
from ...crud.crud_bill import crud_bill
from ...crud.crud_customers import crud_customers
from ...schemas.bill import BillCreate, BillRead, BillUpdate

from sqlalchemy import select, func
from ...models.customer import Customer
from ...models.bill import Bill

router = APIRouter(tags=["bills"])


@router.get("/stats/summary", status_code=200)
async def get_bills_stats(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    month: int | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    """Get statistics about billed and unbilled customers for a specific month and year"""
    now = datetime.now()
    target_month = month or now.month
    target_year = year or now.year

    # 1. Total Active Customers
    total_cust_stmt = select(func.count(Customer.id)).where(Customer.is_deleted == False)
    total_cust_res = await db.execute(total_cust_stmt)
    total_customers = total_cust_res.scalar() or 0

    # 2. Get customer IDs who HAVE bills in target month/year
    billed_cust_stmt = select(Bill.customer_id).where(
        Bill.billing_month == target_month,
        Bill.billing_year == target_year
    )
    billed_cust_res = await db.execute(billed_cust_stmt)
    billed_customer_ids = set(billed_cust_res.scalars().all())

    billed_count = len(billed_customer_ids)
    unbilled_count = max(0, total_customers - billed_count)

    # 3. Of the billed ones, check how many are paid vs unpaid/partially paid
    paid_stmt = select(func.count(Bill.id)).where(
        Bill.billing_month == target_month,
        Bill.billing_year == target_year,
        Bill.status == "paid"
    )
    paid_res = await db.execute(paid_stmt)
    paid_count = paid_res.scalar() or 0

    unpaid_count = max(0, billed_count - paid_count)

    # 4. Nominal based stats
    total_billed_amt_stmt = select(func.sum(Bill.amount)).where(
        Bill.billing_month == target_month,
        Bill.billing_year == target_year
    )
    total_billed_amt_res = await db.execute(total_billed_amt_stmt)
    total_amount_billed = float(total_billed_amt_res.scalar() or 0.0)

    # Calculate actual collected amount for bills of this month
    from ...models.payment import Payment
    collected_amt_stmt = select(func.sum(Payment.amount_paid)).join(Bill).where(
        Bill.billing_month == target_month,
        Bill.billing_year == target_year,
        Payment.status == "completed"
    )
    collected_amt_res = await db.execute(collected_amt_stmt)
    total_amount_collected = float(collected_amt_res.scalar() or 0.0)

    return {
        "billing_month": target_month,
        "billing_year": target_year,
        "total_customers": total_customers,
        "billed_count": billed_count,
        "unbilled_count": unbilled_count,
        "paid_count": paid_count,
        "unpaid_count": unpaid_count,
        "total_amount_billed": total_amount_billed,
        "total_amount_collected": total_amount_collected
    }


@router.post("", response_model=BillRead, status_code=201)
async def create_bill(
    bill: BillCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Create a new bill"""
    # Verify customer exists
    customer = await crud_customers.get(db=db, id=bill.customer_id, is_deleted=False)
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
    billing_month: int | None = None,
    billing_year: int | None = None,
    rt: str | None = None,
    rw: str | None = None,
) -> dict[str, Any]:
    """Get bills with optional filtering"""
    offset = compute_offset(page, items_per_page)

    # Base query for bills
    stmt = select(Bill).join(Customer, Bill.customer_id == Customer.id)

    # Apply filters
    if customer_id:
        stmt = stmt.where(Bill.customer_id == customer_id)
    if status:
        stmt = stmt.where(Bill.status == status)
    if billing_month:
        stmt = stmt.where(Bill.billing_month == billing_month)
    if billing_year:
        stmt = stmt.where(Bill.billing_year == billing_year)
    
    # Parse and apply multiple RT/RW filters
    if rt:
        rt_list = [int(x) for x in rt.split(",")]
        stmt = stmt.where(Customer.rt.in_(rt_list))
    if rw:
        rw_list = [int(x) for x in rw.split(",")]
        stmt = stmt.where(Customer.rw.in_(rw_list))

    # Count total (before pagination)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count_result = await db.execute(count_stmt)
    total_count = total_count_result.scalar() or 0

    # Apply pagination and sorting
    stmt = stmt.order_by(Bill.created_at.desc()).offset(offset).limit(items_per_page)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    
    # Use schema to validate and format
    data = [BillRead.model_validate(row) for row in rows]

    return paginated_response(
        crud_data={"data": data, "total_count": total_count}, page=page, items_per_page=items_per_page
    )


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
