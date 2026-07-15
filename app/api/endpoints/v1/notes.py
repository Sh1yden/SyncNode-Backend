from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import get_current_user, require_note_access
from app.database.core import get_db
from app.database.models import AccessLevel, Notes, Users
from app.schemas import NoteCreateSchema, NoteResponseSchema

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=NoteResponseSchema,
    summary="Create a new note.",
)
async def create_note(
    payload: NoteCreateSchema,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteResponseSchema:
    note = Notes(owner_id=current_user.id, path=payload.path)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return NoteResponseSchema.model_validate(note)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[NoteResponseSchema],
    summary="List notes owned by the current user.",
)
async def list_notes(
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NoteResponseSchema]:
    result = await db.execute(select(Notes).where(Notes.owner_id == current_user.id))
    notes = result.scalars().all()
    # TODO: добавить заметки, где current_user — collaborator
    return [NoteResponseSchema.model_validate(note) for note in notes]


@router.get(
    "/{note_id}",
    status_code=status.HTTP_200_OK,
    response_model=NoteResponseSchema,
    summary="Get a note by id.",
)
async def get_note(
    note: Notes = Depends(require_note_access(AccessLevel.read)),
) -> NoteResponseSchema:
    return NoteResponseSchema.model_validate(note)


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a note.",
)
async def delete_note(
    note_id: UUID,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Notes).where(Notes.id == note_id))
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found.")
    if note.owner_id != current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only the owner can delete a note."
        )
    await db.delete(note)
    await db.commit()
