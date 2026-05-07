from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.purchase import Purchase
from app.models.user import User
from app.schemas.dashboard import PurchaseCreate, PurchaseOut
from app.services import inventory_service

router = APIRouter(prefix="/purchases", tags=["purchases"])

_owners = require_roles("owner", "manager")


@router.post("", response_model=PurchaseOut)
def create_purchase(
    body: PurchaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_owners),
):
    try:
        purchase = inventory_service.register_purchase(
            db,
            user_id=user.id,
            raw_material_id=body.raw_material_id,
            quantity=body.quantity,
            unit_cost=body.unit_cost,
            notes=body.notes,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(purchase)
    return purchase


@router.get("", response_model=list[PurchaseOut])
def list_purchases(
    db: Session = Depends(get_db),
    _: User = Depends(_owners),
):
    return db.query(Purchase).order_by(Purchase.purchased_at.desc()).limit(500).all()


@router.delete("/{purchase_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase(
    purchase_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(_owners),
):
    try:
        inventory_service.delete_purchase_record(db, purchase_id=purchase_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return None
