from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.core.time import period_chart_dates
from app.models.user import User
from app.schemas.dashboard import (
    DashboardSummaryOut,
    InventoryAlertOut,
    PeakHourOut,
    Period,
    SalesChartPointOut,
    TopProductOut,
    WasteSummaryOut,
)
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_admin = require_roles("owner", "manager")


def _range(
    date_from: date | None,
    date_to: date | None,
    period: Period,
) -> tuple[date, date]:
    if date_from is None and date_to is None:
        return period_chart_dates(period)
    start = date_from or date_to
    end = date_to or date_from
    if start is None or end is None:
        return period_chart_dates(period)
    if end < start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_to must be on or after date_from",
        )
    if (end - start).days > 366:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Range cannot exceed 366 days",
        )
    return start, end


@router.get("/summary", response_model=DashboardSummaryOut)
def summary(
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    period: Annotated[Period, Query()] = "today",
    db: Session = Depends(get_db),
    _: User = Depends(_admin),
):
    start, end = _range(date_from, date_to, period)
    s = dashboard_service.dashboard_summary(db, date_from=start, date_to=end)
    return DashboardSummaryOut(
        revenue=s.revenue,
        net_profit=s.net_profit,
        orders_count=s.orders_count,
        avg_order_value=s.avg_order_value,
        date_from=start.isoformat(),
        date_to=end.isoformat(),
    )


@router.get("/sales-chart", response_model=list[SalesChartPointOut])
def sales_chart(
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    period: Annotated[Period, Query()] = "week",
    db: Session = Depends(get_db),
    _: User = Depends(_admin),
):
    start, end = _range(date_from, date_to, period)
    rows = dashboard_service.sales_chart_for_dates(db, date_from=start, date_to=end)
    return [
        SalesChartPointOut(date=r["date"], label=r["label"], revenue=r["revenue"])
        for r in rows
    ]


@router.get("/top-products", response_model=list[TopProductOut])
def top_products(
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    period: Annotated[Period, Query()] = "week",
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    db: Session = Depends(get_db),
    _: User = Depends(_admin),
):
    start, end = _range(date_from, date_to, period)
    rows = dashboard_service.top_products(db, date_from=start, date_to=end, limit=limit)
    return [TopProductOut(**r) for r in rows]


@router.get("/peak-hours", response_model=list[PeakHourOut])
def peak_hours(
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    period: Annotated[Period, Query()] = "today",
    db: Session = Depends(get_db),
    _: User = Depends(_admin),
):
    start, end = _range(date_from, date_to, period)
    rows = dashboard_service.peak_hours(db, date_from=start, date_to=end)
    return [PeakHourOut(**r) for r in rows]


@router.get("/waste", response_model=WasteSummaryOut)
def waste(
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    period: Annotated[Period, Query()] = "today",
    db: Session = Depends(get_db),
    _: User = Depends(_admin),
):
    start, end = _range(date_from, date_to, period)
    data = dashboard_service.waste_summary(db, date_from=start, date_to=end)
    return WasteSummaryOut(**data, date_from=start.isoformat(), date_to=end.isoformat())


@router.get("/inventory-alerts", response_model=list[InventoryAlertOut])
def inventory_alerts(
    db: Session = Depends(get_db),
    _: User = Depends(_admin),
):
    items = dashboard_service.inventory_alerts(db)
    return [InventoryAlertOut.model_validate(x) for x in items]
