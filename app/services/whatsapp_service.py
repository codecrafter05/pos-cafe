"""WhatsApp notifications via Evolution API (optional — see README2 Phase 3)."""
from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request

from app.core.config import settings

logger = logging.getLogger(__name__)

# Store UI: Gulf → international prefix (digits only, no +)
GULF_DIAL_CODES: dict[str, str] = {
    "BH": "973",
    "SA": "966",
    "AE": "971",
    "KW": "965",
    "OM": "968",
    "QA": "974",
}


def compose_gulf_whatsapp(country_code: str, local_raw: str) -> str:
    """
    Build full WhatsApp number from selected Gulf country + local mobile.

    Local may be e.g. 37331306 or 037331306. If the value already includes the
    country prefix for the selected country, it is returned as-is.
    """
    dial = GULF_DIAL_CODES.get(country_code, GULF_DIAL_CODES["BH"])
    d = re.sub(r"\D", "", (local_raw or "").strip())
    if not d:
        return ""
    if d.startswith("00"):
        d = d[2:]
    if d.startswith(dial):
        return d
    if d.startswith("0"):
        d = d[1:]
    return dial + d


def normalize_whatsapp_number(raw: str) -> str:
    """
    Digits only for Evolution. Supports:
    - Full international already stored (>= 10 digits): returned cleaned
    - Legacy rows: 8-digit local only → prepend default country from settings (Bahrain)
    """
    d = re.sub(r"\D", "", (raw or "").strip())
    if not d:
        return ""
    if d.startswith("00"):
        d = d[2:]
    if len(d) >= 10:
        return d
    cc = re.sub(r"\D", "", (settings.whatsapp_default_country_code or "").strip())
    nlen = int(settings.whatsapp_national_number_length or 8)
    if cc and len(d) == nlen and not d.startswith(cc):
        return cc + d
    return d


def is_configured() -> bool:
    return bool(
        settings.evolution_base_url
        and settings.evolution_api_key
        and settings.evolution_instance_name
    )


def send_text(phone_digits: str, text: str) -> bool:
    """
    POST /message/sendText/{instance}. Returns True if HTTP 2xx and API reports success when present.
    If Evolution is not configured, logs and returns False (no exception).
    """
    if not is_configured():
        logger.info("WhatsApp skipped: Evolution API not configured in .env")
        return False
    phone = normalize_whatsapp_number(phone_digits)
    if len(phone) < 10:
        logger.warning(
            "WhatsApp skipped: phone too short after normalize (got %r from %r)",
            phone,
            phone_digits,
        )
        return False

    base = (settings.evolution_base_url or "").rstrip("/")
    instance = settings.evolution_instance_name
    url = f"{base}/message/sendText/{instance}"
    payload = json.dumps({"number": phone, "text": text}).encode("utf-8")
    # urllib uses User-Agent: Python-urllib/... by default — Cloudflare often returns 403 (e.g. error 1010).
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "apikey": settings.evolution_api_key or "",
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if resp.status >= 400:
                logger.error("WhatsApp HTTP %s: %s", resp.status, body[:500])
                return False
            try:
                data = json.loads(body) if body else {}
                if isinstance(data, dict) and data.get("error") is True:
                    logger.error("WhatsApp API error: %s", data)
                    return False
            except json.JSONDecodeError:
                pass
            logger.info("WhatsApp send OK to %s", phone)
            return True
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:1200]
        except Exception:
            pass
        logger.error(
            "WhatsApp HTTPError %s on POST %s — body: %s",
            e.code,
            url,
            err_body or "(empty)",
        )
        if e.code == 403 and "1010" in err_body:
            logger.error(
                "Hint: HTTP 1010 is often Cloudflare blocking the request. "
                "Use the Evolution server direct URL (not behind Cloudflare), or allow your server IP."
            )
        return False
    except urllib.error.URLError:
        logger.exception("WhatsApp URLError")
        return False


def notify_order_received(phone: str, order_id: int) -> bool:
    normalized = normalize_whatsapp_number(phone)
    ok = send_text(
        phone,
        f"Your order was received ✓\nOrder no.: #{order_id}\nWe'll notify you when it's ready ☕",
    )
    if not ok:
        logger.warning(
            "Order #%s: WhatsApp confirmation not sent (check .env Evolution + phone %r → %r)",
            order_id,
            phone,
            normalized,
        )
    return ok


def notify_order_ready(phone: str, order_id: int) -> bool:
    normalized = normalize_whatsapp_number(phone)
    ok = send_text(
        phone,
        f"Your order is ready ☕\nOrder no.: #{order_id}\nThank you — see you soon!",
    )
    if not ok:
        logger.warning(
            "Order #%s: WhatsApp ready message not sent (check Evolution + phone %r → %r)",
            order_id,
            phone,
            normalized,
        )
    return ok
