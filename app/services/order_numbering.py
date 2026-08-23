"""Staff/customer-facing daily order numbers.

Internal `orders.id` stays the primary key for lookups, FKs, and cancel/delete.
The number humans see is computed at query time so it stays chronological by
`created_at` (sale time) within each Asia/Bahrain calendar day, and heals if
an order is later deleted. Nothing is stored — no increment column, no races.
"""

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.time import BAHRAIN_UTC_OFFSET_HOURS
from app.models.order import Order

# Naive UTC `created_at` → Bahrain calendar date. Equivalent to
# DATE(CONVERT_TZ(created_at, '+00:00', '+03:00')); Asia/Bahrain has no DST.
# Same INTERVAL 3 HOUR shift already used by the Reports/dashboard queries.
_BAHRAIN_DAY_SQL = text(f"INTERVAL {BAHRAIN_UTC_OFFSET_HOURS} HOUR")


def bahrain_created_date_expr():
    return func.date(func.date_add(Order.created_at, _BAHRAIN_DAY_SQL))


def daily_order_numbers_by_id(db: Session, order_ids: list[int]) -> dict[int, int]:
    """Map internal order id → 1-based rank for that order's Bahrain day.

    Ranking is over ALL orders of those days (not the filtered result set),
    ordered by `created_at` then `id` so late-syncing older sales still slot
    into the correct chronological position.
    """
    ids = list({int(i) for i in order_ids})
    if not ids:
        return {}

    day_expr = bahrain_created_date_expr()
    days = [
        row[0]
        for row in db.query(day_expr).filter(Order.id.in_(ids)).distinct().all()
        if row[0] is not None
    ]
    if not days:
        return {}

    ranked = func.row_number().over(
        partition_by=day_expr,
        order_by=(Order.created_at.asc(), Order.id.asc()),
    )
    rows = (
        db.query(Order.id, ranked.label("daily_order_number"))
        .filter(day_expr.in_(days))
        .all()
    )
    wanted = set(ids)
    return {int(oid): int(num) for oid, num in rows if int(oid) in wanted}


def daily_order_number_for(db: Session, order_id: int) -> int:
    found = daily_order_numbers_by_id(db, [order_id]).get(int(order_id))
    if found is None:
        raise ValueError(f"Order {order_id} has no daily_order_number")
    return found
