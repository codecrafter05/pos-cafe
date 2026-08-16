from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.shop_settings import DEFAULT_CAFE_NAME, SETTINGS_ROW_ID, ShopSettings


def get_settings(db: Session) -> ShopSettings:
    row = db.get(ShopSettings, SETTINGS_ROW_ID)
    if row is not None:
        return row
    now = datetime.now(timezone.utc)
    row = ShopSettings(
        id=SETTINGS_ROW_ID,
        cafe_name=DEFAULT_CAFE_NAME,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def display_cafe_name(row: ShopSettings) -> str:
    name = (row.cafe_name or "").strip()
    return name or DEFAULT_CAFE_NAME


def update_settings(
    db: Session,
    *,
    cafe_name: str,
    phone_number: str | None,
) -> ShopSettings:
    row = get_settings(db)
    name = (cafe_name or "").strip() or DEFAULT_CAFE_NAME
    if len(name) > 150:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cafe name must be 150 characters or fewer",
        )
    phone = (phone_number or "").strip() or None
    if phone and len(phone) > 40:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number must be 40 characters or fewer",
        )
    row.cafe_name = name
    row.phone_number = phone
    row.updated_at = datetime.now(timezone.utc)
    db.flush()
    return row


def set_image_url(db: Session, *, field: str, url: str | None) -> ShopSettings:
    if field not in ("logo_url", "payment_qr_url"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image field")
    row = get_settings(db)
    setattr(row, field, url)
    row.updated_at = datetime.now(timezone.utc)
    db.flush()
    return row
