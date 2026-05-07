from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.orders import OrderItemIn

GulfPhoneCountry = Literal["BH", "SA", "AE", "KW", "OM", "QA"]


class StoreModifierOut(BaseModel):
    group_name: str
    option_name: str
    extra_price: Decimal

    model_config = ConfigDict(from_attributes=True)


class StoreProductOut(BaseModel):
    id: int
    name: str
    name_ar: str | None
    price: Decimal
    description: str | None
    image_url: str | None
    modifiers: list[StoreModifierOut] = []

    model_config = ConfigDict(from_attributes=True)


class StoreCategoryOut(BaseModel):
    id: int
    name: str
    name_ar: str | None
    products: list[StoreProductOut]


class StoreMenuOut(BaseModel):
    categories: list[StoreCategoryOut]


class StoreOrderCreate(BaseModel):
    items: list[OrderItemIn] = Field(..., min_length=1)
    customer_name: str | None = Field(None, max_length=100)
    whatsapp_country: GulfPhoneCountry = "BH"
    whatsapp_phone: str = Field(..., min_length=6, max_length=20)
    payment_method: Literal["cash", "card", "transfer"] = "transfer"
    notes: str | None = None

    @field_validator("whatsapp_phone")
    @classmethod
    def _strip_phone(cls, v: str) -> str:
        return (v or "").strip()


class StoreOrderCreatedOut(BaseModel):
    id: int
    status: str
    total_amount: Decimal
    created_at: datetime


class PublicOrderStatusOut(BaseModel):
    id: int
    status: str
    total_amount: Decimal
    created_at: datetime
    source: str

    model_config = ConfigDict(from_attributes=True)
