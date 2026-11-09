from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RatingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=1, le=5)
    review_text: str | None = Field(default=None, max_length=2000)

    @field_validator("review_text")
    @classmethod
    def clean_review(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class RatingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int | None = Field(default=None, ge=1, le=5)
    review_text: str | None = Field(default=None, max_length=2000)


class RatingPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    item_id: UUID
    score: int
    review_text: str | None
    created_at: datetime
    updated_at: datetime
