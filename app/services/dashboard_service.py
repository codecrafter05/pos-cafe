from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.raw_material import RawMaterial

Period = Literal["today", "week", "month"]


def _period_start(period: Period, *, now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    if period == "today":
        return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    if period == "week":
        return now - timedelta(days=7)
    # month: calendar month start
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


def _period_end(*, now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now


@dataclass(frozen=True)
class SummaryRow:
    revenue: Decimal
    net_profit: Decimal
    orders_count: int
    avg_order_value: Decimal


def dashboard_summary(db: Session, *, period: Period) -> SummaryRow:
    start = _period_start(period)
    end = _period_end()
    q = db.query(
        func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
        func.coalesce(func.sum(Order.profit), 0).label("net_profit"),
        func.count().label("orders_count"),
        func.coalesce(func.avg(Order.total_amount), 0).label("avg_order_value"),
    ).filter(
        Order.created_at >= start,
        Order.created_at <= end,
        Order.status != "cancelled",
    )
    row = q.one()
    return SummaryRow(
        revenue=Decimal(str(row.revenue or 0)),
        net_profit=Decimal(str(row.net_profit or 0)),
        orders_count=int(row.orders_count or 0),
        avg_order_value=Decimal(str(row.avg_order_value or 0)),
    )


def sales_chart_last_days(db: Session, *, days: int = 7) -> list[dict]:
    end = _period_end()
    start_day = (end - timedelta(days=days - 1)).date()
    rows = (
        db.query(
            func.date(Order.created_at).label("d"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
        )
        .filter(
            Order.created_at >= datetime.combine(start_day, datetime.min.time()).replace(tzinfo=timezone.utc),
            Order.created_at <= end,
            Order.status != "cancelled",
        )
        .group_by(func.date(Order.created_at))
        .all()
    )
    by_date: dict[date, Decimal] = {}
    for r in rows:
        dk = r.d
        if isinstance(dk, datetime):
            dk = dk.date()
        if not isinstance(dk, date):
            continue
        by_date[dk] = Decimal(str(r.revenue or 0))
    out: list[dict] = []
    for i in range(days):
        d = start_day + timedelta(days=i)
        label = d.strftime("%a %d/%m")
        out.append({"date": d.isoformat(), "label": label, "revenue": by_date.get(d, Decimal("0"))})
    return out


def top_products(
    db: Session,
    *,
    period: Period,
    limit: int = 10,
) -> list[dict]:
    start = _period_start(period)
    end = _period_end()
    limit = max(1, min(limit, 50))
    sub = (
        db.query(
            OrderItem.product_id.label("product_id"),
            func.sum(OrderItem.quantity).label("units_sold"),
            func.coalesce(
                func.sum(OrderItem.unit_price * OrderItem.quantity),
                0,
            ).label("revenue"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.created_at >= start,
            Order.created_at <= end,
            Order.status != "cancelled",
        )
        .group_by(OrderItem.product_id)
        .subquery()
    )
    rows = (
        db.query(Product, sub.c.units_sold, sub.c.revenue)
        .join(sub, Product.id == sub.c.product_id)
        .order_by(sub.c.revenue.desc())
        .limit(limit)
        .all()
    )
    out: list[dict] = []
    for p, units, revenue in rows:
        out.append(
            {
                "product_id": p.id,
                "name": p.name,
                "name_ar": p.name_ar,
                "units_sold": int(units or 0),
                "revenue": Decimal(str(revenue or 0)),
            }
        )
    return out


def peak_hours(db: Session, *, period: Period) -> list[dict]:
    start = _period_start(period)
    end = _period_end()
    hour_expr = extract("hour", Order.created_at)
    rows = (
        db.query(
            hour_expr.label("hr"),
            func.count().label("cnt"),
        )
        .filter(
            Order.created_at >= start,
            Order.created_at <= end,
            Order.status != "cancelled",
        )
        .group_by(hour_expr)
        .order_by(hour_expr)
        .all()
    )
    counts = {int(r.hr): int(r.cnt) for r in rows}
    return [{"hour": h, "orders": counts.get(h, 0)} for h in range(24)]


def inventory_alerts(db: Session) -> list[RawMaterial]:
    return (
        db.query(RawMaterial)
        .filter(RawMaterial.current_stock <= RawMaterial.min_stock_alert)
        .order_by(RawMaterial.name)
        .all()
    )
