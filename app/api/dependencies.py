"""`get_current_user` - достаёт `Bearer`-токен через `HTTPBearer`/`OAuth2PasswordBearer`, валидирует, подтягивает `Users` из БД."""

from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import decode_access_token
from app.database.core import get_db
from app.database.models import Users, AccessLevel, Notes, NotesCollaborators


_bearer_scheme = HTTPBearer()
_ACCESS_ORDER = {
    AccessLevel.read: 0,
    AccessLevel.write: 1,
    AccessLevel.admin: 2,
}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Users:
    """Определить авторизованного пользователя по access-токену."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise credentials_error

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_error

    result = await db.execute(select(Users).where(Users.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_error

    return user


def require_note_access(min_level: AccessLevel = AccessLevel.read):
    """
    Фабрика зависимостей: доступ к заметке не ниже min_level.

    Владелец заметки имеет полный доступ всегда, без записи
    в notes_collaborators.
    """

    async def _dependency(
        note_id: UUID,
        current_user: Users = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> Notes:
        result = await db.execute(select(Notes).where(Notes.id == note_id))

        note = result.scalar_one_or_none()
        if note is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found.",
            )

        if note.owner_id == current_user.id:
            return note

        result = await db.execute(
            select(NotesCollaborators).where(
                NotesCollaborators.note_id == note_id,
                NotesCollaborators.user_id == current_user.id,
            )
        )
        collab = result.scalar_one_or_none()

        if (
            collab is None
            or _ACCESS_ORDER[collab.access_level] < _ACCESS_ORDER[min_level]
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough access to this note.",
            )

        return note

    return _dependency
