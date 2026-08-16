import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.core.paths import SETTINGS_UPLOAD_DIR
from app.models.user import User
from app.schemas.settings import ShopSettingsOut, ShopSettingsUpdate
from app.services import shop_settings_service

router = APIRouter(prefix="/settings", tags=["settings"])

_owner = require_roles("owner")

_ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
_MAX_IMAGE_BYTES = 3 * 1024 * 1024
_MIN_IMAGE_BYTES = 32
_URL_PREFIX = "/static/uploads/settings/"


def _ensure_upload_dir() -> None:
    SETTINGS_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _safe_remove_uploaded_file(image_url: str | None) -> None:
    if not image_url or not image_url.startswith(_URL_PREFIX):
        return
    name = image_url.rstrip("/").split("/")[-1]
    if not name or ".." in name or "/" in name:
        return
    path = SETTINGS_UPLOAD_DIR / name
    try:
        if path.is_file() and path.resolve().parent == SETTINGS_UPLOAD_DIR.resolve():
            path.unlink()
    except OSError:
        pass


async def _save_settings_image(file: UploadFile, *, prefix: str) -> str:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_IMAGE_EXT:
        suffix = _MIME_TO_EXT.get((file.content_type or "").split(";")[0].strip().lower(), "")
    if suffix not in _ALLOWED_IMAGE_EXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image type. Use JPG, PNG, WebP, or GIF.",
        )
    raw = await file.read()
    if len(raw) < _MIN_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too small to be a valid image (min {_MIN_IMAGE_BYTES} bytes).",
        )
    if len(raw) > _MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image too large (max 3 MB).",
        )
    _ensure_upload_dir()
    fname = f"{prefix}_{uuid.uuid4().hex}{suffix}"
    dest = SETTINGS_UPLOAD_DIR / fname
    try:
        dest.write_bytes(raw)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save image to disk: {exc}",
        ) from exc
    return f"{_URL_PREFIX}{fname}"


@router.get("", response_model=ShopSettingsOut)
def get_settings(
    db: Session = Depends(get_db),
    _: User = Depends(_owner),
):
    return shop_settings_service.get_settings(db)


@router.put("", response_model=ShopSettingsOut)
def update_settings(
    body: ShopSettingsUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(_owner),
):
    row = shop_settings_service.update_settings(
        db,
        cafe_name=body.cafe_name,
        phone_number=body.phone_number,
    )
    db.commit()
    db.refresh(row)
    return row


@router.post("/logo", response_model=ShopSettingsOut)
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(_owner),
):
    row = shop_settings_service.get_settings(db)
    old_url = row.logo_url
    url = await _save_settings_image(file, prefix="logo")
    _safe_remove_uploaded_file(old_url)
    row = shop_settings_service.set_image_url(db, field="logo_url", url=url)
    db.commit()
    db.refresh(row)
    return row


@router.post("/payment-qr", response_model=ShopSettingsOut)
async def upload_payment_qr(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(_owner),
):
    row = shop_settings_service.get_settings(db)
    old_url = row.payment_qr_url
    url = await _save_settings_image(file, prefix="qr")
    _safe_remove_uploaded_file(old_url)
    row = shop_settings_service.set_image_url(db, field="payment_qr_url", url=url)
    db.commit()
    db.refresh(row)
    return row
