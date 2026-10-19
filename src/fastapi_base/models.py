from datetime import UTC, datetime
from enum import StrEnum
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, Text, func, text
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class UserRole(StrEnum):
    user = "user"
    admin = "admin"


class User(SQLModel, table=True):
    __tablename__: ClassVar[str] = "users"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    email: str = Field(sa_type=Text, nullable=False, unique=True)
    password_hash: str = Field(sa_type=Text, nullable=False)
    role: str = Field(
        default=UserRole.user.value,
        sa_type=Text,
        nullable=False,
        sa_column_kwargs={"server_default": text("'user'")},
    )
    is_active: bool = Field(
        default=True,
        nullable=False,
        sa_column_kwargs={"server_default": text("true")},
    )
    token_version: int = Field(
        default=0,
        nullable=False,
        sa_column_kwargs={"server_default": text("0")},
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
        nullable=False,
        index=True,
        sa_column_kwargs={"server_default": func.now()},
    )


class Item(SQLModel, table=True):
    __tablename__: ClassVar[str] = "items"
    __table_args__ = (Index("ix_items_owner_id_created_at", "owner_id", "created_at"),)

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    owner_id: UUID = Field(
        foreign_key="users.id",
        ondelete="CASCADE",
        nullable=False,
    )
    title: str = Field(sa_type=Text, nullable=False)
    description: str | None = Field(default=None, sa_type=Text, nullable=True)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_type=DateTime(timezone=True),
        nullable=False,
        sa_column_kwargs={"server_default": func.now()},
    )
