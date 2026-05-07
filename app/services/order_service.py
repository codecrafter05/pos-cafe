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
from app.schemas.orders import OrderCreate, OrderModifierSnapshot
from app.services import inventory_service


def _extra_price_for_modifiers(
    db: Session, product_id: int, selected: list[OrderModifierSnapshot]
) -> Decimal:
    if not selected:
        return Decimal("0")
    existing: dict[tuple[str, str], Decimal] = {
        (m.group_name, m.option_name): m.extra_price
        for m in db.query(ProductModifier).filter(ProductModifier.product_id == product_id).all()
    }
    extras = Decimal("0")
    for mod in selected:
        key = (mod.group_name, mod.option_name)
        if key not in existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid modifier {key[0]!r} / {key[1]!r} for this product",
            )
        extras += existing[key]
    return extras


def create_pos_order(db: Session, user: User, payload: OrderCreate) -> Order:
    order = Order(
        user_id=user.id,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        payment_method=payload.payment_method,
        source="pos",
        status="delivered",
        notes=payload.notes,
        total_amount=Decimal("0"),
        total_cost=Decimal("0"),
        profit=Decimal("0"),
    )
    db.add(order)
    db.flush()

    total_amount = Decimal("0")
    total_cost = Decimal("0")

    for line in payload.items:
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

        extras = _extra_price_for_modifiers(db, product.id, line.modifiers)
        unit_price = product.price + extras
        line_revenue = unit_price * line.quantity

        unit_cost = inventory_service.apply_sale_deduction_for_product(
            db,
            product_id=product.id,
            quantity=line.quantity,
            order_id=order.id,
        )
        line_cost = unit_cost * Decimal(line.quantity)

        snapshot = [m.model_dump(mode="json") for m in line.modifiers]
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=line.quantity,
                unit_price=unit_price,
                unit_cost=unit_cost,
                modifiers_snapshot=snapshot or None,
                notes=line.notes,
            )
        )
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
