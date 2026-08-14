"""Public online store API (Phase 3) — mounted at /api/store."""
from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.category import Category
from app.models.order import Order
from app.models.product import Product
from app.schemas.store import (
    PublicOrderStatusOut,
    StoreCategoryOut,
    StoreMenuOut,
    StoreModifierOut,
    StoreOrderCreate,
    StoreOrderCreatedOut,
    StoreProductOut,
)
from app.services import order_service, whatsapp_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/menu", response_model=StoreMenuOut)
def get_store_menu(db: Session = Depends(get_db)):
    cats = (
        db.query(Category)
        .filter(Category.is_active.is_(True))
        .order_by(Category.sort_order, Category.id)
        .all()
    )
    out_cats: list[StoreCategoryOut] = []
    for c in cats:
        prods = (
            db.query(Product)
            .options(joinedload(Product.modifiers))
            .filter(Product.category_id == c.id, Product.is_active.is_(True))
            .order_by(Product.sort_order, Product.id)
            .all()
        )
        out_prods = [
            StoreProductOut(
                id=p.id,
                name=p.name,
                name_ar=p.name_ar,
                price=p.price,
                description=p.description,
                image_url=p.image_url,
                modifiers=[StoreModifierOut.model_validate(m) for m in p.modifiers],
            )
            for p in prods
        ]
        if not out_prods:
            continue
        out_cats.append(
            StoreCategoryOut(
                id=c.id,
                name=c.name,
                name_ar=c.name_ar,
                products=out_prods,
            )
        )
    return StoreMenuOut(categories=out_cats)


@router.post("/orders", response_model=StoreOrderCreatedOut)
def create_store_order(body: StoreOrderCreate, db: Session = Depends(get_db)):
    phone = whatsapp_service.compose_gulf_whatsapp(
        body.whatsapp_country, body.whatsapp_phone
    )
    if len(re.sub(r"\D", "", phone)) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone for selected country (enter local mobile without country code)",
        )
    try:
        order = order_service.create_online_order(
            db,
            customer_name=body.customer_name,
            customer_phone=phone,
            payment_method=body.payment_method,
            notes=body.notes,
            items=body.items,
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("create_store_order failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not place order",
        )
    db.refresh(order)
    try:
        whatsapp_service.notify_order_received(phone, order.id)
    except Exception:
        logger.exception("WhatsApp order confirmation failed (order still created)")
    return StoreOrderCreatedOut(
        id=order.id,
        status=order.status,
        total_amount=order.total_amount,
        created_at=order.created_at,
    )


@router.get("/orders/{order_id}/status", response_model=PublicOrderStatusOut)
def get_public_order_status(order_id: int, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None or order.source != "online":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return PublicOrderStatusOut.model_validate(order)
