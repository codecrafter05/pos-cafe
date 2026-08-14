from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.core.security import hash_password
from app.models.order import Order
from app.models.purchase import Purchase
from app.models.user import User
from app.schemas.dashboard import UserAdminCreate, UserAdminUpdate, UserListOut

router = APIRouter(prefix="/users", tags=["users"])

_owner = require_roles("owner")


@router.post("", response_model=UserListOut)
def create_user(
    body: UserAdminCreate,
    db: Session = Depends(get_db),
    _: User = Depends(_owner),
):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    user = User(
        name=body.name,
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserListOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(_owner),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.put("/{user_id}", response_model=UserListOut)
def update_user(
    user_id: int,
    body: UserAdminUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(_owner),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    data = body.model_dump(exclude_unset=True)
    pw = data.pop("password", None)
    if "username" in data:
        data.pop("username", None)
    for k, v in data.items():
        setattr(user, k, v)
    if pw:
        user.password_hash = hash_password(pw)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_owner),
):
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if db.query(Order).filter(Order.user_id == user_id).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a user who has orders. Deactivate instead.",
        )
    if db.query(Purchase).filter(Purchase.user_id == user_id).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a user linked to purchase records.",
        )
    db.delete(user)
    db.commit()
    return None
