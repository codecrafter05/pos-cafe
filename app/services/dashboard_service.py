from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy import extract, func, text
from sqlalchemy.orm import Session

from app.core.payments import payment_label
from app.core.time import (
    as_bahrain,
    bahrain_range_utc,
    period_bounds_utc,
    period_chart_dates,
)
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.raw_material import RawMaterial

Period = Literal["today", "week", "month"]


@dataclass(frozen=True)
class SummaryRow:
    revenue: Decimal
    net_profit: Decimal
    orders_count: int
    avg_order_value: Decimal
    total_cost: Decimal = Decimal("0")


def _summary_between(db: Session, start: datetime, end: datetime) -> SummaryRow:
    q = db.query(
        func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
        func.coalesce(func.sum(Order.total_cost), 0).label("total_cost"),
        func.coalesce(func.sum(Order.profit), 0).label("net_profit"),
        func.count().label("orders_count"),
        func.coalesce(func.avg(Order.total_amount), 0).label("avg_order_value"),
    ).filter(
        Order.created_at >= start,
        Order.created_at < end,
        Order.status != "cancelled",
    )
    row = q.one()
    return SummaryRow(
        revenue=Decimal(str(row.revenue or 0)),
        total_cost=Decimal(str(row.total_cost or 0)),
        net_profit=Decimal(str(row.net_profit or 0)),
        orders_count=int(row.orders_count or 0),
        avg_order_value=Decimal(str(row.avg_order_value or 0)),
    )


def dashboard_summary(db: Session, *, period: Period) -> SummaryRow:
    start, end = period_bounds_utc(period)
    return _summary_between(db, start, end)


def sales_chart_for_dates(db: Session, *, date_from: date, date_to: date) -> list[dict]:
    start, end = bahrain_range_utc(date_from, date_to)
    rows = (
        db.query(Order.created_at, Order.total_amount, Order.total_cost, Order.profit)
        .filter(
            Order.created_at >= start,
            Order.created_at < end,
            Order.status != "cancelled",
        )
        .all()
    )
    by_date: dict[date, dict[str, Decimal | int]] = {}
    d = date_from
    while d <= date_to:
        by_date[d] = {
            "revenue": Decimal("0"),
            "cost": Decimal("0"),
            "profit": Decimal("0"),
            "orders": 0,
        }
        d += timedelta(days=1)
    for created_at, amount, cost, profit in rows:
        if created_at is None:
            continue
        dk = as_bahrain(created_at).date()
        bucket = by_date.get(dk)
        if bucket is None:
            continue
        bucket["revenue"] += Decimal(str(amount or 0))
        bucket["cost"] += Decimal(str(cost or 0))
        bucket["profit"] += Decimal(str(profit or 0))
        bucket["orders"] = int(bucket["orders"]) + 1
    out: list[dict] = []
    d = date_from
    while d <= date_to:
        b = by_date[d]
        out.append(
            {
                "date": d.isoformat(),
                "label": d.strftime("%a %d/%m"),
                "revenue": b["revenue"],
                "cost": b["cost"],
                "profit": b["profit"],
                "orders": int(b["orders"]),
            }
        )
        d += timedelta(days=1)
    return out


def sales_chart_for_period(db: Session, *, period: Period) -> list[dict]:
    date_from, date_to = period_chart_dates(period)
    return sales_chart_for_dates(db, date_from=date_from, date_to=date_to)


def sales_chart_last_days(db: Session, *, days: int = 7) -> list[dict]:
    date_from, date_to = period_chart_dates("week")
    return sales_chart_for_dates(db, date_from=date_from, date_to=date_to)


