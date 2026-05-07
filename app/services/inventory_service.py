from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.inventory_movement import InventoryMovement
from app.models.product_recipe import ProductRecipe
from app.models.raw_material import RawMaterial


def record_movement(
    db: Session,
    *,
    raw_material_id: int,
    movement_type: str,
    quantity: Decimal,
    order_id: int | None = None,
    notes: str | None = None,
) -> InventoryMovement:
    movement = InventoryMovement(
        raw_material_id=raw_material_id,
        movement_type=movement_type,
        quantity=quantity,
        order_id=order_id,
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
        notes=notes,
    )
    return rm


def apply_sale_deduction_for_product(
    db: Session,
    *,
    product_id: int,
    quantity: int,
    order_id: int,
) -> Decimal:
    """Deduct recipe materials for ``quantity`` units of ``product_id``. Returns unit cost (one unit)."""
    lines = db.query(ProductRecipe).filter(ProductRecipe.product_id == product_id).all()
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
            notes=f"Sale: product {product_id} × {quantity}",
        )
    return unit_cost
