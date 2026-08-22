from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.inventory_movement import InventoryMovement
from app.models.modifier_recipe import ModifierRecipe
from app.models.product_modifier import ProductModifier
from app.models.product_recipe import ProductRecipe
from app.models.purchase import Purchase
from app.models.raw_material import RawMaterial


def record_movement(
    db: Session,
    *,
    raw_material_id: int,
    movement_type: str,
    quantity: Decimal,
    order_id: int | None = None,
    order_item_id: int | None = None,
    notes: str | None = None,
) -> InventoryMovement:
    movement = InventoryMovement(
        raw_material_id=raw_material_id,
        movement_type=movement_type,
        quantity=quantity,
        order_id=order_id,
        order_item_id=order_item_id,
        notes=notes,
    )
    db.add(movement)
    return movement


def adjust_raw_material_stock(
    db: Session,
    *,
    raw_material_id: int,
    quantity_delta: Decimal,
    movement_type: str = "manual_adjustment",
    order_id: int | None = None,
    order_item_id: int | None = None,
    notes: str | None = None,
) -> RawMaterial:
    rm = (
        db.query(RawMaterial)
        .filter(RawMaterial.id == raw_material_id)
        .with_for_update()
        .first()
    )
    if rm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Raw material not found")
    new_level = rm.current_stock + quantity_delta
    if new_level < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adjustment would result in negative stock",
        )
    rm.current_stock = new_level
    record_movement(
        db,
        raw_material_id=raw_material_id,
        movement_type=movement_type,
        quantity=quantity_delta,
        order_id=order_id,
        order_item_id=order_item_id,
        notes=notes,
    )
    return rm


def _assert_recipe_lines_stock(
    db: Session,
    lines,
    quantity: int,
    reserved: dict[int, Decimal],
) -> Decimal:
    unit_cost = Decimal("0")
    for line in lines:
        rm = (
            db.query(RawMaterial)
            .filter(RawMaterial.id == line.raw_material_id)
            .with_for_update()
            .first()
        )
        if rm is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recipe references missing raw material id {line.raw_material_id}",
            )
        qty_needed = line.quantity_used * Decimal(quantity)
        already = reserved.get(rm.id, Decimal("0"))
        required = already + qty_needed
        if rm.current_stock < required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient stock for “{rm.name}”: need {required} {rm.unit}, "
                    f"have {rm.current_stock}"
                ),
            )
        reserved[rm.id] = required
        unit_cost += line.quantity_used * rm.cost_per_unit
    return unit_cost


def _deduct_recipe_lines(
    db: Session,
    lines,
    quantity: int,
    order_id: int,
    order_item_id: int | None,
    notes: str,
) -> Decimal:
    unit_cost = Decimal("0")
    for line in lines:
        rm = (
            db.query(RawMaterial)
            .filter(RawMaterial.id == line.raw_material_id)
            .with_for_update()
            .first()
        )
        if rm is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recipe references missing raw material id {line.raw_material_id}",
            )
        qty_needed = line.quantity_used * Decimal(quantity)
        unit_cost += line.quantity_used * rm.cost_per_unit
        if rm.current_stock < qty_needed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient stock for “{rm.name}”: need {qty_needed} {rm.unit}, "
                    f"have {rm.current_stock}"
                ),
            )
        rm.current_stock -= qty_needed
        record_movement(
            db,
            raw_material_id=rm.id,
            movement_type="sale_deduction",
            quantity=-qty_needed,
            order_id=order_id,
            order_item_id=order_item_id,
            notes=notes,
        )
    return unit_cost


def assert_sufficient_stock_for_product(
    db: Session,
    *,
    product_id: int,
    quantity: int,
    reserved: dict[int, Decimal],
) -> Decimal:
    """Confirm recipe materials exist and stock covers this line plus earlier
    lines in the same order. Does not deduct. ``reserved`` is mutated with
    additional raw-material quantities this line would consume.
    """
    lines = db.query(ProductRecipe).filter(ProductRecipe.product_id == product_id).all()
    return _assert_recipe_lines_stock(db, lines, quantity, reserved)


def assert_sufficient_stock_for_modifiers(
    db: Session,
    *,
    modifiers: list[ProductModifier],
    quantity: int,
    reserved: dict[int, Decimal],
) -> Decimal:
    """Same reservation rules as the base recipe, for optional modifier ingredients."""
    if not modifiers:
        return Decimal("0")
    ids = [m.id for m in modifiers]
    lines = db.query(ModifierRecipe).filter(ModifierRecipe.modifier_id.in_(ids)).all()
    return _assert_recipe_lines_stock(db, lines, quantity, reserved)


def apply_sale_deduction_for_product(
    db: Session,
    *,
    product_id: int,
    quantity: int,
    order_id: int,
    order_item_id: int | None = None,
) -> Decimal:
    """Deduct recipe materials for ``quantity`` units of ``product_id``. Returns unit cost (one unit)."""
    lines = db.query(ProductRecipe).filter(ProductRecipe.product_id == product_id).all()
    return _deduct_recipe_lines(
        db,
        lines,
        quantity,
        order_id,
        order_item_id,
        notes=f"Sale: product {product_id} × {quantity}",
    )


