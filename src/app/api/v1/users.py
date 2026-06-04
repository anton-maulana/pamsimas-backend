from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastcrud import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_superuser, get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import DuplicateValueException, ForbiddenException, NotFoundException
from ...core.security import blacklist_token, get_password_hash, oauth2_scheme
from ...crud.crud_customers import crud_customers
from ...crud.crud_images import crud_images
from ...crud.crud_rate_limit import crud_rate_limits
from ...crud.crud_tier import crud_tiers
from ...crud.crud_users import crud_users
from ...schemas.image import ImageRead, ImageStatus, ImageUpdateInternal
from ...schemas.tier import TierRead
from ...schemas.user import (
    UserCreate,
    UserCreateInternal,
    UserPasswordReset,
    UserRead,
    UserRole,
    UserUpdate,
)

router = APIRouter(tags=["users"])


@router.post("/user", response_model=UserRead, status_code=201)
async def write_user(
    request: Request, user: UserCreate, db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict[str, Any]:
    email_row = await crud_users.exists(db=db, email=user.email)
    if email_row:
        raise DuplicateValueException("Email is already registered")

    username_row = await crud_users.exists(db=db, username=user.username)
    if username_row:
        raise DuplicateValueException("Username not available")

    user_internal_dict = user.model_dump()
    areas_data = user_internal_dict.pop("areas", [])
    user_internal_dict["hashed_password"] = get_password_hash(password=user_internal_dict["password"])
    del user_internal_dict["password"]

    user_internal = UserCreateInternal(**user_internal_dict)
    created_user = await crud_users.create(db=db, object=user_internal, schema_to_select=UserRead)

    if created_user is None:
        raise NotFoundException("Failed to create user")

    # Add areas
    if areas_data:
        from ...models.officer_area import OfficerArea
        for area in areas_data:
            db_area = OfficerArea(user_id=created_user["id"], **area)
            db.add(db_area)
        await db.commit()
        # Refresh to include areas in response
        db_user = await crud_users.get(db=db, id=created_user["id"], schema_to_select=UserRead)
        return db_user

    return created_user


@router.get("/users", response_model=PaginatedListResponse[UserRead])
async def read_users(
    request: Request, db: Annotated[AsyncSession, Depends(async_get_db)], page: int = 1, items_per_page: int = 10
) -> dict:
    users_data = await crud_users.get_multi(
        db=db,
        offset=compute_offset(page, items_per_page),
        limit=items_per_page,
        is_deleted=False,
    )

    response: dict[str, Any] = paginated_response(crud_data=users_data, page=page, items_per_page=items_per_page)
    return response


@router.get(
    "/user/officers", response_model=PaginatedListResponse[UserRead], dependencies=[Depends(get_current_superuser)]
)
async def read_officers(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 10,
    rt: str | None = None,
    rw: str | None = None,
) -> dict:
    """List all users with role=officer with pagination. Supports filtering by RT/RW."""
    from ...models.officer_area import OfficerArea
    from ...models.user import User
    from sqlalchemy import select, func
    from sqlalchemy.orm import selectinload

    # 1. Start with base statement
    stmt = select(User).where(User.role == UserRole.officer, User.is_deleted == False)

    # 2. Add filtering if rt/rw provided
    if rt is not None or rw is not None:
        area_stmt = select(OfficerArea.user_id)
        if rt is not None:
            area_stmt = area_stmt.where(OfficerArea.rt == rt)
        if rw is not None:
            area_stmt = area_stmt.where(OfficerArea.rw == rw)
        stmt = stmt.where(User.id.in_(area_stmt))

    # 3. Calculate count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count_res = await db.execute(count_stmt)
    total_count = total_count_res.scalar() or 0
    
    # 4. Fetch paginated data with areas eager loaded
    fetch_stmt = stmt.options(selectinload(User.areas)).offset(compute_offset(page, items_per_page)).limit(items_per_page)
    result = await db.execute(fetch_stmt)
    rows = result.scalars().all()
    
    # 5. Build response list
    data = [UserRead.model_validate(row) for row in rows]
    officers_data = {"data": data, "total_count": total_count}

    return paginated_response(crud_data=officers_data, page=page, items_per_page=items_per_page)


@router.post("/user/officers", response_model=UserRead, status_code=201, dependencies=[Depends(get_current_superuser)])
async def create_officer(
    request: Request, user: UserCreate, db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict[str, Any]:
    """Create a new officer (petugas) account."""
    email_row = await crud_users.exists(db=db, email=user.email)
    if email_row:
        raise DuplicateValueException("Email is already registered")

    username_row = await crud_users.exists(db=db, username=user.username)
    if username_row:
        raise DuplicateValueException("Username not available")

    user_internal_dict = user.model_dump()
    areas_data = user_internal_dict.pop("areas", [])
    user_internal_dict["hashed_password"] = get_password_hash(password=user_internal_dict["password"])
    del user_internal_dict["password"]

    user_internal = UserCreateInternal(**user_internal_dict)
    created_user = await crud_users.create(db=db, object=user_internal, schema_to_select=UserRead)

    if created_user is None:
        raise NotFoundException("Failed to create user")

    # Add areas
    if areas_data:
        from ...models.officer_area import OfficerArea
        for area in areas_data:
            db_area = OfficerArea(user_id=created_user["id"], **area)
            db.add(db_area)
        await db.commit()
        # Refresh to include areas in response
        db_user = await crud_users.get(db=db, id=created_user["id"], schema_to_select=UserRead)
        return db_user

    return created_user



@router.post("/petugas", response_model=UserRead, status_code=201, dependencies=[Depends(get_current_superuser)])
async def create_petugas(
    request: Request,
    user: UserCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Create a new petugas (officer) account. Superuser only. [DEPRECATED: Use /user/officers]"""
    if await crud_users.exists(db=db, email=user.email):
        raise DuplicateValueException("Email is already registered")

    if await crud_users.exists(db=db, username=user.username):
        raise DuplicateValueException("Username not available")

    user_internal_dict = user.model_dump()
    user_internal_dict["hashed_password"] = get_password_hash(password=user_internal_dict.pop("password"))
    user_internal = UserCreateInternal(**user_internal_dict)
    created_user = await crud_users.create(db=db, object=user_internal, schema_to_select=UserRead)

    if created_user is None:
        raise NotFoundException("Failed to create petugas")

    return created_user


@router.get(
    "/petugas/{username}/customers/count",
    dependencies=[Depends(get_current_superuser)],
)
async def read_petugas_customer_count(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Return the number of customers assigned to a petugas. [DEPRECATED: Use /user/{user_id}/customers/count]"""
    db_user = await crud_users.get(db=db, username=username, schema_to_select=UserRead)
    if db_user is None:
        raise NotFoundException("Petugas not found")

    customers_data = await crud_customers.get_multi(db=db, officer_id=db_user["id"], is_deleted=False)
    return {"username": username, "customer_count": customers_data["total_count"]}


@router.get(
    "/user/officers/{user_id}/customers/count",
    dependencies=[Depends(get_current_superuser)],
)
async def read_officer_customer_count(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Return the number of customers assigned to a specific officer."""
    db_user = await crud_users.get(db=db, id=user_id, schema_to_select=UserRead)
    if db_user is None:
        raise NotFoundException("Officer not found")

    if db_user["role"] != UserRole.officer:
        raise ForbiddenException("User is not an officer")

    customers_data = await crud_customers.get_multi(db=db, officer_id=user_id, is_deleted=False)
    return {"user_id": user_id, "customer_count": customers_data["total_count"]}


@router.patch("/user/officers/{user_id}", dependencies=[Depends(get_current_superuser)])
async def update_officer(
    request: Request,
    user_id: int,
    user_update: UserUpdate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Update an officer's information."""
    db_user = await crud_users.get(db=db, id=user_id, is_deleted=False)
    if db_user is None:
        raise NotFoundException("Officer not found")

    update_data = user_update.model_dump(exclude_unset=True)
    areas_data = update_data.pop("areas", None)

    updated_user = await crud_users.update(db=db, id=user_id, object=update_data)

    if areas_data is not None:
        from ...models.officer_area import OfficerArea
        from sqlalchemy import delete
        # Clear existing areas
        await db.execute(delete(OfficerArea).where(OfficerArea.user_id == user_id))
        # Add new areas
        for area in areas_data:
            db_area = OfficerArea(user_id=user_id, **area)
            db.add(db_area)
        await db.commit()

    return await crud_users.get(db=db, id=user_id, schema_to_select=UserRead)


@router.delete("/user/officers/{user_id}", dependencies=[Depends(get_current_superuser)])
async def delete_officer(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Soft delete an officer."""
    db_user = await crud_users.get(db=db, id=user_id, is_deleted=False)
    if db_user is None:
        raise NotFoundException("Officer not found")

    await crud_users.delete(db=db, id=user_id)
    return {"message": "Officer deleted successfully"}


@router.patch("/user/officers/{user_id}/reset-password", dependencies=[Depends(get_current_superuser)])
async def reset_officer_password(
    request: Request,
    user_id: int,
    password_reset: UserPasswordReset,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Reset an officer's password."""
    db_user = await crud_users.get(db=db, id=user_id, is_deleted=False)
    if db_user is None:
        raise NotFoundException("Officer not found")

    hashed_password = get_password_hash(password_reset.new_password)
    await crud_users.update(db=db, id=user_id, object={"hashed_password": hashed_password})
    return {"message": "Password reset successfully"}
