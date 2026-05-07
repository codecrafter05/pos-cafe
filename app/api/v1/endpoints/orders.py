from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.order import Order
from app.models.user import User
from app.schemas.orders import OrderCreate, OrderOut
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut)
def create_order(
    body: OrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("owner", "manager", "cashier")),
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


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("owner", "manager", "cashier")),
):
    order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == order_id)
        .first()
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if user.role == "cashier" and order.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return order
