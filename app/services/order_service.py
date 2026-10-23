from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.product_modifier import ProductModifier
from app.models.user import User
from app.schemas.orders import OrderCreate, OrderItemIn, OrderModifierSnapshot


def get_or_create_online_store_user(db: Session) -> User:
    """Implicit staff account for web orders (appears in history)."""
    u = db.query(User).filter(User.username == "online_store").first()
    if u is not None:
        return u
    from app.core.config import settings
    from app.core.security import hash_password

    u = User(
        name="Online store",
        username="online_store",
        password_hash=hash_password(f"!no-login-{settings.SECRET_KEY[:24]}"),
        role="manager",
        is_active=True,
    )
    db.add(u)
    db.flush()
    return u


def _resolve_selected_modifiers(
    db: Session, product_id: int, selected: list[OrderModifierSnapshot]
) -> tuple[list[ProductModifier], Decimal]:
    """Resolve selected options by (group_name, option_name); price from server."""
    if not selected:
        return [], Decimal("0")
    existing: dict[tuple[str, str], ProductModifier] = {
        (m.group_name, m.option_name): m
        for m in db.query(ProductModifier).filter(ProductModifier.product_id == product_id).all()
    }
    resolved: list[ProductModifier] = []
    extras = Decimal("0")
    for snap in selected:
        key = (snap.group_name, snap.option_name)
        if key not in existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid modifier {key[0]!r} / {key[1]!r} for this product",
            )
        resolved.append(existing[key])
        extras += existing[key].extra_price
    return resolved, extras


def _create_order_from_items(
    db: Session,
    *,
    user_id: int,
    source: str,
    order_status: str,
    customer_name: str | None,
    customer_phone: str | None,
    payment_method: str,
    notes: str | None,
    items: list[OrderItemIn],
    customer_car_plate: str | None = None,
    client_uuid: str | None = None,
    device_id: str | None = None,
    created_at: datetime | None = None,
) -> Order:
    prepared: list[tuple[OrderItemIn, Product, Decimal]] = []

    for line in items:
        product = (
            db.query(Product)
            .filter(Product.id == line.product_id, Product.is_active.is_(True))
            .first()
        )
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {line.product_id} not available",
            )

        _, extras = _resolve_selected_modifiers(db, product.id, line.modifiers)
        prepared.append((line, product, extras))

    order = Order(
        user_id=user_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_car_plate=customer_car_plate,
        payment_method=payment_method,
        source=source,
        status=order_status,
        notes=notes,
        total_amount=Decimal("0"),
        total_cost=Decimal("0"),
        profit=Decimal("0"),
        client_uuid=client_uuid,
        device_id=device_id,
    )
    if created_at is not None:
        order.created_at = created_at
    db.add(order)
    db.flush()

    total_amount = Decimal("0")

    for line, product, extras in prepared:
        unit_price = product.price + extras
        line_revenue = unit_price * line.quantity

        snapshot = [m.model_dump(mode="json") for m in line.modifiers]
        item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=line.quantity,
            unit_price=unit_price,
            unit_cost=Decimal("0"),
            modifiers_snapshot=snapshot or None,
            notes=line.notes,
            line_status="sold",
        )
        db.add(item)
        total_amount += line_revenue

    order.total_amount = total_amount
    order.total_cost = Decimal("0")
    order.profit = total_amount
    db.flush()

    return (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == order.id)
        .one()
    )


def create_pos_order(db: Session, user: User, payload: OrderCreate) -> Order:
    return _create_order_from_items(
        db,
        user_id=user.id,
        source="pos",
        order_status="delivered",
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        customer_car_plate=payload.customer_car_plate,
        payment_method=payload.payment_method,
        notes=payload.notes,
        items=payload.items,
    )


def create_device_order(
    db: Session,
    user: User,
    payload: OrderCreate,
    *,
    client_uuid: str,
    device_id: str | None = None,
    created_at: datetime | None = None,
) -> Order:
    """In-person sale from a Sunmi companion device."""
    return _create_order_from_items(
        db,
        user_id=user.id,
        source="sunmi_device",
        order_status="delivered",
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        customer_car_plate=payload.customer_car_plate,
        payment_method=payload.payment_method,
        notes=payload.notes,
        items=payload.items,
        client_uuid=client_uuid,
        device_id=device_id,
        created_at=created_at,
    )


def create_online_order(
    db: Session,
    *,
    customer_name: str | None,
    customer_phone: str,
    payment_method: str,
    notes: str | None,
    items: list[OrderItemIn],
) -> Order:
    actor = get_or_create_online_store_user(db)
    return _create_order_from_items(
        db,
        user_id=actor.id,
        source="online",
        order_status="pending",
        customer_name=customer_name,
        customer_phone=customer_phone,
        payment_method=payment_method,
        notes=notes,
        items=items,
    )


def recompute_order_totals(db: Session, order: Order) -> Order:
    """Sold lines count as revenue; wasted lines drop revenue; cancelled drop both."""
    total_amount = Decimal("0")
    sold = 0
    wasted = 0
    cancelled = 0
    for item in order.items:
        status = item.line_status or "sold"
        line_price = item.unit_price * Decimal(item.quantity)
        if status == "cancelled":
            cancelled += 1
            continue
        if status == "wasted":
            wasted += 1
            continue
        sold += 1
        total_amount += line_price
    order.total_amount = total_amount
    order.total_cost = Decimal("0")
    order.profit = total_amount
    if sold == 0 and wasted == 0 and cancelled > 0:
        order.status = "cancelled"
    db.flush()
    return order


def set_order_item_line_status(db: Session, *, order: Order, item: OrderItem, new_status: str) -> Order:
    current = item.line_status or "sold"
    if new_status not in ("cancelled", "wasted"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Line status must be cancelled or wasted",
        )
    if current == new_status:
        return order
    if current in ("cancelled", "wasted"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This item is already {current}",
        )
    item.line_status = new_status
    db.flush()
    return recompute_order_totals(db, order)


def delete_cancelled_order(db: Session, order: Order) -> None:
    """Hard-delete a cancelled order and its child rows."""
    if (order.status or "") != "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cancel this order first, then you can delete it.",
        )
    order_id = order.id
    db.query(OrderItem).filter(OrderItem.order_id == order_id).delete(synchronize_session=False)
    db.query(Order).filter(Order.id == order_id).delete(synchronize_session=False)
    db.flush()
