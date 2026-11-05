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

NormalizedEmail = Annotated[EmailStr, AfterValidator(_normalize_email)]
Password = Annotated[
    str,
    Field(min_length=8, max_length=72),
]


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: NormalizedEmail
    username: str | None = Field(default=None, min_length=3, max_length=50)
    password: Password


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: NormalizedEmail | None = None
    username: str | None = Field(default=None, min_length=3, max_length=50)
    password: Password | None = None

    @model_validator(mode="after")
    def validate_update(self) -> "UserUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        if "email" in self.model_fields_set and self.email is None:
            raise ValueError("email cannot be null")
        if "username" in self.model_fields_set and self.username is None:
            raise ValueError("username cannot be null")
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
    username: str | None = None
    role: UserRole
    is_active: bool
    created_at: datetime
