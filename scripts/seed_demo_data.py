"""
Additive seed for this coffee shop's real menu.

Creates missing raw materials, categories, products, and recipe lines only.
Does not delete or update existing rows (users, orders, or already-seeded menu).

Usage:
    cd /var/www/pos
    source .venv/bin/activate
    python scripts/seed_demo_data.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from app.core.database import SessionLocal
from app.models.category import Category
from app.models.product import Product
from app.models.product_recipe import ProductRecipe
from app.models.raw_material import RawMaterial
from app.services.order_service import recompute_product_cost_price


def _d(value: str | float | int) -> Decimal:
    return Decimal(str(value))


def _get_or_create_raw_material(
    db,
    *,
    name: str,
    unit: str,
    current_stock: Decimal,
    min_stock_alert: Decimal,
    cost_per_unit: Decimal,
) -> tuple[RawMaterial, bool]:
    existing = db.query(RawMaterial).filter(RawMaterial.name == name).first()
    if existing:
        return existing, False
    rm = RawMaterial(
        name=name,
        unit=unit,
        current_stock=current_stock,
        min_stock_alert=min_stock_alert,
        cost_per_unit=cost_per_unit,
        created_at=datetime.now(timezone.utc),
    )
    db.add(rm)
    db.flush()
    return rm, True


def _get_or_create_category(
    db,
    *,
    name: str,
    name_ar: str,
    sort_order: int,
) -> tuple[Category, bool]:
    existing = db.query(Category).filter(Category.name == name).first()
    if existing:
        return existing, False
    cat = Category(
        name=name,
        name_ar=name_ar,
        sort_order=sort_order,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(cat)
    db.flush()
    return cat, True


def _get_or_create_product(
    db,
    *,
    category: Category,
    name: str,
    name_ar: str,
    price: Decimal,
    sort_order: int,
) -> tuple[Product, bool]:
    existing = (
        db.query(Product)
        .filter(Product.name == name, Product.category_id == category.id)
        .first()
    )
    if existing:
        return existing, False
    product = Product(
        category_id=category.id,
        name=name,
        name_ar=name_ar,
        price=price,
        cost_price=_d("0"),
        description=None,
        image_url=None,
        is_active=True,
        sort_order=sort_order,
        created_at=datetime.now(timezone.utc),
    )
    db.add(product)
    db.flush()
    return product, True


def _ensure_recipe_line(
    db,
    *,
    product: Product,
    raw_material: RawMaterial,
    quantity_used: Decimal,
    unit: str,
) -> bool:
    existing = (
        db.query(ProductRecipe)
        .filter(
            ProductRecipe.product_id == product.id,
            ProductRecipe.raw_material_id == raw_material.id,
        )
        .first()
    )
    if existing:
        return False
    db.add(
        ProductRecipe(
            product_id=product.id,
            raw_material_id=raw_material.id,
            quantity_used=quantity_used,
            unit=unit,
        )
    )
    return True


def seed_raw_materials(db) -> dict[str, RawMaterial]:
    # Placeholder stock/cost values — update later with real purchasing data.
    specs: list[tuple[str, str, str, str, str]] = [
        # name, unit, current_stock, min_stock_alert, cost_per_unit (BHD)
        ("Matcha powder", "g", "2000", "200", "0.055"),
        ("Milk", "ml", "50000", "5000", "0.001"),
        ("Foam", "ml", "8000", "800", "0.004"),
        ("Vanilla syrup", "ml", "3000", "300", "0.003"),
        ("Agave syrup", "ml", "2000", "200", "0.004"),
        ("Ice", "g", "30000", "3000", "0.001"),
        ("Croissant", "piece", "80", "10", "0.250"),
        ("Chocolate", "g", "3000", "300", "0.012"),
        ("White chocolate", "g", "2000", "200", "0.014"),
        ("White sugar", "g", "5000", "500", "0.001"),
        ("Cherry beans", "g", "3000", "300", "0.018"),
        ("Classic beans", "g", "3000", "300", "0.012"),
        ("Red Bull", "piece", "48", "12", "0.800"),
        ("Ice tea", "ml", "10000", "1000", "0.002"),
        ("Hibiscus", "g", "1500", "150", "0.008"),
        ("Pineapple", "g", "8000", "800", "0.003"),
        ("Coconut milk", "ml", "8000", "800", "0.002"),
        ("Pineapple juice", "ml", "10000", "1000", "0.002"),
        ("Strawberry syrup", "ml", "2500", "250", "0.003"),
        ("Peach syrup", "ml", "2500", "250", "0.003"),
        ("Apple syrup", "ml", "2500", "250", "0.003"),
        ("Passion fruit syrup", "ml", "2500", "250", "0.003"),
        ("Rose syrup", "ml", "2500", "250", "0.003"),
        ("Hibiscus syrup", "ml", "2500", "250", "0.003"),
    ]
    by_name: dict[str, RawMaterial] = {}
    created = 0
    for name, unit, stock, min_alert, cost in specs:
        rm, was_created = _get_or_create_raw_material(
            db,
            name=name,
            unit=unit,
            current_stock=_d(stock),
            min_stock_alert=_d(min_alert),
            cost_per_unit=_d(cost),
        )
        by_name[name] = rm
        if was_created:
            created += 1
            print(f"  + raw material: {name} ({unit})")
        else:
            print(f"  = raw material exists: {name}")
    print(f"Raw materials: {created} created, {len(specs) - created} already present")
    return by_name


def seed_categories(db) -> dict[str, Category]:
    specs = [
        ("Matcha", "ماتشا", 10),
        ("Waffles", "وافل", 20),
        ("V60 Coffee", "قهوة V60", 30),
        ("Refreshments", "منعشات", 40),
    ]
    out: dict[str, Category] = {}
    created = 0
    for name, name_ar, sort_order in specs:
        cat, was_created = _get_or_create_category(
            db, name=name, name_ar=name_ar, sort_order=sort_order
        )
        out[name] = cat
        if was_created:
            created += 1
            print(f"  + category: {name}")
        else:
            print(f"  = category exists: {name}")
    print(f"Categories: {created} created, {len(specs) - created} already present")
    return out


def seed_products_and_recipes(
    db,
    cats: dict[str, Category],
    mats: dict[str, RawMaterial],
) -> None:
    def rm(name: str) -> RawMaterial:
        return mats[name]

    products: list[dict] = [
        {
            "category": "Matcha",
            "name": "French Vanilla Matcha",
            "name_ar": "ماتشا فانيلا فرنسية",
            "price": "2.600",
            "sort_order": 10,
            "recipe": [
                (rm("Matcha powder"), "5", "g"),
                (rm("Milk"), "200", "ml"),
                (rm("Foam"), "40", "ml"),
                (rm("Vanilla syrup"), "20", "ml"),
                (rm("Ice"), "120", "g"),
            ],
        },
        {
            "category": "Matcha",
            "name": "Seasalted Vanilla Matcha",
            "name_ar": "ماتشا فانيلا مملحة",
            "price": "2.500",
            "sort_order": 20,
            "recipe": [
                (rm("Matcha powder"), "5", "g"),
                (rm("Milk"), "200", "ml"),
                (rm("Foam"), "40", "ml"),
                (rm("Vanilla syrup"), "20", "ml"),
                (rm("Ice"), "120", "g"),
            ],
        },
        {
            "category": "Matcha",
            "name": "Your Birthday Matcha",
            "name_ar": "ماتشا عيد ميلادك",
            "price": "2.700",
            "sort_order": 30,
            "recipe": [
                (rm("Matcha powder"), "5", "g"),
                (rm("Milk"), "200", "ml"),
                (rm("Foam"), "50", "ml"),
                (rm("Vanilla syrup"), "20", "ml"),
                (rm("Ice"), "120", "g"),
            ],
        },
        {
            "category": "Matcha",
            "name": "White Chocolate Matcha",
            "name_ar": "ماتشا شوكولاتة بيضاء",
            "price": "2.400",
            "sort_order": 40,
            "recipe": [
                (rm("Matcha powder"), "5", "g"),
                (rm("Milk"), "200", "ml"),
                (rm("White chocolate"), "20", "g"),
                (rm("Ice"), "120", "g"),
            ],
        },
        {
            "category": "Waffles",
            "name": "Chocolate Strawberry",
            "name_ar": "شوكولاتة وفراولة",
            "price": "1.700",
            "sort_order": 10,
            "recipe": [
                (rm("Croissant"), "1", "piece"),
                (rm("Chocolate"), "25", "g"),
                (rm("White sugar"), "8", "g"),
            ],
        },
        {
            "category": "Waffles",
            "name": "Cinnamon Custard",
            "name_ar": "كاسترد بالقرفة",
            "price": "1.500",
            "sort_order": 20,
            "recipe": [
                (rm("Croissant"), "1", "piece"),
                (rm("White chocolate"), "20", "g"),
                (rm("White sugar"), "8", "g"),
            ],
        },
        {
            "category": "V60 Coffee",
            "name": "V60 Cherry",
            "name_ar": "V60 كرز",
            "price": "1.500",
            "sort_order": 10,
            "recipe": [
                (rm("Cherry beans"), "15", "g"),
            ],
        },
        {
            "category": "V60 Coffee",
            "name": "V60 Grape",
            "name_ar": "V60 عنب",
            "price": "1.500",
            "sort_order": 20,
            "recipe": [
                (rm("Cherry beans"), "15", "g"),
            ],
        },
        {
            "category": "V60 Coffee",
            "name": "V60 Classic",
            "name_ar": "V60 كلاسيك",
            "price": "1.200",
            "sort_order": 30,
            "recipe": [
                (rm("Classic beans"), "15", "g"),
            ],
        },
        {
            "category": "Refreshments",
            "name": "Piña Colada",
            "name_ar": "بينا كولادا",
            "price": "1.900",
            "sort_order": 10,
            "recipe": [
                (rm("Pineapple"), "80", "g"),
                (rm("Coconut milk"), "80", "ml"),
                (rm("Pineapple juice"), "120", "ml"),
            ],
        },
        {
            "category": "Refreshments",
            "name": "Sun-Kissed Ice Tea",
            "name_ar": "آيس تي",
            "price": "1.600",
            "sort_order": 20,
            "recipe": [
                (rm("Ice tea"), "250", "ml"),
                (rm("Ice"), "120", "g"),
            ],
        },
        {
            "category": "Refreshments",
            "name": "Naughty Hibiscus",
            "name_ar": "كركديه",
            "price": "1.500",
            "sort_order": 30,
            "recipe": [
                (rm("Hibiscus"), "8", "g"),
                (rm("Hibiscus syrup"), "20", "ml"),
                (rm("Ice"), "120", "g"),
            ],
        },
        {
            "category": "Refreshments",
            "name": "DK Redbull",
            "name_ar": "ريد بول",
            "price": "2.200",
            "sort_order": 40,
            "recipe": [
                (rm("Red Bull"), "1", "piece"),
            ],
        },
    ]

    created_products = 0
    created_lines = 0
    for spec in products:
        product, was_created = _get_or_create_product(
            db,
            category=cats[spec["category"]],
            name=spec["name"],
            name_ar=spec["name_ar"],
            price=_d(spec["price"]),
            sort_order=spec["sort_order"],
        )
        if was_created:
            created_products += 1
            print(f"  + product: {spec['name']} ({spec['price']} BD)")
        else:
            print(f"  = product exists: {spec['name']}")

        for material, qty, unit in spec["recipe"]:
            if _ensure_recipe_line(
                db,
                product=product,
                raw_material=material,
                quantity_used=_d(qty),
                unit=unit,
            ):
                created_lines += 1
        db.flush()
        recompute_product_cost_price(db, product.id)

    print(f"Products: {created_products} created, {len(products) - created_products} already present")
    print(f"Recipe lines added: {created_lines}")


def main() -> None:
    db = SessionLocal()
    try:
        print("Seeding raw materials...")
        mats = seed_raw_materials(db)
        print("Seeding categories...")
        cats = seed_categories(db)
        print("Seeding products and recipes...")
        seed_products_and_recipes(db, cats, mats)
        db.commit()

        products = db.query(Product).order_by(Product.id).all()
        missing = []
        for product in products:
            line_count = (
                db.query(ProductRecipe)
                .filter(ProductRecipe.product_id == product.id)
                .count()
            )
            if line_count < 1:
                missing.append(product.name)
            print(f"  recipe check: {product.name} -> {line_count} line(s)")
        if missing:
            raise RuntimeError(f"Products without recipes: {missing}")
        print("All products have at least one recipe line.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
