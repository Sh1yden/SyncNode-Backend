"""WebSocket-эндпоинт синхронизации заметок (CRDT)."""

from uuid import UUID

from fastapi import APIRouter, Query, WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database.core import (
    AsyncSessionLocal,
    hydrated_rooms,
    websocket_server,
    FastAPIWebsocketAdapter,
)
from app.database.models import Notes, NotesCollaborators

router = APIRouter(tags=["sync"])


async def _authorize(note_id: UUID, token: str, db: AsyncSession) -> bool:
    """Проверить токен и права доступа к заметке."""
    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
    except Exception:
        return False

    result = await db.execute(select(Notes).where(Notes.id == note_id))
    note = result.scalar_one_or_none()
    if note is None:
        return False

    if note.owner_id == user_id:
        return True

    result = await db.execute(
        select(NotesCollaborators).where(
            NotesCollaborators.note_id == note_id,
            NotesCollaborators.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def _hydrate_room(note_id: UUID, db: AsyncSession) -> None:
    """При первом открытии комнаты — подгрузить сохранённое состояние."""
    room_name = str(note_id)
    if room_name in hydrated_rooms:
        return

    room = await websocket_server.get_room(room_name)

    result = await db.execute(select(Notes.crdt_state).where(Notes.id == note_id))
    stored_state = result.scalar_one_or_none()
    if stored_state:
        room.ydoc.apply_update(stored_state)

    room.ydoc.observe(lambda event: _schedule_persist(note_id, room))
    hydrated_rooms.add(room_name)


def _schedule_persist(note_id: UUID, room) -> None:
    import asyncio

    asyncio.create_task(_persist_snapshot(note_id, room))


async def _persist_snapshot(note_id: UUID, room) -> None:
    """Сохранить полный снимок документа в Postgres."""
    snapshot = room.ydoc.get_update()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Notes).where(Notes.id == note_id))
        note = result.scalar_one_or_none()
        if note is None:
            return
        note.crdt_state = snapshot
        await db.commit()


@router.websocket("/notes/{note_id}/sync")
async def notes_sync(
    websocket: WebSocket,
    note_id: UUID,
    token: str = Query(...),
) -> None:
    await websocket.accept()

    async with AsyncSessionLocal() as db:
        if not await _authorize(note_id, token, db):
            await websocket.close(code=4401)
            return
        await _hydrate_room(note_id, db)

    adapter = FastAPIWebsocketAdapter(websocket, path=str(note_id))
    await websocket_server.serve(adapter)
