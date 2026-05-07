from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User
from app.schemas.dashboard import OrderStatusUpdate
from app.schemas.orders import OrderCreate, OrderItemOut, OrderOut
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])

_staff = require_roles("owner", "manager", "cashier")


def _order_to_out(db: Session, order: Order) -> OrderOut:
    staff = db.get(User, order.user_id)
    items_out: list[OrderItemOut] = []
    for it in order.items:
        pname = it.product.name if getattr(it, "product", None) else None
        io = OrderItemOut.model_validate(it)
        items_out.append(io.model_copy(update={"product_name": pname}))
    base = OrderOut.model_validate(order)
    return base.model_copy(
        update={
            "items": items_out,
            "staff_username": staff.username if staff else None,
        }
    )


@router.get("", response_model=list[OrderOut])
def list_orders(
    db: Session = Depends(get_db),
    user: User = Depends(_staff),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
):
    q = db.query(Order).options(joinedload(Order.items))
    if user.role == "cashier":
        q = q.filter(Order.user_id == user.id)
    if date_from is not None:
        start = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        q = q.filter(Order.created_at >= start)
    if date_to is not None:
        end = datetime.combine(date_to, time(23, 59, 59, 999999), tzinfo=timezone.utc)
        q = q.filter(Order.created_at <= end)
    if status_filter:
        q = q.filter(Order.status == status_filter)
    return q.order_by(Order.created_at.desc()).limit(500).all()


@router.post("", response_model=OrderOut)
def create_order(
    body: OrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_staff),
):
    try:
        order = order_service.create_pos_order(db, user, body)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return (
        db.query(Order).options(joinedload(Order.items)).filter(Order.id == order.id).one()
    )


@router.put("/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    body: OrderStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(_staff),
):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if user.role == "cashier" and order.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    order.status = body.status
    db.commit()
    return (
        db.query(Order).options(joinedload(Order.items)).filter(Order.id == order.id).one()
    )


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(_staff),
):
    order = (
        db.query(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .filter(Order.id == order_id)
        .first()
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if user.role == "cashier" and order.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return _order_to_out(db, order)
