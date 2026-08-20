from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserOut
from app.services import refresh_token_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _access_for(user: User, *, device: bool) -> tuple[str, int]:
    minutes = (
        settings.DEVICE_ACCESS_TOKEN_EXPIRE_MINUTES
        if device
        else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    token = create_access_token(
        subject=user.username,
        role=user.role,
        expires_minutes=minutes,
    )
    return token, minutes * 60


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    device = body.client == "device"
    access, expires_in = _access_for(user, device=device)
    refresh = None
    if device:
        refresh, _ = refresh_token_service.issue(db, user)
        db.commit()
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        new_refresh, _, user = refresh_token_service.rotate(db, body.refresh_token)
    except refresh_token_service.RefreshError as exc:
        db.commit()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    access, expires_in = _access_for(user, device=True)
    db.commit()
    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshRequest, db: Session = Depends(get_db)):
    refresh_token_service.revoke_plain(db, body.refresh_token)
    db.commit()
    return None


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
