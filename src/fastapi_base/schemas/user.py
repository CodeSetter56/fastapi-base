from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)

from ..models import UserRole


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _validate_password_bytes(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("password must be at most 72 bytes")
    return value


NormalizedEmail = Annotated[EmailStr, AfterValidator(_normalize_email)]
Password = Annotated[
    str,
    Field(min_length=8, max_length=72),
    AfterValidator(_validate_password_bytes),
]


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: NormalizedEmail
    password: Password


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: NormalizedEmail | None = None
    password: Password | None = None

    @model_validator(mode="after")
    def validate_update(self) -> "UserUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        if "email" in self.model_fields_set and self.email is None:
            raise ValueError("email cannot be null")
        if "password" in self.model_fields_set and self.password is None:
            raise ValueError("password cannot be null")
        return self


class UserRoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: UserRole


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
