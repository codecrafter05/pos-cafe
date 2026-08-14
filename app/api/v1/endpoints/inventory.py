from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.raw_material import RawMaterial
from app.models.user import User
from app.schemas.menu import ManualStockAdjustRequest, RawMaterialOut
from app.services import inventory_service

router = APIRouter(prefix="/inventory", tags=["inventory"])

_viewers = require_roles("owner", "manager")
_writers = require_roles("owner", "manager")


@router.get("", response_model=list[RawMaterialOut])
def list_inventory(
    db: Session = Depends(get_db),
    _: User = Depends(_viewers),
):
    return db.query(RawMaterial).order_by(RawMaterial.name).all()


@router.post("/{material_id}/adjust", response_model=RawMaterialOut)
def adjust_inventory(
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
