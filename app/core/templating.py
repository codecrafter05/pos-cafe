from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.core.database import SessionLocal
from app.core.paths import PROJECT_ROOT
from app.services import shop_settings_service

templates = Jinja2Templates(directory=str(PROJECT_ROOT / "views"))


def shop_public_dict() -> dict:
    db = SessionLocal()
    try:
        row = shop_settings_service.get_settings(db)
        phone = (row.phone_number or "").strip() or None
        return {
            "cafe_name": shop_settings_service.display_cafe_name(row),
            "phone_number": phone,
            "logo_url": row.logo_url or None,
            "payment_qr_url": row.payment_qr_url or None,
        }
    finally:
        db.close()


def render(request: Request, name: str, context: dict | None = None):
    ctx = dict(context or {})
    ctx["request"] = request
    ctx["shop"] = shop_public_dict()
    return templates.TemplateResponse(name, ctx)
