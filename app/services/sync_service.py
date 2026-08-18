import hashlib
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.time import to_naive_utc
from app.models.category import Category
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.schemas.orders import OrderCreate
from app.schemas.sync import (
    DeviceOrderIn,
    SyncCatalogOut,
    SyncCategoryOut,
    SyncModifierOut,
    SyncOrderResult,
    SyncProductOut,
    SyncShopOut,
)
from app.services import order_service
from app.services.shop_settings_service import display_cafe_name, get_settings


def _http_detail_reason(exc: HTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, list):
        return "; ".join(str(item) for item in detail)
    return str(detail)


def _catalog_version(categories: list[Category], products: list[Product], shop: SyncShopOut) -> str:
    h = hashlib.sha256()
    h.update(
        f"shop|{shop.cafe_name}|{shop.phone_number}|{shop.logo_url}|{shop.payment_qr_url}".encode()
    )
    for cat in categories:
        h.update(f"c|{cat.id}|{cat.name}|{cat.name_ar}|{cat.sort_order}".encode())
    for product in products:
        h.update(
            f"p|{product.id}|{product.category_id}|{product.name}|{product.name_ar}|"
            f"{product.price}|{product.sort_order}|{product.image_url}".encode()
        )
        for mod in product.modifiers:
            h.update(
                f"m|{mod.id}|{mod.group_name}|{mod.option_name}|{mod.extra_price}".encode()
            )
    return h.hexdigest()[:16]


def get_device_catalog(db: Session) -> SyncCatalogOut:
    settings_row = get_settings(db)
    shop = SyncShopOut(
        cafe_name=display_cafe_name(settings_row),
        phone_number=settings_row.phone_number,
        logo_url=settings_row.logo_url,
        payment_qr_url=settings_row.payment_qr_url,
    )
    categories = (
        db.query(Category)
        .filter(Category.is_active.is_(True))
        .order_by(Category.sort_order, Category.id)
        .all()
    )
    active_category_ids = [c.id for c in categories]
    products: list[Product] = []
    if active_category_ids:
        products = (
            db.query(Product)
            .options(joinedload(Product.modifiers))
            .filter(
                Product.is_active.is_(True),
                Product.category_id.in_(active_category_ids),
            )
            .order_by(Product.sort_order, Product.id)
            .all()
        )
    return SyncCatalogOut(
        generated_at=datetime.now(timezone.utc),
        catalog_version=_catalog_version(categories, products, shop),
        shop=shop,
        categories=[SyncCategoryOut.model_validate(c) for c in categories],
        products=[
            SyncProductOut(
                id=p.id,
                category_id=p.category_id,
                name=p.name,
                name_ar=p.name_ar,
                price=p.price,
                description=p.description,
                image_url=p.image_url,
                sort_order=p.sort_order,
                modifiers=[SyncModifierOut.model_validate(m) for m in p.modifiers],
            )
            for p in products
        ],
    )


def _existing_by_client_uuid(db: Session, client_uuid: str) -> Order | None:
    return db.query(Order).filter(Order.client_uuid == client_uuid).first()


def _success_result(client_uuid: UUID, server_order_id: int) -> SyncOrderResult:
    return SyncOrderResult(
        client_uuid=client_uuid,
        status="success",
        server_order_id=server_order_id,
    )


def _failed_result(client_uuid: UUID, reason: str) -> SyncOrderResult:
    return SyncOrderResult(
        client_uuid=client_uuid,
        status="failed",
        reason=reason,
    )


def sync_device_orders(
    db: Session,
    user: User,
    orders: list[DeviceOrderIn],
    *,
    batch_device_id: str | None = None,
) -> list[SyncOrderResult]:
    """Process each device order independently. Failures do not abort the batch."""
    results: list[SyncOrderResult] = []
    for payload in orders:
        results.append(
            _sync_one_device_order(db, user, payload, batch_device_id=batch_device_id)
        )
    return results


def _sync_one_device_order(
    db: Session,
    user: User,
    payload: DeviceOrderIn,
    *,
    batch_device_id: str | None,
) -> SyncOrderResult:
    uuid_str = str(payload.client_uuid)
    existing = _existing_by_client_uuid(db, uuid_str)
    if existing is not None:
        return _success_result(payload.client_uuid, existing.id)

    device_id = payload.device_id or batch_device_id
    created_at = to_naive_utc(payload.created_at) if payload.created_at is not None else None
    create_payload = OrderCreate(
        items=payload.items,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        customer_car_plate=payload.customer_car_plate,
        payment_method=payload.payment_method,
        notes=payload.notes,
    )
    try:
        order = order_service.create_device_order(
            db,
            user,
            create_payload,
            client_uuid=uuid_str,
            device_id=device_id,
            created_at=created_at,
        )
        db.commit()
        return _success_result(payload.client_uuid, order.id)
    except HTTPException as exc:
        db.rollback()
        return _failed_result(payload.client_uuid, _http_detail_reason(exc))
    except IntegrityError:
        db.rollback()
        raced = _existing_by_client_uuid(db, uuid_str)
        if raced is not None:
            return _success_result(payload.client_uuid, raced.id)
        return _failed_result(payload.client_uuid, "Could not save order (duplicate or constraint error)")
    except Exception as exc:
        db.rollback()
        return _failed_result(payload.client_uuid, str(exc) or "Unexpected error while saving order")
