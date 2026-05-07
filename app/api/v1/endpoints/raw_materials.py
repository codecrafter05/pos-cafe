from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.raw_material import RawMaterial
from app.models.user import User
from app.schemas.menu import ManualStockAdjustRequest, RawMaterialCreate, RawMaterialOut, RawMaterialUpdate
from app.services import inventory_service

router = APIRouter(prefix="/raw-materials", tags=["raw-materials"])

_staff = require_roles("owner", "manager", "cashier")
_writers = require_roles("owner", "manager")


@router.get("", response_model=list[RawMaterialOut])
def list_raw_materials(
    db: Session = Depends(get_db),
    _: User = Depends(_staff),
):
    return db.query(RawMaterial).order_by(RawMaterial.name).all()


@router.post("", response_model=RawMaterialOut)
def create_raw_material(
    body: RawMaterialCreate,
    db: Session = Depends(get_db),
    _: User = Depends(_writers),
):
    data = body.model_dump()
    opening = data.pop("current_stock")
    rm = RawMaterial(**data, current_stock=0)
    db.add(rm)
    db.flush()
    if opening != 0:
        inventory_service.adjust_raw_material_stock(
            db,
            raw_material_id=rm.id,
            quantity_delta=opening,
            notes="Opening balance",
        )
    db.commit()
    db.refresh(rm)
    return rm


@router.put("/{material_id}", response_model=RawMaterialOut)
def update_raw_material(
    material_id: int,
    body: RawMaterialUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(_writers),
):
    rm = db.get(RawMaterial, material_id)
    if rm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Raw material not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(rm, k, v)
    db.commit()
    db.refresh(rm)
    return rm


@router.post("/{material_id}/adjust", response_model=RawMaterialOut)
def adjust_stock(
    material_id: int,
    body: ManualStockAdjustRequest,
    db: Session = Depends(get_db),
    _: User = Depends(_writers),
):
    try:
        rm = inventory_service.adjust_raw_material_stock(
            db,
            raw_material_id=material_id,
            quantity_delta=body.quantity_delta,
            movement_type="manual_adjustment",
            notes=body.notes,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(rm)
    return rm


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_raw_material(
    material_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(_writers),
):
    rm = db.get(RawMaterial, material_id)
    if rm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Raw material not found")
    if rm.recipe_lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete material used in a product recipe.",
        )
    db.delete(rm)
    db.commit()
    return None