def _products_between(
    db: Session,
    start: datetime,
    end: datetime,
    *,
    limit: int | None = None,
) -> list[dict]:
    sub = (
        db.query(
            OrderItem.product_id.label("product_id"),
            func.sum(OrderItem.quantity).label("units_sold"),
            func.coalesce(
                func.sum(OrderItem.unit_price * OrderItem.quantity),
                0,
            ).label("revenue"),
            func.coalesce(
                func.sum(OrderItem.unit_cost * OrderItem.quantity),
                0,
            ).label("cost"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.created_at >= start,
            Order.created_at < end,
            Order.status != "cancelled",
        )
        .group_by(OrderItem.product_id)
        .subquery()
    )
    q = (
        db.query(Product, sub.c.units_sold, sub.c.revenue, sub.c.cost)
        .join(sub, Product.id == sub.c.product_id)
        .order_by(sub.c.revenue.desc())
    )
    if limit is not None:
        q = q.limit(max(1, min(limit, 50)))
    rows = q.all()
    out: list[dict] = []
    for p, units, revenue, cost in rows:
        rev = Decimal(str(revenue or 0))
        cst = Decimal(str(cost or 0))
        out.append(
            {
                "product_id": p.id,
                "name": p.name,
                "name_ar": p.name_ar,
                "units_sold": int(units or 0),
                "revenue": rev,
                "cost": cst,
                "profit": rev - cst,
            }
        )
    return out


def top_products(
    db: Session,
    *,
    period: Period,
    limit: int = 10,
) -> list[dict]:
    start, end = period_bounds_utc(period)
    return _products_between(db, start, end, limit=limit)


def peak_hours(db: Session, *, period: Period) -> list[dict]:
    start, end = period_bounds_utc(period)
    hour_expr = extract("hour", func.date_add(Order.created_at, text("INTERVAL 3 HOUR")))
    rows = (
        db.query(
            hour_expr.label("hr"),
            func.count().label("cnt"),
        )
        .filter(
            Order.created_at >= start,
            Order.created_at < end,
            Order.status != "cancelled",
        )
        .group_by(hour_expr)
        .order_by(hour_expr)
        .all()
    )
    counts = {int(r.hr): int(r.cnt) for r in rows if r.hr is not None}
    return [{"hour": h, "orders": counts.get(h, 0)} for h in range(24)]


def inventory_alerts(db: Session) -> list[RawMaterial]:
    return (
        db.query(RawMaterial)
        .filter(RawMaterial.current_stock <= RawMaterial.min_stock_alert)
        .order_by(RawMaterial.name)
        .all()
    )


def _payments_between(db: Session, start: datetime, end: datetime) -> list[dict]:
    """Revenue split by how the customer paid, biggest earner first."""
    rows = (
        db.query(
            Order.payment_method.label("payment_method"),
            func.count().label("orders"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.coalesce(func.sum(Order.profit), 0).label("profit"),
        )
        .filter(
            Order.created_at >= start,
            Order.created_at < end,
            Order.status != "cancelled",
        )
        .group_by(Order.payment_method)
        .all()
    )
    out = [
        {
            "payment_method": row.payment_method or "",
            "label": payment_label(row.payment_method),
            "orders": int(row.orders or 0),
            "revenue": Decimal(str(row.revenue or 0)),
            "profit": Decimal(str(row.profit or 0)),
        }
        for row in rows
    ]
    out.sort(key=lambda r: r["revenue"], reverse=True)
    return out


def report_for_range(db: Session, *, date_from: date, date_to: date) -> dict:
    start, end = bahrain_range_utc(date_from, date_to)
    summary = _summary_between(db, start, end)
    by_day = sales_chart_for_dates(db, date_from=date_from, date_to=date_to)
    by_product = _products_between(db, start, end, limit=None)
    by_payment = _payments_between(db, start, end)
    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "revenue": summary.revenue,
        "total_cost": summary.total_cost,
        "net_profit": summary.net_profit,
        "orders_count": summary.orders_count,
        "avg_order_value": summary.avg_order_value,
        "by_day": by_day,
        "by_product": by_product,
        "by_payment": by_payment,
    }
