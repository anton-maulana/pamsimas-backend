from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastcrud import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException
from ...crud.crud_bill import crud_bill
from ...crud.crud_payment import crud_payment
from ...schemas.payment import PaymentCreate, PaymentRead, PaymentUpdate, CumulativePaymentCreate

from sqlalchemy import select, func
from ...models.payment import Payment

router = APIRouter(tags=["payments"])


@router.get("/stats/income", status_code=200)
async def get_income_stats(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    month: int | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    """Get total income for a specific month and year"""
    from datetime import datetime
    now = datetime.now()
    target_month = month or now.month
    target_year = year or now.year

    # Filter payments by month and year of payment_date
    stmt = select(func.sum(Payment.amount_paid)).where(
        func.extract('month', Payment.payment_date) == target_month,
        func.extract('year', Payment.payment_date) == target_year,
        Payment.status == "completed"
    )
    
    result = await db.execute(stmt)
    total_income = result.scalar() or 0.0

    return {
        "month": target_month,
        "year": target_year,
        "total_income": float(total_income)
    }


@router.post("/cumulative", status_code=200)
async def create_cumulative_payment(
    payment: CumulativePaymentCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Record a cumulative payment and distribute it using FIFO across unpaid/partially paid bills"""
    # 1. Fetch all bills for the customer that are not fully paid, sorted by billing_year, billing_month (oldest first)
    # We do a select from database
    from sqlalchemy import select
    from ...models.bill import Bill
    from ...models.payment import Payment
    
    stmt = select(Bill).where(
        Bill.customer_id == payment.customer_id,
        Bill.status.in_(["unpaid", "partially_paid"])
    ).order_by(Bill.billing_year.asc(), Bill.billing_month.asc())
    
    result = await db.execute(stmt)
    bills = result.scalars().all()
    
    if not bills:
        return {"message": "No outstanding bills found for this customer", "payments_created": []}
        
    remaining_cash = payment.amount_paid
    payments_created = []
    
    for bill in bills:
        if remaining_cash <= 0:
            break
            
        # Get amount already paid for this bill
        stmt_pay = select(Payment).where(
            Payment.bill_id == bill.id,
            Payment.status == "completed"
        )
        res_pay = await db.execute(stmt_pay)
        bill_payments = res_pay.scalars().all()
        already_paid = sum([p.amount_paid for p in bill_payments])
        
        needed = float(bill.amount) - float(already_paid)
        if needed <= 0:
            # Mark paid if not already
            if bill.status != "paid":
                await crud_bill.update(db=db, object={"status": "paid"}, id=bill.id)
            continue
            
        # Allocate amount
        allocation = min(remaining_cash, needed)
        
        # Create payment record
        from ...schemas.payment import PaymentCreate as InnerPaymentCreate
        pay_obj = InnerPaymentCreate(
            bill_id=bill.id,
            amount_paid=allocation,
            payment_method=payment.payment_method,
            reference_number=payment.reference_number,
            status="completed",
            notes=payment.notes
        )
        
        created = await crud_payment.create(db=db, object=pay_obj, schema_to_select=PaymentRead)
        payments_created.append(created)
        
        # Update bill status
        new_total_paid = float(already_paid) + float(allocation)
        if new_total_paid >= float(bill.amount):
            await crud_bill.update(db=db, object={"status": "paid"}, id=bill.id)
        else:
            await crud_bill.update(db=db, object={"status": "partially_paid"}, id=bill.id)
            
        remaining_cash -= allocation

    # commit the session to make sure everything is saved
    await db.commit()

    return {
        "message": f"Successfully processed cumulative payment of {payment.amount_paid}",
        "remaining_amount": remaining_cash,
        "payments_created": payments_created
    }


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

    # Get total paid so far for this bill
    all_payments = await crud_payment.get_multi(
        db=db,
        bill_id=bill.id,
        status="completed"
    )
    
    total_paid = sum([p["amount_paid"] for p in all_payments.get("data", [])])

    # If total paid is greater than or equal to bill amount, mark as paid
    if total_paid >= bill.amount:
        await crud_bill.update(db=db, object={"status": "paid"}, id=bill.id)
    else:
        # Update bill status to partially_paid
        await crud_bill.update(db=db, object={"status": "partially_paid"}, id=bill.id)

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
