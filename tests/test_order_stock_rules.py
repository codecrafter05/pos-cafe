"""Stock rules on the sales path.

Sales must never be blocked by stock levels — stock is allowed to go negative and
stays visible to the owner. The separate recipe-existence rule must still block,
since selling a product with no recipe records zero cost and fakes the profit.

    .venv/bin/python -m unittest discover -s tests -v
"""

import unittest
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  — registers every mapper before create_all
from app.core.database import Base
from app.models.category import Category
from app.models.inventory_movement import InventoryMovement
from app.models.modifier_recipe import ModifierRecipe
from app.models.product import Product
from app.models.product_modifier import ProductModifier
from app.models.product_recipe import ProductRecipe
from app.models.raw_material import RawMaterial
from app.models.user import User
from app.schemas.orders import OrderCreate, OrderItemIn, OrderModifierSnapshot
from app.services import order_service


class StockRulesTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

        self.user = User(
            name="Cashier", username="cashier1", password_hash="x",
            role="cashier", is_active=True,
        )
        self.category = Category(name="Waffles", sort_order=1)
        self.db.add_all([self.user, self.category])
        self.db.flush()

        self.material = RawMaterial(
            name="Croissant", unit="piece",
            current_stock=Decimal("0"), min_stock_alert=Decimal("2"),
            cost_per_unit=Decimal("0.400"),
        )
        self.db.add(self.material)
        self.db.flush()

        self.product = Product(
            category_id=self.category.id, name="Chocolate Strawberry Waffles",
            price=Decimal("1.700"), cost_price=Decimal("0.400"), is_active=True,
        )
        self.db.add(self.product)
        self.db.flush()
        self.db.add(ProductRecipe(
            product_id=self.product.id, raw_material_id=self.material.id,
            quantity_used=Decimal("1.000"), unit="piece",
        ))
        self.db.flush()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _order(self, quantity=1, modifiers=None):
        return order_service.create_device_order(
            self.db, self.user,
            OrderCreate(
                items=[OrderItemIn(
                    product_id=self.product.id,
                    quantity=quantity,
                    modifiers=modifiers or [],
                )],
                customer_name=None, customer_phone=None, customer_car_plate=None,
                payment_method="cash", notes=None,
            ),
            client_uuid=f"uuid-{quantity}-{len(modifiers or [])}",
        )

    # ---- stock never blocks a sale -------------------------------------

    def test_sale_completes_at_zero_stock_and_goes_negative(self):
        order = self._order(quantity=2)

        self.assertIsNotNone(order.id)
        self.assertEqual(order.total_amount, Decimal("3.400"))
        self.db.refresh(self.material)
        self.assertEqual(self.material.current_stock, Decimal("-2.000"))

    def test_sale_completes_when_stock_is_already_negative(self):
        self.material.current_stock = Decimal("-5.000")
        self.db.flush()

        order = self._order(quantity=3)

        self.assertIsNotNone(order.id)
        self.db.refresh(self.material)
        self.assertEqual(self.material.current_stock, Decimal("-8.000"))

    def test_cost_is_still_tracked_on_a_negative_stock_sale(self):
        order = self._order(quantity=2)

        self.assertEqual(order.total_cost, Decimal("0.800"))
        self.assertEqual(order.profit, Decimal("2.600"))

    def test_deduction_movements_are_still_written_when_going_negative(self):
        order = self._order(quantity=2)

        movements = (
            self.db.query(InventoryMovement)
            .filter(
                InventoryMovement.order_id == order.id,
                InventoryMovement.movement_type == "sale_deduction",
            )
            .all()
        )
        self.assertEqual(len(movements), 1)
        self.assertEqual(movements[0].quantity, Decimal("-2.000"))

    def test_repeated_sales_keep_accumulating_the_shortfall(self):
        for _ in range(3):
            order_service.create_pos_order(
                self.db, self.user,
                OrderCreate(
                    items=[OrderItemIn(product_id=self.product.id, quantity=1)],
                    customer_name=None, customer_phone=None, customer_car_plate=None,
                    payment_method="cash", notes=None,
                ),
            )
        self.db.refresh(self.material)
        self.assertEqual(self.material.current_stock, Decimal("-3.000"))

    def test_modifier_recipe_also_goes_negative_without_blocking(self):
        syrup = RawMaterial(
            name="Chocolate syrup", unit="ml",
            current_stock=Decimal("-1.000"), cost_per_unit=Decimal("0.010"),
        )
        self.db.add(syrup)
        self.db.flush()
        modifier = ProductModifier(
            product_id=self.product.id, group_name="Sauce",
            option_name="Extra chocolate", extra_price=Decimal("0.300"),
        )
        self.db.add(modifier)
        self.db.flush()
        self.db.add(ModifierRecipe(
            modifier_id=modifier.id, raw_material_id=syrup.id,
            quantity_used=Decimal("20.000"), unit="ml",
        ))
        self.db.flush()

        order = self._order(
            quantity=1,
            modifiers=[OrderModifierSnapshot(
                group_name="Sauce", option_name="Extra chocolate",
                extra_price=Decimal("0.300"),
            )],
        )

        self.assertIsNotNone(order.id)
        self.assertEqual(order.total_amount, Decimal("2.000"))
        self.db.refresh(syrup)
        self.assertEqual(syrup.current_stock, Decimal("-21.000"))

    def test_substitution_modifier_skips_the_base_line_and_still_allows_negative(self):
        oat = RawMaterial(
            name="Oat base", unit="piece",
            current_stock=Decimal("-2.000"), cost_per_unit=Decimal("0.500"),
        )
        self.db.add(oat)
        self.db.flush()
        modifier = ProductModifier(
            product_id=self.product.id, group_name="Base",
            option_name="Oat instead", extra_price=Decimal("0"),
        )
        self.db.add(modifier)
        self.db.flush()
        self.db.add(ModifierRecipe(
            modifier_id=modifier.id, raw_material_id=oat.id,
            quantity_used=Decimal("1.000"), unit="piece",
            substitutes_raw_material_id=self.material.id,
        ))
        self.db.flush()

        order = self._order(
            quantity=1,
            modifiers=[OrderModifierSnapshot(
                group_name="Base", option_name="Oat instead", extra_price=Decimal("0"),
            )],
        )

        self.assertIsNotNone(order.id)
        self.db.refresh(self.material)
        self.db.refresh(oat)
        self.assertEqual(self.material.current_stock, Decimal("0.000"),
                         "substituted base ingredient must not be deducted")
        self.assertEqual(oat.current_stock, Decimal("-3.000"))

    # ---- the recipe-existence rule is untouched -------------------------

    def test_product_without_a_recipe_is_still_rejected(self):
        bare = Product(
            category_id=self.category.id, name="Mystery item",
            price=Decimal("2.000"), is_active=True,
        )
        self.db.add(bare)
        self.db.flush()

        with self.assertRaises(HTTPException) as ctx:
            order_service.create_device_order(
                self.db, self.user,
                OrderCreate(
                    items=[OrderItemIn(product_id=bare.id, quantity=1)],
                    customer_name=None, customer_phone=None, customer_car_plate=None,
                    payment_method="cash", notes=None,
                ),
                client_uuid="uuid-bare",
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("no recipe is configured", str(ctx.exception.detail))

    def test_inactive_product_is_still_rejected(self):
        self.product.is_active = False
        self.db.flush()

        with self.assertRaises(HTTPException) as ctx:
            self._order(quantity=1)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_unknown_modifier_is_still_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            self._order(
                quantity=1,
                modifiers=[OrderModifierSnapshot(
                    group_name="Nope", option_name="Nope", extra_price=Decimal("0"),
                )],
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid modifier", str(ctx.exception.detail))


if __name__ == "__main__":
    unittest.main()
