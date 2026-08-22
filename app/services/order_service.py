from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.product_modifier import ProductModifier
from app.models.product_recipe import ProductRecipe
from app.models.raw_material import RawMaterial
from app.models.user import User
from app.schemas.orders import OrderCreate, OrderItemIn, OrderModifierSnapshot
from app.services import inventory_service


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
    prepared: list[tuple[OrderItemIn, Product, Decimal, list[ProductModifier]]] = []
    reserved: dict[int, Decimal] = {}

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

        has_recipe = (
            db.query(ProductRecipe.id)
            .filter(ProductRecipe.product_id == product.id)
            .first()
            is not None
        )
        if not has_recipe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot sell “{product.name}”: no recipe is configured. "
                    "Add ingredients on the product page before selling."
                ),
            )

        resolved_mods, extras = _resolve_selected_modifiers(db, product.id, line.modifiers)
        inventory_service.assert_sufficient_stock_for_product(
            db,
            product_id=product.id,
            quantity=line.quantity,
            reserved=reserved,
        )
        inventory_service.assert_sufficient_stock_for_modifiers(
            db,
            modifiers=resolved_mods,
            quantity=line.quantity,
            reserved=reserved,
        )
        prepared.append((line, product, extras, resolved_mods))

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
    total_cost = Decimal("0")

    for line, product, extras, resolved_mods in prepared:
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
        db.flush()

        unit_cost = inventory_service.apply_sale_deduction_for_product(
            db,
            product_id=product.id,
            quantity=line.quantity,
            order_id=order.id,
            order_item_id=item.id,
        )
        unit_cost += inventory_service.apply_sale_deduction_for_modifiers(
            db,
            modifiers=resolved_mods,
            quantity=line.quantity,
            order_id=order.id,
            order_item_id=item.id,
        )
        item.unit_cost = unit_cost
        line_cost = unit_cost * Decimal(line.quantity)

        total_amount += line_revenue
        total_cost += line_cost

    order.total_amount = total_amount
    order.total_cost = total_cost
    order.profit = total_amount - total_cost
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
    """In-person sale from a Sunmi companion device. Same stock/recipe path as POS."""
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


def recompute_product_cost_price(db: Session, product_id: int) -> None:
    product = db.get(Product, product_id)
    if product is None:
        return
    lines = db.query(ProductRecipe).filter(ProductRecipe.product_id == product_id).all()
    total = Decimal("0")
    for line in lines:
        rm = db.get(RawMaterial, line.raw_material_id)
        if rm is None:
            continue
        total += line.quantity_used * rm.cost_per_unit
    product.cost_price = total


def recompute_order_totals(db: Session, order: Order) -> Order:
    """Sold lines count as revenue; wasted lines keep cost (no restock); cancelled drop both."""
    total_amount = Decimal("0")
    total_cost = Decimal("0")
    sold = 0
    wasted = 0
    cancelled = 0
    for item in order.items:
        status = item.line_status or "sold"
        line_price = item.unit_price * Decimal(item.quantity)
        line_cost = item.unit_cost * Decimal(item.quantity)
        if status == "cancelled":
            cancelled += 1
            continue
        if status == "wasted":
            wasted += 1
            total_cost += line_cost
            continue
        sold += 1
        total_amount += line_price
        total_cost += line_cost
    order.total_amount = total_amount
    order.total_cost = total_cost
    order.profit = total_amount - total_cost
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
    if new_status == "cancelled":
        inventory_service.reverse_sale_deductions_for_item(db, item=item)
    item.line_status = new_status
    db.flush()
    return recompute_order_totals(db, order)
