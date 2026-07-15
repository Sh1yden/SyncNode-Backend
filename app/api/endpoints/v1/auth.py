"""Эндпоинты авторизации: register, login, refresh, logout."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import settings
from app.core import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.database.core import get_db
from app.database.core import get_redis
from app.database.models import Users
from app.schemas import (
    TokenRefreshSchema,
    TokenResponseSchema,
    UserCreateSchema,
    UserLoginSchema,
    UserResponseSchema,
)
from app.api import get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_TTL_SECONDS = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400


async def _issue_token_pair(user_id: UUID, redis: Redis) -> TokenResponseSchema:
    """Создать и сохранить новую пару access/refresh токенов."""
    access_token = create_access_token(user_id)
    refresh_token = generate_refresh_token()

    await redis.setex(
        f"refresh:{hash_refresh_token(refresh_token)}",
        _REFRESH_TTL_SECONDS,
        str(user_id),
    )

    return TokenResponseSchema(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenResponseSchema,
    summary="Register a new user.",
)
async def register(
    payload: UserCreateSchema,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenResponseSchema:
    """Создать пользователя и сразу авторизовать его."""
    user = Users(
        name=payload.name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this name already exists.",
        )

    await db.refresh(user)
    return await _issue_token_pair(user.id, redis)


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=TokenResponseSchema,
    summary="Login a user.",
)
async def login(
    payload: UserLoginSchema,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenResponseSchema:
    """Проверить учётные данные и выдать пару токенов."""
    result = await db.execute(select(Users).where(Users.name == payload.name))
    user = result.scalar_one_or_none()

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid name or password.",
    )

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise invalid_credentials

    return await _issue_token_pair(user.id, redis)


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    response_model=TokenResponseSchema,
    summary="Refresh a token pair.",
)
async def refresh(
    payload: TokenRefreshSchema,
    redis: Redis = Depends(get_redis),
) -> TokenResponseSchema:
    """Ротировать refresh-токен и выдать новую пару."""
    key = f"refresh:{hash_refresh_token(payload.refresh_token)}"
    stored_user_id = await redis.get(key)

    if stored_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or expired.",
        )

    await redis.delete(key)
    return await _issue_token_pair(UUID(stored_user_id), redis)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout a user.",
)
async def logout(
    payload: TokenRefreshSchema,
    redis: Redis = Depends(get_redis),
) -> dict:
    """Отозвать refresh-токен."""
    key = f"refresh:{hash_refresh_token(payload.refresh_token)}"
    await redis.delete(key)
    return {"detail": "Logged out."}


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserResponseSchema,
    summary="Get current authenticated user.",
)
async def me(
    current_user: Users = Depends(get_current_user),
) -> UserResponseSchema:
    return UserResponseSchema.model_validate(current_user)
