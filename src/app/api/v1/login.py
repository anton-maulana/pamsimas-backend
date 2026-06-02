from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import UnauthorizedException
from ...core.schemas import Token
from ...core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    TokenType,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    verify_token,
)

router = APIRouter(tags=["login"])


@router.post("/login", response_model=Token)
async def login_for_access_token(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, str]:
    user = await authenticate_user(username_or_email=form_data.username, password=form_data.password, db=db)
    if not user:
        raise UnauthorizedException("Wrong username, email or password.")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # We add role and id to the JWT so the frontend can check user permissions
    token_data = {
        "sub": user["username"],
        "id": user["id"],
        "role": user["role"]
    }

    access_token = await create_access_token(data=token_data, expires_delta=access_token_expires)

    refresh_token = await create_refresh_token(data={"sub": user["username"]})
    #max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    # response.set_cookie(
    #     key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="lax", max_age=max_age
    # )

    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}


@router.post("/refresh")
async def refresh_access_token(request: Request, db: AsyncSession = Depends(async_get_db)) -> dict[str, str]:
    refresh_token = request.cookies.get("refresh_token")
    # For clients that send refresh_token in body instead of cookies
    if not refresh_token:
        try:
            body = await request.json()
            refresh_token = body.get("refresh_token")
        except Exception:
            pass

    # Also support form data for refresh_token
    if not refresh_token:
        try:
            form = await request.form()
            refresh_token = form.get("refresh_token")
        except Exception:
            pass

    if not refresh_token:
        raise UnauthorizedException("Refresh token missing.")

    user_data = await verify_token(refresh_token, TokenType.REFRESH, db)
    if not user_data:
        raise UnauthorizedException("Invalid refresh token.")

    from ...crud.crud_users import crud_users
    from ...schemas.user import UserRead

    db_user = await crud_users.get(db=db, username=user_data.username_or_email, schema_to_select=UserRead)
    if not db_user:
         raise UnauthorizedException("User no longer exists.")

    token_data = {
        "sub": db_user["username"],
        "id": db_user["id"],
        "role": db_user["role"].value if hasattr(db_user["role"], "value") else db_user["role"]
    }

    new_access_token = await create_access_token(data=token_data)
    return {"access_token": new_access_token, "token_type": "bearer"}
