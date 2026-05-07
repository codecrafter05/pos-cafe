from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.user import User
from app.schemas.dashboard import (
    DashboardSummaryOut,
    InventoryAlertOut,
    PeakHourOut,
    Period,
    SalesChartPointOut,
    TopProductOut,
)
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_admin = require_roles("owner", "manager")


@router.get("/summary", response_model=DashboardSummaryOut)
def summary(
    period: Annotated[Period, Query()] = "today",
    db: Session = Depends(get_db),
    _: User = Depends(_admin),
):
    s = dashboard_service.dashboard_summary(db, period=period)
    return DashboardSummaryOut(
        revenue=s.revenue,
        net_profit=s.net_profit,
        orders_count=s.orders_count,
        avg_order_value=s.avg_order_value,
        period=period,
    )


@router.get("/sales-chart", response_model=list[SalesChartPointOut])
def sales_chart(
    db: Session = Depends(get_db),
    _: User = Depends(_admin),
):
    rows = dashboard_service.sales_chart_last_days(db, days=7)
    return [SalesChartPointOut(**r) for r in rows]


@router.get("/top-products", response_model=list[TopProductOut])
def top_products(
    period: Annotated[Period, Query()] = "week",
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    db: Session = Depends(get_db),
    _: User = Depends(_admin),
):
    rows = dashboard_service.top_products(db, period=period, limit=limit)
    return [TopProductOut(**r) for r in rows]


@router.get("/peak-hours", response_model=list[PeakHourOut])
def peak_hours(
    period: Annotated[Period, Query()] = "today",
    db: Session = Depends(get_db),
    _: User = Depends(_admin),
):
    rows = dashboard_service.peak_hours(db, period=period)
    return [PeakHourOut(**r) for r in rows]


@router.get("/inventory-alerts", response_model=list[InventoryAlertOut])
def inventory_alerts(
    db: Session = Depends(get_db),
    _: User = Depends(_admin),
):
    items = dashboard_service.inventory_alerts(db)
    return [InventoryAlertOut.model_validate(x) for x in items]
