from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import get_current_user
from app.database.core import get_db
from app.database.models import Users
from app.schemas import UserResponseSchema

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/search",
    status_code=status.HTTP_200_OK,
    response_model=list[UserResponseSchema],
    summary="Search users by name.",
)
async def search_users(
    q: str = Query(
        ...,
        min_length=2,
        max_length=255,
        description="Search query (min 2 chars)",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Max results",
    ),
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponseSchema]:
    result = await db.execute(
        select(Users)
        .where(Users.name.ilike(f"%{q}%"), Users.id != current_user.id)
        .limit(limit)
    )
    users = result.scalars().all()
    return [UserResponseSchema.model_validate(u) for u in users]
