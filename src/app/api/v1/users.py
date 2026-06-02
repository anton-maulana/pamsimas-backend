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
    user_internal_dict["hashed_password"] = get_password_hash(password=user_internal_dict["password"])
    del user_internal_dict["password"]

    user_internal = UserCreateInternal(**user_internal_dict)
    created_user = await crud_users.create(db=db, object=user_internal, schema_to_select=UserRead)

    if created_user is None:
        raise NotFoundException("Failed to create user")

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
) -> dict:
    """List all users with role=officer with pagination."""
    officers_data = await crud_users.get_multi(
        db=db,
        offset=compute_offset(page, items_per_page),
        limit=items_per_page,
        is_deleted=False,
        role=UserRole.officer,
    )
    response: dict[str, Any] = paginated_response(crud_data=officers_data, page=page, items_per_page=items_per_page)
    return response


@router.post("/user/officers", response_model=UserRead, status_code=201, dependencies=[Depends(get_current_superuser)])
async def create_officer(
    request: Request,
    user: UserCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Create a new officer account. Superuser only."""
    if await crud_users.exists(db=db, email=user.email):
        raise DuplicateValueException("Email is already registered")

    if await crud_users.exists(db=db, username=user.username):
        raise DuplicateValueException("Username not available")

    user_internal_dict = user.model_dump()

    # We must explicitly pop password since it is not part of UserCreateInternal
    password = user_internal_dict.pop("password")

    user_internal_dict["hashed_password"] = get_password_hash(password=password)
    user_internal = UserCreateInternal(**user_internal_dict)

    created_user = await crud_users.create(db=db, object=user_internal, schema_to_select=UserRead)

    if created_user is None:
        raise NotFoundException("Failed to create officer")

    return created_user


@router.get("/user/me/", response_model=UserRead)
async def read_users_me(request: Request, current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
    return current_user


@router.get("/user/{username}", response_model=UserRead)
async def read_user(
    request: Request, username: str, db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict[str, Any]:
    db_user = await crud_users.get(db=db, username=username, is_deleted=False, schema_to_select=UserRead)
    if db_user is None:
        raise NotFoundException("User not found")

    return db_user


@router.patch("/user/{username}")
async def patch_user(
    request: Request,
    values: UserUpdate,
    username: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, str]:
    db_user = await crud_users.get(db=db, username=username)
    if db_user is None:
        raise NotFoundException("User not found")

    db_username = db_user["username"]
    db_email = db_user["email"]

    if db_username != current_user["username"] and not current_user.get("is_superuser", False):
        raise ForbiddenException()

    if values.email is not None and values.email != db_email:
        if await crud_users.exists(db=db, email=values.email):
            raise DuplicateValueException("Email is already registered")

    if values.username is not None and values.username != db_username:
        if await crud_users.exists(db=db, username=values.username):
            raise DuplicateValueException("Username not available")

    if values.profile_image_id is not None:
        image = await crud_images.get(db=db, id=values.profile_image_id, is_deleted=False, schema_to_select=ImageRead)
        if not image:
            raise NotFoundException("Image not found")
        if image["uploaded_by_user_id"] != current_user["id"]:
            raise ForbiddenException()

    await crud_users.update(db=db, object=values, username=username)

    if values.profile_image_id is not None:
        await crud_images.update(
            db=db,
            object=ImageUpdateInternal(status=ImageStatus.USED, updated_at=datetime.now(UTC)),
            id=values.profile_image_id,
        )

    return {"message": "User updated"}


@router.delete("/user/{username}")
async def erase_user(
    request: Request,
    username: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    token: str = Depends(oauth2_scheme),
) -> dict[str, str]:
    db_user = await crud_users.get(db=db, username=username, schema_to_select=UserRead)
    if not db_user:
        raise NotFoundException("User not found")

    if username != current_user["username"] and not current_user.get("is_superuser", False):
        raise ForbiddenException()

    await crud_users.delete(db=db, username=username)
    await blacklist_token(token=token, db=db)
    return {"message": "User deleted"}


@router.delete("/db_user/{username}", dependencies=[Depends(get_current_superuser)])
async def erase_db_user(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    token: str = Depends(oauth2_scheme),
) -> dict[str, str]:
    db_user = await crud_users.exists(db=db, username=username)
    if not db_user:
        raise NotFoundException("User not found")

    await crud_users.db_delete(db=db, username=username)
    await blacklist_token(token=token, db=db)
    return {"message": "User deleted from the database"}


@router.get("/user/{username}/rate_limits", dependencies=[Depends(get_current_superuser)])
async def read_user_rate_limits(
    request: Request, username: str, db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict[str, Any]:
    db_user = await crud_users.get(db=db, username=username, schema_to_select=UserRead)
    if db_user is None:
        raise NotFoundException("User not found")

    user_dict = dict(db_user)
    if db_user["tier_id"] is None:
        user_dict["tier_rate_limits"] = []
        return user_dict

    db_tier = await crud_tiers.get(db=db, id=db_user["tier_id"], schema_to_select=TierRead)
    if db_tier is None:
        raise NotFoundException("Tier not found")

    db_rate_limits = await crud_rate_limits.get_multi(db=db, tier_id=db_tier["id"])

    user_dict["tier_rate_limits"] = db_rate_limits["data"]

    return user_dict


@router.get("/user/{username}/tier")
async def read_user_tier(
    request: Request, username: str, db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict | None:
    db_user = await crud_users.get(db=db, username=username, schema_to_select=UserRead)
    if db_user is None:
        raise NotFoundException("User not found")

    if db_user["tier_id"] is None:
        return None

    db_tier = await crud_tiers.get(db=db, id=db_user["tier_id"], schema_to_select=TierRead)
    if not db_tier:
        raise NotFoundException("Tier not found")

    user_dict = dict(db_user)
    tier_dict = dict(db_tier)

    for key, value in tier_dict.items():
        user_dict[f"tier_{key}"] = value

    return user_dict


@router.patch("/user/{user_id}/reset-password", dependencies=[Depends(get_current_superuser)])
async def reset_user_password(
    request: Request,
    user_id: int,
    values: UserPasswordReset,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, str]:
    """Reset a user's password. Superuser only."""
    db_user = await crud_users.get(db=db, id=user_id, schema_to_select=UserRead)
    if db_user is None:
        raise NotFoundException("User not found")

    hashed_password = get_password_hash(password=values.new_password)
    await crud_users.update(db=db, object={"hashed_password": hashed_password}, id=user_id)
    return {"message": f"Password for user {db_user['name']} has been reset"}


# ─── Petugas (Officer) Endpoints ──────────────────────────────────────────────


@router.get(
    "/user/officers/{user_id}", response_model=UserRead, dependencies=[Depends(get_current_superuser)]
)
async def read_officer(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Get a specific officer by ID."""
    db_user = await crud_users.get(db=db, id=user_id, is_deleted=False, schema_to_select=UserRead)
    if db_user is None or db_user["role"] != UserRole.officer:
        raise NotFoundException("Officer not found")

    return db_user

@router.patch("/user/officers/{user_id}", dependencies=[Depends(get_current_superuser)])
async def patch_officer(
    request: Request,
    values: UserUpdate,
    user_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, str]:
    db_user = await crud_users.get(db=db, id=user_id, is_deleted=False)
    if db_user is None or db_user["role"] != UserRole.officer:
        raise NotFoundException("Officer not found")

    if values.email is not None and values.email != db_user["email"]:
        if await crud_users.exists(db=db, email=values.email):
            raise DuplicateValueException("Email is already registered")

    if values.username is not None and values.username != db_user["username"]:
        if await crud_users.exists(db=db, username=values.username):
            raise DuplicateValueException("Username not available")

    await crud_users.update(db=db, object=values, id=user_id)
    return {"message": "Officer updated"}

@router.delete("/user/officers/{user_id}", dependencies=[Depends(get_current_superuser)])
async def erase_officer(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, str]:
    db_user = await crud_users.get(db=db, id=user_id, is_deleted=False)
    if not db_user or db_user["role"] != UserRole.officer:
        raise NotFoundException("Officer not found")

    await crud_users.delete(db=db, id=user_id)
    return {"message": "Officer deleted"}

@router.patch("/user/officers/{user_id}/reset-password", dependencies=[Depends(get_current_superuser)])
async def reset_officer_password(
    request: Request,
    user_id: int,
    values: UserPasswordReset,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, str]:
    """Reset an officer's password. Superuser only."""
    db_user = await crud_users.get(db=db, id=user_id, schema_to_select=UserRead)
    if db_user is None or db_user["role"] != UserRole.officer:
        raise NotFoundException("Officer not found")

    hashed_password = get_password_hash(password=values.new_password)
    await crud_users.update(db=db, object={"hashed_password": hashed_password}, id=user_id)
    return {"message": f"Password for officer {db_user['name']} has been reset"}

@router.get(
    "/user/officers/{user_id}/customers/count",
    dependencies=[Depends(get_current_superuser)],
)
async def read_officer_customer_count(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, Any]:
    """Return the number of customers assigned to an officer."""
    db_user = await crud_users.get(db=db, id=user_id, schema_to_select=UserRead)
    if db_user is None:
        raise NotFoundException("Officer not found")

    customers_data = await crud_customers.get_multi(db=db, officer_id=user_id, is_deleted=False)
    return {"user_id": user_id, "customer_count": customers_data["total_count"]}


# ─── Legacy Petugas Endpoints (Deprecated) ────────────────────────────────────


@router.get("/petugas", response_model=PaginatedListResponse[UserRead], dependencies=[Depends(get_current_superuser)])
async def read_petugas(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 10,
) -> dict:
    """List all non-superuser users (petugas/officers) with pagination. [DEPRECATED: Use /user/officers]"""
    petugas_data = await crud_users.get_multi(
        db=db,
        offset=compute_offset(page, items_per_page),
        limit=items_per_page,
        is_deleted=False,
        is_superuser=False,
    )
    response: dict[str, Any] = paginated_response(crud_data=petugas_data, page=page, items_per_page=items_per_page)
    return response


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
