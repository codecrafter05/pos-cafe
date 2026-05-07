from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Period = Literal["today", "week", "month"]


class DashboardSummaryOut(BaseModel):
    revenue: Decimal
    net_profit: Decimal
    orders_count: int
    avg_order_value: Decimal
    period: Period


class SalesChartPointOut(BaseModel):
    date: str
    label: str
    revenue: Decimal


class TopProductOut(BaseModel):
    product_id: int
    name: str
    name_ar: str | None
    units_sold: int
    revenue: Decimal


class PeakHourOut(BaseModel):
    hour: int
    orders: int


class InventoryAlertOut(BaseModel):
    id: int
    name: str
    unit: str
    current_stock: Decimal
    min_stock_alert: Decimal

    model_config = ConfigDict(from_attributes=True)


class PurchaseCreate(BaseModel):
    raw_material_id: int
    quantity: Decimal = Field(..., gt=0)
    unit_cost: Decimal = Field(..., ge=0)
    notes: str | None = None


class PurchaseOut(BaseModel):
    id: int
    raw_material_id: int
    user_id: int
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    purchased_at: datetime
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    status: Literal["pending", "preparing", "ready", "delivered", "cancelled"]


class UserAdminCreate(BaseModel):
    name: str = Field(..., max_length=100)
    username: str = Field(..., max_length=50)
    password: str = Field(..., min_length=4)
    role: Literal["owner", "manager", "cashier"]


class UserAdminUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    role: Literal["owner", "manager", "cashier"] | None = None
    is_active: bool | None = None
    password: str | None = Field(None, min_length=4)


class UserListOut(BaseModel):
    id: int
    name: str
    username: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
