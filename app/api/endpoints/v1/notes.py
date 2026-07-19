from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import get_current_user, require_note_access
from app.database.core import get_db
from app.database.models import AccessLevel, Notes, NotesCollaborators, Users
from app.schemas import (
    CollaboratorAddSchema,
    CollaboratorResponseSchema,
    NoteContentResponseSchema,
    NoteCreateSchema,
    NoteResponseSchema,
)

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    response_model=NoteResponseSchema,
    summary="Create a new note (or return existing one with same path).",
)
async def create_note(
    payload: NoteCreateSchema,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteResponseSchema:
    existing = await db.execute(
        select(Notes).where(
            Notes.owner_id == current_user.id,
            Notes.path == payload.path,
        )
    )
    note = existing.scalar_one_or_none()
    if note is not None:
        return NoteResponseSchema.model_validate(note)

    note = Notes(owner_id=current_user.id, path=payload.path)
    db.add(note)
    try:
        await db.commit()
        await db.refresh(note)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A note with this path already exists.",
        )
    return NoteResponseSchema.model_validate(note)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=list[NoteResponseSchema],
    summary="List notes accessible by the current user.",
)
async def list_notes(
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NoteResponseSchema]:
    result = await db.execute(
        select(Notes).where(
            or_(
                Notes.owner_id == current_user.id,
                Notes.id.in_(
                    select(NotesCollaborators.note_id).where(
                        NotesCollaborators.user_id == current_user.id
                    )
                ),
            )
        )
    )
    notes = result.scalars().all()
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
    status_code=status.HTTP_200_OK,
    summary="Delete a note.",
)
async def delete_note(
    note_id: UUID,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
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
    return {"detail": "Note deleted."}


@router.patch(
    "/{note_id}",
    status_code=status.HTTP_200_OK,
    response_model=NoteResponseSchema,
    summary="Update a note path (rename).",
)
async def rename_note(
    note_id: UUID,
    payload: NoteCreateSchema,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteResponseSchema:
    result = await db.execute(select(Notes).where(Notes.id == note_id))
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found.")
    if note.owner_id != current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only the owner can rename a note."
        )

    duplicate = await db.execute(
        select(Notes).where(
            Notes.owner_id == current_user.id,
            Notes.path == payload.path,
            Notes.id != note_id,
        )
    )
    if duplicate.scalar_one_or_none() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Another note with this path already exists.",
        )

    note.path = payload.path
    await db.commit()
    await db.refresh(note)
    return NoteResponseSchema.model_validate(note)


@router.get(
    "/{note_id}/content",
    status_code=status.HTTP_200_OK,
    response_model=NoteContentResponseSchema,
    summary="Get the current text content of a note.",
)
async def get_note_content(
    note: Notes = Depends(require_note_access(AccessLevel.read)),
) -> NoteContentResponseSchema:
    content = ""
    if note.crdt_state is not None:
        from pycrdt import Doc, Text
        doc = Doc()
        doc.apply_update(note.crdt_state)
        content = str(doc.get("content", type=Text))

    return NoteContentResponseSchema(
        content=content,
        updated_at=note.updated_at,
    )


@router.put(
    "/{note_id}/content",
    status_code=status.HTTP_200_OK,
    response_model=NoteContentResponseSchema,
    summary="Upload text content for a note (converts to CRDT state).",
)
async def upload_note_content(
    note_id: UUID,
    payload: NoteContentResponseSchema,
    note: Notes = Depends(require_note_access(AccessLevel.write)),
    db: AsyncSession = Depends(get_db),
) -> NoteContentResponseSchema:
    from pycrdt import Doc, Text

    doc = Doc()
    text = doc.get("content", type=Text)
    text += payload.content

    note.crdt_state = doc.get_update()
    note.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(note)

    return NoteContentResponseSchema(
        content=payload.content,
        updated_at=note.updated_at,
    )


@router.post(
    "/{note_id}/collaborators",
    status_code=status.HTTP_201_CREATED,
    response_model=CollaboratorResponseSchema,
    summary="Add a collaborator to a note.",
)
async def add_collaborator(
    payload: CollaboratorAddSchema,
    note: Notes = Depends(require_note_access(AccessLevel.admin)),
    db: AsyncSession = Depends(get_db),
) -> CollaboratorResponseSchema:
    if payload.user_id == note.owner_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Owner already has full access.",
        )

    result = await db.execute(
        select(Users).where(Users.id == payload.user_id)
    )
    target_user = result.scalar_one_or_none()
    if target_user is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    collab = NotesCollaborators(
        note_id=note.id,
        user_id=payload.user_id,
        access_level=payload.access_level,
    )
    db.add(collab)

    try:
        await db.commit()
        await db.refresh(collab)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="User is already a collaborator on this note.",
        )

    return CollaboratorResponseSchema(
        id=collab.id,
        note_id=collab.note_id,
        user_id=collab.user_id,
        user_name=target_user.name,
        access_level=collab.access_level,
    )


@router.delete(
    "/{note_id}/collaborators/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a collaborator from a note.",
)
async def remove_collaborator(
    user_id: UUID,
    note: Notes = Depends(require_note_access(AccessLevel.admin)),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(NotesCollaborators).where(
            NotesCollaborators.note_id == note.id,
            NotesCollaborators.user_id == user_id,
        )
    )
    collab = result.scalar_one_or_none()
    if collab is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Collaborator not found.",
        )
    await db.delete(collab)
    await db.commit()


@router.get(
    "/{note_id}/collaborators",
    status_code=status.HTTP_200_OK,
    response_model=list[CollaboratorResponseSchema],
    summary="List collaborators of a note.",
)
async def list_collaborators(
    note: Notes = Depends(require_note_access(AccessLevel.read)),
    db: AsyncSession = Depends(get_db),
) -> list[CollaboratorResponseSchema]:
    result = await db.execute(
        select(NotesCollaborators, Users.name)
        .join(Users, NotesCollaborators.user_id == Users.id)
        .where(NotesCollaborators.note_id == note.id)
    )
    rows = result.all()
    return [
        CollaboratorResponseSchema(
            id=row.NotesCollaborators.id,
            note_id=row.NotesCollaborators.note_id,
            user_id=row.NotesCollaborators.user_id,
            user_name=row.name,
            access_level=row.NotesCollaborators.access_level,
        )
        for row in rows
    ]
