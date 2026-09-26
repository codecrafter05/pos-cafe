from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.core.database import SessionLocal
from app.core.paths import PROJECT_ROOT
from app.services import shop_settings_service

templates = Jinja2Templates(directory=str(PROJECT_ROOT / "views"))

# Public /store: set True to show Add buttons and Cart when online ordering launches.
STORE_ORDERING_ENABLED = False

# Public /store pages and /api/store. False suspends the customer store.
PUBLIC_STORE_ENABLED = True


def _asset_version() -> str:
    """Cache-busting stamp taken from the newest local JS/CSS file.

    Nginx serves /static without Cache-Control, so browsers fall back to
    heuristic freshness and keep an old bundle for hours. Appending this to the
    asset URLs means a deploy reaches returning users immediately instead of
    leaving them on a half-updated page. Computed once per process, which is
    exactly right: a deploy restarts the service.
    """
    newest = 0.0
    for path in (PROJECT_ROOT / "static").rglob("*"):
        if path.suffix in (".js", ".css") and path.is_file():
            newest = max(newest, path.stat().st_mtime)
    return str(int(newest))


templates.env.globals["asset_version"] = _asset_version()


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
    ctx.setdefault("store_ordering_enabled", STORE_ORDERING_ENABLED)
    return templates.TemplateResponse(name, ctx)
