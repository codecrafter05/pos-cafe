"""
Wipe POS demo data (orders, purchases, movements, menu, inventory) and refill
with consistent categories, raw materials, products, recipes, and modifiers.

Keeps users unchanged (log in with your existing account).

Usage:
    cd "pos cafe"
    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --yes   # non-interactive confirm
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import delete

from app.core.database import SessionLocal
from app.models.category import Category
from app.models.inventory_movement import InventoryMovement
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.product_modifier import ProductModifier
from app.models.product_recipe import ProductRecipe
from app.models.purchase import Purchase
from app.models.raw_material import RawMaterial
from app.services.order_service import recompute_product_cost_price


def _d(x: str | float | int) -> Decimal:
    return Decimal(str(x))


def clear_transactional_data(db) -> None:
    """Delete orders, purchases, movements, menu, inventory. Preserve users."""
    db.execute(delete(OrderItem))
    db.execute(delete(Order))
    db.execute(delete(Purchase))
    db.execute(delete(InventoryMovement))
    db.execute(delete(ProductModifier))
    db.execute(delete(ProductRecipe))
    db.execute(delete(Product))
    db.execute(delete(Category))
    db.execute(delete(RawMaterial))
    db.commit()


def seed_raw_materials(db) -> dict[str, RawMaterial]:
    """Realistic BHD costs: coffee ~8/kg → 0.008/g; milk ~1/L → 0.001/ml."""
    rows: list[tuple[str, str, Decimal, Decimal, Decimal]] = [
        ("Espresso blend", "g", _d("60000"), _d("2500"), _d("0.008")),
        ("Whole milk", "ml", _d("250000"), _d("12000"), _d("0.001")),
        ("Oat milk", "ml", _d("90000"), _d("5000"), _d("0.002")),
        ("Vanilla syrup", "ml", _d("30000"), _d("1200"), _d("0.003")),
        ("Caramel syrup", "ml", _d("30000"), _d("1200"), _d("0.003")),
        ("Simple syrup", "ml", _d("35000"), _d("1500"), _d("0.002")),
        ("Cocoa powder", "g", _d("20000"), _d("800"), _d("0.018")),
        ("Tea leaves", "g", _d("10000"), _d("400"), _d("0.022")),
        ("Matcha powder", "g", _d("6000"), _d("300"), _d("0.055")),
        ("Filtered water", "ml", _d("600000"), _d("30000"), _d("0.0001")),
        ("Croissant dough", "piece", _d("400"), _d("40"), _d("0.35")),
        ("Puff pastry sheet", "piece", _d("250"), _d("25"), _d("0.42")),
        ("Whipping cream", "ml", _d("40000"), _d("2500"), _d("0.0045")),
        ("Orange juice", "ml", _d("60000"), _d("3500"), _d("0.0016")),
        ("Apple juice", "ml", _d("50000"), _d("3000"), _d("0.0014")),
        ("Burger bun", "piece", _d("500"), _d("50"), _d("0.11")),
        ("Sliced bread", "piece", _d("450"), _d("45"), _d("0.035")),
        ("Grilled chicken", "g", _d("25000"), _d("1500"), _d("0.0075")),
        ("Cheddar cheese", "g", _d("15000"), _d("900"), _d("0.019")),
        ("Lettuce", "g", _d("10000"), _d("600"), _d("0.002")),
        ("Butter", "g", _d("5000"), _d("400"), _d("0.012")),
        ("Chocolate chips", "g", _d("12000"), _d("600"), _d("0.015")),
        ("Egg", "piece", _d("600"), _d("60"), _d("0.045")),
    ]
    by_key: dict[str, RawMaterial] = {}
    for name, unit, stock, min_a, cost in rows:
        rm = RawMaterial(
            name=name,
            unit=unit,
            current_stock=stock,
            min_stock_alert=min_a,
            cost_per_unit=cost,
            created_at=datetime.now(timezone.utc),
        )
        db.add(rm)
        key = name.lower().replace(" ", "_")
        by_key[key] = rm
    db.flush()
    return by_key


def seed_categories(db) -> dict[str, Category]:
    specs: list[tuple[str, str | None, int]] = [
        ("Hot Coffee", "قهوة ساخنة", 10),
        ("Cold Coffee", "قهوة باردة", 20),
        ("Tea & Matcha", "شاي وماتشا", 30),
        ("Fresh Juices", "عصائر طازجة", 40),
        ("Pastries", "مخبوزات", 50),
        ("Sandwiches", "سندويشات", 60),
    ]
    out: dict[str, Category] = {}
    for name, ar, so in specs:
        c = Category(
            name=name,
            name_ar=ar,
            sort_order=so,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(c)
        out[name] = c
    db.flush()
    return out


def _recipe(db, product: Product, lines: list[tuple[RawMaterial, Decimal, str]]) -> None:
    for rm, qty, unit in lines:
        db.add(
            ProductRecipe(
                product_id=product.id,
                raw_material_id=rm.id,
                quantity_used=qty,
                unit=unit,
            )
        )


def _mods(db, product: Product, mods: list[tuple[str, str, Decimal]]) -> None:
    for group, option, extra in mods:
        db.add(
            ProductModifier(
                product_id=product.id,
                group_name=group,
                option_name=option,
                extra_price=extra,
            )
        )


def add_product(
    db,
    category: Category,
    *,
    name: str,
    name_ar: str | None,
    price: Decimal,
    sort_order: int,
    recipes: list[tuple[RawMaterial, Decimal, str]],
    modifiers: list[tuple[str, str, Decimal]] | None = None,
) -> Product:
    p = Product(
        category_id=category.id,
        name=name,
        name_ar=name_ar,
        price=price,
        cost_price=Decimal("0"),
        description=None,
        image_url=None,
        is_active=True,
        sort_order=sort_order,
        created_at=datetime.now(timezone.utc),
    )
    db.add(p)
    db.flush()
    _recipe(db, p, recipes)
    if modifiers:
        _mods(db, p, modifiers)
    recompute_product_cost_price(db, p.id)
    return p


def seed_products(db, cats: dict[str, Category], m: dict[str, RawMaterial]) -> int:
    """Returns product count."""
    def rm(key: str) -> RawMaterial:
        return m[key]

    sort = 0

    # --- Hot Coffee ---
    hc = cats["Hot Coffee"]
    add_product(
        db, hc, name="Espresso", name_ar="إسبريسو", price=_d("1.200"), sort_order=sort,
        recipes=[(rm("espresso_blend"), _d("7"), "g")],
    )
    sort += 1
    add_product(
        db, hc, name="Double Espresso", name_ar="دبل إسبريسو", price=_d("1.600"), sort_order=sort,
        recipes=[(rm("espresso_blend"), _d("14"), "g")],
    )
    sort += 1
    add_product(
        db, hc, name="Americano", name_ar="أمريكانو", price=_d("1.400"), sort_order=sort,
        recipes=[
            (rm("espresso_blend"), _d("7"), "g"),
            (rm("filtered_water"), _d("180"), "ml"),
        ],
    )
    sort += 1
    add_product(
        db, hc, name="Cappuccino", name_ar="كابتشينو", price=_d("1.850"), sort_order=sort,
        recipes=[
            (rm("espresso_blend"), _d("7"), "g"),
            (rm("whole_milk"), _d("180"), "ml"),
        ],
        modifiers=[
            ("Size", "Regular", _d("0")),
            ("Size", "Large", _d("0.150")),
            ("Milk", "Whole", _d("0")),
            ("Milk", "Oat", _d("0.100")),
        ],
    )
    sort += 1
    add_product(
        db, hc, name="Latte", name_ar="لاتيه", price=_d("1.950"), sort_order=sort,
        recipes=[
            (rm("espresso_blend"), _d("7"), "g"),
            (rm("whole_milk"), _d("200"), "ml"),
        ],
        modifiers=[
            ("Size", "Regular", _d("0")),
            ("Size", "Large", _d("0.150")),
            ("Milk", "Whole", _d("0")),
            ("Milk", "Oat", _d("0.100")),
        ],
    )
    sort += 1
    add_product(
        db, hc, name="Flat White", name_ar="فلات وايت", price=_d("2.050"), sort_order=sort,
        recipes=[
            (rm("espresso_blend"), _d("14"), "g"),
            (rm("whole_milk"), _d("160"), "ml"),
        ],
    )
    sort += 1
    add_product(
        db, hc, name="Cafe Mocha", name_ar="موكا", price=_d("2.250"), sort_order=sort,
        recipes=[
            (rm("espresso_blend"), _d("7"), "g"),
            (rm("whole_milk"), _d("170"), "ml"),
            (rm("cocoa_powder"), _d("12"), "g"),
            (rm("vanilla_syrup"), _d("8"), "ml"),
        ],
    )
    sort += 1
    add_product(
        db, hc, name="Caramel Macchiato", name_ar="كراميل ماكياتو", price=_d("2.450"), sort_order=sort,
        recipes=[
            (rm("espresso_blend"), _d("7"), "g"),
            (rm("whole_milk"), _d("160"), "ml"),
            (rm("caramel_syrup"), _d("18"), "ml"),
        ],
    )
    sort += 1
    add_product(
        db, hc, name="Hot Chocolate", name_ar="شوكولاتة ساخنة", price=_d("1.900"), sort_order=sort,
        recipes=[
            (rm("whole_milk"), _d("220"), "ml"),
            (rm("cocoa_powder"), _d("22"), "g"),
            (rm("vanilla_syrup"), _d("10"), "ml"),
        ],
    )
    sort += 1

    # --- Cold Coffee ---
    cc = cats["Cold Coffee"]
    add_product(
        db, cc, name="Iced Americano", name_ar="آيس أمريكانو", price=_d("1.550"), sort_order=sort,
        recipes=[
            (rm("espresso_blend"), _d("7"), "g"),
            (rm("filtered_water"), _d("220"), "ml"),
        ],
    )
    sort += 1
    add_product(
        db, cc, name="Iced Latte", name_ar="آيس لاتيه", price=_d("2.000"), sort_order=sort,
        recipes=[
            (rm("espresso_blend"), _d("7"), "g"),
            (rm("whole_milk"), _d("200"), "ml"),
        ],
        modifiers=[
            ("Size", "Regular", _d("0")),
            ("Size", "Large", _d("0.150")),
            ("Milk", "Whole", _d("0")),
            ("Milk", "Oat", _d("0.100")),
        ],
    )
    sort += 1
    add_product(
        db, cc, name="Iced Caramel Latte", name_ar="آيس كراميل لاتيه", price=_d("2.350"), sort_order=sort,
        recipes=[
            (rm("espresso_blend"), _d("7"), "g"),
            (rm("whole_milk"), _d("180"), "ml"),
            (rm("caramel_syrup"), _d("20"), "ml"),
        ],
    )
    sort += 1
    add_product(
        db, cc, name="Cold Brew", name_ar="كولد برو", price=_d("2.250"), sort_order=sort,
        recipes=[
            (rm("espresso_blend"), _d("14"), "g"),
            (rm("filtered_water"), _d("180"), "ml"),
        ],
    )
    sort += 1
    add_product(
        db, cc, name="Iced Mocha", name_ar="آيس موكا", price=_d("2.450"), sort_order=sort,
        recipes=[
            (rm("espresso_blend"), _d("7"), "g"),
            (rm("whole_milk"), _d("170"), "ml"),
            (rm("cocoa_powder"), _d("12"), "g"),
        ],
    )
    sort += 1
    add_product(
        db, cc, name="Coffee Frappé", name_ar="فرابيه قهوة", price=_d("2.850"), sort_order=sort,
        recipes=[
            (rm("espresso_blend"), _d("8"), "g"),
            (rm("whole_milk"), _d("100"), "ml"),
            (rm("whipping_cream"), _d("35"), "ml"),
            (rm("vanilla_syrup"), _d("15"), "ml"),
            (rm("simple_syrup"), _d("15"), "ml"),
        ],
    )
    sort += 1
    add_product(
        db, cc, name="Iced Spanish Latte", name_ar="آيس سبانيش لاتيه", price=_d("2.400"), sort_order=sort,
        recipes=[
            (rm("espresso_blend"), _d("7"), "g"),
            (rm("whole_milk"), _d("140"), "ml"),
            (rm("simple_syrup"), _d("40"), "ml"),
            (rm("vanilla_syrup"), _d("10"), "ml"),
        ],
    )
    sort += 1

    # --- Tea & Matcha ---
    tm = cats["Tea & Matcha"]
    add_product(
        db, tm, name="English Breakfast Tea", name_ar="شاي إنجليزي", price=_d("1.050"), sort_order=sort,
        recipes=[
            (rm("tea_leaves"), _d("3"), "g"),
            (rm("filtered_water"), _d("280"), "ml"),
        ],
    )
    sort += 1
    add_product(
        db, tm, name="Hot Matcha Latte", name_ar="ماتشا لاتيه ساخن", price=_d("2.550"), sort_order=sort,
        recipes=[
            (rm("matcha_powder"), _d("4"), "g"),
            (rm("whole_milk"), _d("200"), "ml"),
            (rm("vanilla_syrup"), _d("6"), "ml"),
        ],
    )
    sort += 1
    add_product(
        db, tm, name="Iced Matcha Latte", name_ar="آيس ماتشا لاتيه", price=_d("2.650"), sort_order=sort,
        recipes=[
            (rm("matcha_powder"), _d("4"), "g"),
            (rm("whole_milk"), _d("200"), "ml"),
            (rm("vanilla_syrup"), _d("8"), "ml"),
        ],
    )
    sort += 1
    add_product(
        db, tm, name="Moroccan Mint Tea", name_ar="شاي نعناع", price=_d("1.200"), sort_order=sort,
        recipes=[
            (rm("tea_leaves"), _d("2.5"), "g"),
            (rm("filtered_water"), _d("260"), "ml"),
            (rm("simple_syrup"), _d("15"), "ml"),
        ],
    )
    sort += 1
    add_product(
        db, tm, name="Lemon Iced Tea", name_ar="شاي مثلج بالليمون", price=_d("1.450"), sort_order=sort,
        recipes=[
            (rm("tea_leaves"), _d("3"), "g"),
            (rm("filtered_water"), _d("220"), "ml"),
            (rm("simple_syrup"), _d("25"), "ml"),
        ],
    )
    sort += 1

    # --- Fresh Juices ---
    fj = cats["Fresh Juices"]
    add_product(
        db, fj, name="Fresh Orange", name_ar="برتقال طازج", price=_d("1.850"), sort_order=sort,
        recipes=[(rm("orange_juice"), _d("350"), "ml")],
    )
    sort += 1
    add_product(
        db, fj, name="Fresh Apple", name_ar="تفاح طازج", price=_d("1.650"), sort_order=sort,
        recipes=[(rm("apple_juice"), _d("350"), "ml")],
    )
    sort += 1
    add_product(
        db, fj, name="Orange & Apple Mix", name_ar="عصير مشكل", price=_d("1.950"), sort_order=sort,
        recipes=[
            (rm("orange_juice"), _d("180"), "ml"),
            (rm("apple_juice"), _d("180"), "ml"),
        ],
    )
    sort += 1
    add_product(
        db, fj, name="Tropical Blend", name_ar="مكس استوائي", price=_d("2.100"), sort_order=sort,
        recipes=[
            (rm("orange_juice"), _d("200"), "ml"),
            (rm("apple_juice"), _d("150"), "ml"),
            (rm("simple_syrup"), _d("10"), "ml"),
        ],
    )
    sort += 1

    # --- Pastries ---
    pa = cats["Pastries"]
    add_product(
        db, pa, name="Butter Croissant", name_ar="كرواسون زبدة", price=_d("0.850"), sort_order=sort,
        recipes=[
            (rm("croissant_dough"), _d("1"), "piece"),
            (rm("butter"), _d("5"), "g"),
        ],
    )
    sort += 1
    add_product(
        db, pa, name="Almond Croissant", name_ar="كرواسون لوز", price=_d("1.150"), sort_order=sort,
        recipes=[
            (rm("croissant_dough"), _d("1"), "piece"),
            (rm("butter"), _d("6"), "g"),
            (rm("chocolate_chips"), _d("8"), "g"),
        ],
    )
    sort += 1
    add_product(
        db, pa, name="Pain au Chocolat", name_ar="بان أو شوكولا", price=_d("1.050"), sort_order=sort,
        recipes=[
            (rm("puff_pastry_sheet"), _d("1"), "piece"),
            (rm("chocolate_chips"), _d("22"), "g"),
            (rm("butter"), _d("4"), "g"),
        ],
    )
    sort += 1
    add_product(
        db, pa, name="Cheese Danish", name_ar="دانية جبن", price=_d("0.950"), sort_order=sort,
        recipes=[
            (rm("puff_pastry_sheet"), _d("1"), "piece"),
            (rm("cheddar_cheese"), _d("25"), "g"),
            (rm("simple_syrup"), _d("5"), "ml"),
        ],
    )
    sort += 1
    add_product(
        db, pa, name="Chocolate Muffin", name_ar="مافن شوكولا", price=_d("1.100"), sort_order=sort,
        recipes=[
            (rm("chocolate_chips"), _d("35"), "g"),
            (rm("whole_milk"), _d("40"), "ml"),
            (rm("butter"), _d("12"), "g"),
            (rm("egg"), _d("1"), "piece"),
        ],
    )
    sort += 1
    add_product(
        db, pa, name="Blueberry Scone", name_ar="سكون توت أزرق", price=_d("0.980"), sort_order=sort,
        recipes=[
            (rm("butter"), _d("18"), "g"),
            (rm("whole_milk"), _d("25"), "ml"),
            (rm("simple_syrup"), _d("8"), "ml"),
        ],
    )
    sort += 1

    # --- Sandwiches ---
    sw = cats["Sandwiches"]
    add_product(
        db, sw, name="Chicken Club", name_ar="كلوب دجاج", price=_d("2.650"), sort_order=sort,
        recipes=[
            (rm("burger_bun"), _d("1"), "piece"),
            (rm("grilled_chicken"), _d("130"), "g"),
            (rm("cheddar_cheese"), _d("35"), "g"),
            (rm("lettuce"), _d("20"), "g"),
        ],
    )
    sort += 1
    add_product(
        db, sw, name="Grilled Cheese", name_ar="جبن مشوي", price=_d("1.850"), sort_order=sort,
        recipes=[
            (rm("sliced_bread"), _d("2"), "piece"),
            (rm("cheddar_cheese"), _d("70"), "g"),
            (rm("butter"), _d("15"), "g"),
        ],
    )
    sort += 1
    add_product(
        db, sw, name="Egg & Cheese Muffin", name_ar="إنجلش مافن بيض", price=_d("2.100"), sort_order=sort,
        recipes=[
            (rm("burger_bun"), _d("1"), "piece"),
            (rm("egg"), _d("1"), "piece"),
            (rm("cheddar_cheese"), _d("30"), "g"),
            (rm("butter"), _d("5"), "g"),
        ],
    )
    sort += 1
    add_product(
        db, sw, name="Chicken Wrap", name_ar="راب دجاج", price=_d("2.450"), sort_order=sort,
        recipes=[
            (rm("lettuce"), _d("35"), "g"),
            (rm("grilled_chicken"), _d("110"), "g"),
            (rm("cheddar_cheese"), _d("25"), "g"),
        ],
    )
    sort += 1

    return sort


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset menu/inventory demo data")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation",
    )
    args = parser.parse_args()

    if not args.yes:
        print(
            "This will DELETE all orders, purchases, inventory movements, "
            "products, categories, and raw materials.\n"
            "Users are kept. Type YES to continue:",
            end=" ",
        )
        if input().strip() != "YES":
            print("Aborted.")
            return

    db = SessionLocal()
    try:
        clear_transactional_data(db)
        mats = seed_raw_materials(db)
        cats = seed_categories(db)
        n = seed_products(db, cats, mats)
        db.commit()
        print(
            f"Done. Seeded {len(mats)} raw materials, {len(cats)} categories, {n} products."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
