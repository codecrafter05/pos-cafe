from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OrderModifierSnapshot(BaseModel):
    group_name: str
    option_name: str
    extra_price: Decimal = Decimal("0")


class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(..., ge=1)
    modifiers: list[OrderModifierSnapshot] = []
    notes: str | None = Field(None, max_length=255)


class OrderCreate(BaseModel):
    items: list[OrderItemIn] = Field(..., min_length=1)
    customer_name: str | None = Field(None, max_length=100)
    customer_phone: str | None = Field(None, max_length=20)
    payment_method: Literal["cash", "card", "transfer"]
    notes: str | None = None


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str | None = None
    quantity: int
    unit_price: Decimal
    unit_cost: Decimal
    modifiers_snapshot: list[dict[str, Any]] | dict[str, Any] | None = None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: int
    user_id: int
    staff_username: str | None = None
    customer_name: str | None
    customer_phone: str | None
    total_amount: Decimal
    total_cost: Decimal
    profit: Decimal
    payment_method: str
    source: str
    status: str
    notes: str | None
    created_at: datetime
    items: list[OrderItemOut] = []

    model_config = ConfigDict(from_attributes=True)
