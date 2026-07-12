from datetime import datetime
from uuid import UUID
from enum import Enum

from sqlalchemy import ForeignKey, Enum as SAEnum, LargeBinary, String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AccessLevel(str, Enum):
    read = "read"
    write = "write"
    admin = "admin"


class Users(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=func.uuid_generate_v4())
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now
    )

    # Relationships
    notes: Mapped[list["Notes"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class Notes(Base):
    __tablename__ = "notes"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=func.uuid_generate_v4())
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="cascade"))
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    crdt_state: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    owner: Mapped["Users"] = relationship(back_populates="notes")
    collaborators: Mapped[list["NotesCollaborators"]] = relationship(
        back_populates="note", cascade="all, delete-orphan"
    )


class NotesCollaborators(Base):
    __tablename__ = "notes_collaborators"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=func.uuid_generate_v4())
    note_id: Mapped[UUID] = mapped_column(ForeignKey("notes.id", ondelete="cascade"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="cascade"))
    access_level: Mapped[AccessLevel] = mapped_column(
        SAEnum(AccessLevel), nullable=False
    )

    # Relationships
    note: Mapped["Notes"] = relationship(back_populates="collaborators")
    user: Mapped["Users"] = relationship(back_populates="notes")
