from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.time import UtcDateTime

Period = Literal["today", "week", "month"]


class DashboardSummaryOut(BaseModel):
    revenue: Decimal
    orders_count: int
    avg_order_value: Decimal
    date_from: str
    date_to: str


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


class WasteProductOut(BaseModel):
    product_id: int
    name: str
    name_ar: str | None
    units: int
    lost_retail: Decimal


class WasteSummaryOut(BaseModel):
    items_count: int
    products_count: int
    lost_retail: Decimal
    products: list[WasteProductOut]
    date_from: str
    date_to: str


class ReportDayOut(BaseModel):
    date: str
    label: str
    revenue: Decimal
    orders: int


class ReportProductOut(BaseModel):
    product_id: int
    name: str
    name_ar: str | None
    units_sold: int
    revenue: Decimal


class ReportPaymentOut(BaseModel):
    payment_method: str
    label: str
    orders: int
    revenue: Decimal


class ReportSummaryOut(BaseModel):
    date_from: str
    date_to: str
    revenue: Decimal
    orders_count: int
    avg_order_value: Decimal
    by_day: list[ReportDayOut]
    by_product: list[ReportProductOut]
    by_payment: list[ReportPaymentOut] = []


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
    created_at: UtcDateTime

    model_config = ConfigDict(from_attributes=True)
