from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.payments import InPersonPaymentMethod
from app.schemas.orders import OrderItemIn


class SyncShopOut(BaseModel):
    cafe_name: str
    phone_number: str | None
    logo_url: str | None
    payment_qr_url: str | None = None


class SyncCategoryOut(BaseModel):
    id: int
    name: str
    name_ar: str | None
    sort_order: int

    model_config = ConfigDict(from_attributes=True)


class SyncModifierOut(BaseModel):
    id: int
    group_name: str
    option_name: str
    extra_price: Decimal

    model_config = ConfigDict(from_attributes=True)


class SyncProductOut(BaseModel):
    id: int
    category_id: int
    name: str
    name_ar: str | None
    price: Decimal
    description: str | None
    image_url: str | None
    sort_order: int
    modifiers: list[SyncModifierOut] = []

    model_config = ConfigDict(from_attributes=True)


class SyncCatalogOut(BaseModel):
    generated_at: datetime
    catalog_version: str
    shop: SyncShopOut
    categories: list[SyncCategoryOut]
    products: list[SyncProductOut]


class DeviceOrderIn(BaseModel):
    client_uuid: UUID
    device_id: str | None = Field(None, max_length=64)
    created_at: datetime | None = None
    items: list[OrderItemIn] = Field(..., min_length=1)
    customer_name: str | None = Field(None, max_length=100)
    customer_phone: str | None = Field(None, max_length=20)
    customer_car_plate: str | None = Field(None, max_length=40)
    payment_method: InPersonPaymentMethod
    notes: str | None = None


class SyncOrdersRequest(BaseModel):
    device_id: str | None = Field(None, max_length=64)
    orders: list[DeviceOrderIn] = Field(..., min_length=1)


class SyncOrderResult(BaseModel):
    client_uuid: UUID
    status: Literal["success", "failed"]
    server_order_id: int | None = None
    reason: str | None = None


class SyncOrdersResponse(BaseModel):
    results: list[SyncOrderResult]
