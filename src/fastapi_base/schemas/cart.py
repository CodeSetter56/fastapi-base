from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from .item import ItemOut


class CartItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: UUID
    quantity: int = Field(default=1, ge=1, le=1000)


class CartItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: int = Field(ge=1, le=1000)


class CartItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    item_id: UUID
    quantity: int
    item: ItemOut | None = None
    created_at: datetime
    updated_at: datetime


class CartSummary(BaseModel):
    items: list[CartItemPublic]
    total_items: int
