"""
Additive seed for categories and products (no inventory / recipes).

Creates missing categories and products only. Does not delete or update
existing rows (users, orders, or already-seeded menu).

Usage:
    cd /var/www/pos
    source .venv/bin/activate
    python scripts/seed_demo_data.py
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from app.core.database import SessionLocal
from app.models.category import Category
from app.models.product import Product


def _d(value: str | float | int) -> Decimal:
    return Decimal(str(value))


def _get_or_create_category(db, *, name: str, sort_order: int = 0) -> Category:
    existing = db.query(Category).filter(Category.name == name).first()
    if existing:
        return existing
    cat = Category(name=name, sort_order=sort_order, is_active=True)
    db.add(cat)
    db.flush()
    return cat


def _get_or_create_product(
    db,
    *,
    category_id: int,
    name: str,
    price: Decimal,
    sort_order: int = 0,
) -> tuple[Product, bool]:
    existing = db.query(Product).filter(Product.name == name).first()
    if existing:
        return existing, False
    p = Product(
        category_id=category_id,
        name=name,
        price=price,
        is_active=True,
        sort_order=sort_order,
    )
    db.add(p)
    db.flush()
    return p, True


def main() -> None:
    db = SessionLocal()
    try:
        drinks = _get_or_create_category(db, name="Drinks", sort_order=1)
        food = _get_or_create_category(db, name="Food", sort_order=2)
        created = 0
        for name, price, cat in (
            ("Classic matcha", _d("1.700"), drinks),
            ("Gathering box waffles", _d("5.000"), food),
        ):
            _, was_created = _get_or_create_product(
                db, category_id=cat.id, name=name, price=price
            )
            if was_created:
                created += 1
        db.commit()
        print(f"Seed complete. New products: {created}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
