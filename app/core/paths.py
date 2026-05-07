"""Single project paths (avoid drift between main.py and feature modules)."""

from pathlib import Path

# app/core/paths.py → repo root (parent of `app/`)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = PROJECT_ROOT / "static"
TEMPLATE_DIR = PROJECT_ROOT / "template"
PRODUCT_UPLOAD_DIR = STATIC_DIR / "uploads" / "products"
