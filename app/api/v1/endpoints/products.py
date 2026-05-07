import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_roles
from app.core.database import get_db
from app.core.paths import PRODUCT_UPLOAD_DIR
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.product_modifier import ProductModifier
from app.models.product_recipe import ProductRecipe
from app.models.user import User
from app.schemas.menu import (
    ModifierOut,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    RecipeLineOut,
    RecipeReplaceRequest,
)
from app.services.order_service import recompute_product_cost_price

router = APIRouter(prefix="/products", tags=["products"])

_ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_MAX_IMAGE_BYTES = 3 * 1024 * 1024
# Reject empty / test payloads that are not decodable in browsers
_MIN_IMAGE_BYTES = 32

_staff = require_roles("owner", "manager", "cashier")
_WRITERS = require_roles("owner", "manager")
_writers = _WRITERS


def _safe_remove_uploaded_file(image_url: str | None) -> None:
    if not image_url or not image_url.startswith("/static/uploads/products/"):
        return
    name = image_url.rstrip("/").split("/")[-1]
    if not name or ".." in name or "/" in name:
        return
    path = PRODUCT_UPLOAD_DIR / name
    try:
        if path.is_file() and path.resolve().parent == PRODUCT_UPLOAD_DIR.resolve():
            path.unlink()
    except OSError:
        pass


def _ensure_upload_dir() -> None:
    PRODUCT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _to_out(p: Product) -> ProductOut:
    return ProductOut(
        id=p.id,
        category_id=p.category_id,
        name=p.name,
        name_ar=p.name_ar,
        price=p.price,
        cost_price=p.cost_price,
        description=p.description,
        image_url=p.image_url,
        is_active=p.is_active,
        sort_order=p.sort_order,
        created_at=p.created_at,
        modifiers=[ModifierOut.model_validate(m) for m in p.modifiers],
        recipe=[RecipeLineOut.model_validate(r) for r in p.recipe_lines],
    )


def _load_product(db: Session, product_id: int) -> Product:
    p = (
        db.query(Product)
        .options(joinedload(Product.modifiers), joinedload(Product.recipe_lines))
        .filter(Product.id == product_id)
        .first()
    )
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return p


@router.get("", response_model=list[ProductOut])
def list_products(
    category_id: int | None = None,
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
    _: User = Depends(_staff),
):
    q = db.query(Product).options(
        joinedload(Product.modifiers),
        joinedload(Product.recipe_lines),
    )
    if category_id is not None:
        q = q.filter(Product.category_id == category_id)
    if active_only:
        q = q.filter(Product.is_active.is_(True))
    rows = q.order_by(Product.sort_order, Product.id).all()
    return [_to_out(p) for p in rows]


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(_staff),
):
    p = _load_product(db, product_id)
    return _to_out(p)


@router.post("", response_model=ProductOut)
def create_product(
    body: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(_writers),
):
    data = body.model_dump(exclude={"modifiers"})
    p = Product(**data)
    db.add(p)
    db.flush()
    for m in body.modifiers:
        db.add(ProductModifier(product_id=p.id, **m.model_dump()))
    db.flush()
    recompute_product_cost_price(db, p.id)
    db.commit()
    p = _load_product(db, p.id)
    return _to_out(p)


@router.post("/{product_id}/image", response_model=ProductOut)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(_writers),
):
    p = db.get(Product, product_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    suffix = Path(file.filename or "").suffix.lower()
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
    _safe_remove_uploaded_file(p.image_url)
    fname = f"{product_id}_{uuid.uuid4().hex}{suffix}"
    dest = PRODUCT_UPLOAD_DIR / fname
    try:
        dest.write_bytes(raw)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save image to disk: {exc}",
        ) from exc
    p.image_url = f"/static/uploads/products/{fname}"
    db.commit()
    p = _load_product(db, product_id)
    return _to_out(p)


@router.delete("/{product_id}/image", response_model=ProductOut)
def delete_product_image(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(_writers),
):
    p = db.get(Product, product_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    _safe_remove_uploaded_file(p.image_url)
    p.image_url = None
    db.commit()
    p = _load_product(db, product_id)
    return _to_out(p)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    body: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(_writers),
):
    p = db.get(Product, product_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    payload = body.model_dump(exclude_unset=True)
    mods = payload.pop("modifiers", None)
    for k, v in payload.items():
        setattr(p, k, v)
    if mods is not None:
        db.query(ProductModifier).filter(ProductModifier.product_id == p.id).delete(
            synchronize_session=False
        )
        for m in mods:
            db.add(ProductModifier(product_id=p.id, **m))
    db.flush()
    recompute_product_cost_price(db, p.id)
    db.commit()
    p = _load_product(db, product_id)
    return _to_out(p)


@router.post("/{product_id}/recipe", response_model=ProductOut)
def replace_recipe(
    product_id: int,
    body: RecipeReplaceRequest,
    db: Session = Depends(get_db),
    _: User = Depends(_writers),
):
    p = db.get(Product, product_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    db.query(ProductRecipe).filter(ProductRecipe.product_id == p.id).delete(synchronize_session=False)
    for line in body.lines:
        db.add(ProductRecipe(product_id=p.id, **line.model_dump()))
    db.flush()
    recompute_product_cost_price(db, p.id)
    db.commit()
    p = _load_product(db, product_id)
    return _to_out(p)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(_writers),
):
    p = db.get(Product, product_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    sold = db.query(OrderItem).filter(OrderItem.product_id == product_id).first() is not None
    if sold:
        p.is_active = False
        db.commit()
        return None
    _safe_remove_uploaded_file(p.image_url)
    db.query(ProductModifier).filter(ProductModifier.product_id == p.id).delete(synchronize_session=False)
    db.query(ProductRecipe).filter(ProductRecipe.product_id == p.id).delete(synchronize_session=False)
    db.delete(p)
    db.commit()
    return None