def apply_sale_deduction_for_modifiers(
    db: Session,
    *,
    modifiers: list[ProductModifier],
    quantity: int,
    order_id: int,
    order_item_id: int | None = None,
) -> Decimal:
    """Deduct optional modifier ingredients. No-op when none are linked. Returns extra unit cost."""
    extra_cost = Decimal("0")
    for mod in modifiers:
        lines = db.query(ModifierRecipe).filter(ModifierRecipe.modifier_id == mod.id).all()
        extra_cost += _deduct_recipe_lines(
            db,
            lines,
            quantity,
            order_id,
            order_item_id,
            notes=f"Sale: modifier {mod.id} ({mod.group_name}/{mod.option_name}) × {quantity}",
        )
    return extra_cost


def reverse_sale_deductions_for_item(db: Session, *, item) -> None:
    """Restore stock for one cancelled line. No-op for waste. Idempotent per item."""
    from app.models.order_item import OrderItem

    if not isinstance(item, OrderItem):
        return
    if (item.line_status or "sold") == "wasted":
        return
    order_id = item.order_id
    tag = f"item #{item.id}"
    already = (
        db.query(InventoryMovement.id)
        .filter(
            InventoryMovement.order_id == order_id,
            InventoryMovement.movement_type == "cancellation_reversal",
            InventoryMovement.notes.contains(tag),
        )
        .first()
    )
    if already is not None:
        return

    linked = (
        db.query(InventoryMovement)
        .filter(
            InventoryMovement.order_id == order_id,
            InventoryMovement.movement_type == "sale_deduction",
            InventoryMovement.order_item_id == item.id,
        )
        .all()
    )
    if linked:
        deductions = linked
    else:
        expected_notes = f"Sale: product {item.product_id} × {item.quantity}"
        deductions = (
            db.query(InventoryMovement)
            .filter(
                InventoryMovement.order_id == order_id,
                InventoryMovement.movement_type == "sale_deduction",
                InventoryMovement.order_item_id.is_(None),
                InventoryMovement.notes == expected_notes,
            )
            .all()
        )

    for mov in deductions:
        restore_qty = -mov.quantity
        if restore_qty == 0:
            continue
        adjust_raw_material_stock(
            db,
            raw_material_id=mov.raw_material_id,
            quantity_delta=restore_qty,
            movement_type="cancellation_reversal",
            order_id=order_id,
            order_item_id=item.id,
            notes=f"Cancellation of order #{order_id} {tag} (reverses movement #{mov.id})",
        )


def reverse_sale_deductions_for_order(db: Session, *, order_id: int) -> None:
    """Restore stock for a cancelled order.

    Reverses original ``sale_deduction`` movements for lines that are still sold.
    Wasted lines are left deducted (food was prepared). Already-cancelled lines
    are skipped. Idempotent per line.
    """
    from app.models.order_item import OrderItem

    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    if items:
        for item in items:
            status = item.line_status or "sold"
            if status in ("wasted", "cancelled"):
                continue
            reverse_sale_deductions_for_item(db, item=item)
            item.line_status = "cancelled"
        return

    already = (
        db.query(InventoryMovement.id)
        .filter(
            InventoryMovement.order_id == order_id,
            InventoryMovement.movement_type == "cancellation_reversal",
        )
        .first()
    )
    if already is not None:
        return

    deductions = (
        db.query(InventoryMovement)
        .filter(
            InventoryMovement.order_id == order_id,
            InventoryMovement.movement_type == "sale_deduction",
        )
        .all()
    )
    for mov in deductions:
        restore_qty = -mov.quantity
        if restore_qty == 0:
            continue
        adjust_raw_material_stock(
            db,
            raw_material_id=mov.raw_material_id,
            quantity_delta=restore_qty,
            movement_type="cancellation_reversal",
            order_id=order_id,
            notes=f"Cancellation of order #{order_id} (reverses movement #{mov.id})",
        )


def register_purchase(
    db: Session,
    *,
    user_id: int,
    raw_material_id: int,
    quantity: Decimal,
    unit_cost: Decimal,
    notes: str | None = None,
) -> Purchase:
    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Purchase quantity must be positive",
        )
    if unit_cost < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unit cost cannot be negative",
        )
    total_cost = quantity * unit_cost
    note = notes or None
    movement_note = note or f"Purchase {quantity} @ {unit_cost}"
    rm = adjust_raw_material_stock(
        db,
        raw_material_id=raw_material_id,
        quantity_delta=quantity,
        movement_type="purchase",
        notes=movement_note,
    )
    rm.cost_per_unit = unit_cost

    purchase = Purchase(
        raw_material_id=raw_material_id,
        user_id=user_id,
        quantity=quantity,
        unit_cost=unit_cost,
        total_cost=total_cost,
        notes=note,
    )
    db.add(purchase)
    db.flush()

    from app.services import order_service

    product_ids = (
        db.query(ProductRecipe.product_id)
        .filter(ProductRecipe.raw_material_id == raw_material_id)
        .distinct()
        .all()
    )
    for (pid,) in product_ids:
        order_service.recompute_product_cost_price(db, pid)

    return purchase


def delete_purchase_record(db: Session, *, purchase_id: int) -> None:
    pur = db.get(Purchase, purchase_id)
    if pur is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase not found",
        )
    adjust_raw_material_stock(
        db,
        raw_material_id=pur.raw_material_id,
        quantity_delta=-pur.quantity,
        movement_type="manual_adjustment",
        notes=f"Reversal: deleted purchase #{pur.id}",
    )
    db.delete(pur)
