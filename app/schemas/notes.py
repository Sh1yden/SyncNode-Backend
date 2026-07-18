from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.database.models import AccessLevel


class BaseNoteSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class NoteCreateSchema(BaseNoteSchema):
    path: str = Field(..., min_length=1, max_length=1024)


class NoteResponseSchema(BaseNoteSchema):
    id: UUID
    owner_id: UUID
    path: str
    updated_at: datetime


class NoteContentResponseSchema(BaseNoteSchema):
    content: str
    updated_at: datetime


class CollaboratorAddSchema(BaseNoteSchema):
    user_id: UUID
    access_level: AccessLevel


class CollaboratorResponseSchema(BaseNoteSchema):
    id: UUID
    note_id: UUID
    user_id: UUID
    user_name: str
    access_level: AccessLevel
