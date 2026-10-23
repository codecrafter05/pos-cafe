"""Pure POS order rules: no recipes/stock; modifiers are price-only.

    .venv/bin/python -m unittest discover -s tests -v
"""

import unittest
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 — registers every mapper before create_all
from app.core.database import Base
from app.models.category import Category
from app.models.order import Order
from app.models.product import Product
from app.models.product_modifier import ProductModifier
from app.models.user import User
from app.schemas.orders import OrderCreate, OrderItemIn, OrderModifierSnapshot
from app.services import order_service


class PurePosOrdersTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

        self.user = User(
            name="Cashier",
            username="cashier1",
            password_hash="x",
            role="cashier",
            is_active=True,
        )
        self.category = Category(name="Drinks", sort_order=1)
        self.db.add_all([self.user, self.category])
        self.db.flush()

        self.bare = Product(
            category_id=self.category.id,
            name="Gathering box waffles",
            price=Decimal("5.000"),
            is_active=True,
        )
        self.matcha = Product(
            category_id=self.category.id,
            name="Classic matcha",
            price=Decimal("1.700"),
            is_active=True,
        )
        self.db.add_all([self.bare, self.matcha])
        self.db.flush()
        self.db.add(
            ProductModifier(
                product_id=self.matcha.id,
                group_name="Ota Milk",
                option_name="extra",
                extra_price=Decimal("0.300"),
            )
        )
        self.db.flush()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_product_without_recipe_is_sellable_on_pos(self):
        order = order_service.create_pos_order(
            self.db,
            self.user,
            OrderCreate(
                items=[OrderItemIn(product_id=self.bare.id, quantity=1)],
                customer_name=None,
                customer_phone=None,
                customer_car_plate=None,
                payment_method="cash",
                notes=None,
            ),
        )
        self.assertIsNotNone(order.id)
        self.assertEqual(order.total_amount, Decimal("5.000"))
        self.assertEqual(order.total_cost, Decimal("0"))
        self.assertEqual(order.profit, Decimal("5.000"))
        self.assertEqual(order.items[0].unit_cost, Decimal("0"))

    def test_product_without_recipe_is_sellable_via_device_sync(self):
        order = order_service.create_device_order(
            self.db,
            self.user,
            OrderCreate(
                items=[OrderItemIn(product_id=self.bare.id, quantity=2)],
                customer_name=None,
                customer_phone=None,
                customer_car_plate=None,
                payment_method="cash",
                notes=None,
            ),
            client_uuid=str(uuid4()),
            device_id="test-device",
        )
        self.assertEqual(order.source, "sunmi_device")
        self.assertEqual(order.total_amount, Decimal("10.000"))
        self.assertEqual(order.profit, Decimal("10.000"))

    def test_modifier_surcharge_is_applied_from_server_price(self):
        order = order_service.create_pos_order(
            self.db,
            self.user,
            OrderCreate(
                items=[
                    OrderItemIn(
                        product_id=self.matcha.id,
                        quantity=1,
                        modifiers=[
                            OrderModifierSnapshot(
                                group_name="Ota Milk",
                                option_name="extra",
                                # Client-sent price must be ignored.
                                extra_price=Decimal("9.999"),
                            )
                        ],
                    )
                ],
                customer_name=None,
                customer_phone=None,
                customer_car_plate=None,
                payment_method="cash",
                notes=None,
            ),
        )
        self.assertEqual(order.total_amount, Decimal("2.000"))
        self.assertEqual(order.items[0].unit_price, Decimal("2.000"))

    def test_unknown_modifier_is_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            order_service.create_pos_order(
                self.db,
                self.user,
                OrderCreate(
                    items=[
                        OrderItemIn(
                            product_id=self.matcha.id,
                            quantity=1,
                            modifiers=[
                                OrderModifierSnapshot(
                                    group_name="Nope",
                                    option_name="Nope",
                                    extra_price=Decimal("0"),
                                )
                            ],
                        )
                    ],
                    customer_name=None,
                    customer_phone=None,
                    customer_car_plate=None,
                    payment_method="cash",
                    notes=None,
                ),
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_cancel_and_delete_cancelled_order(self):
        order = order_service.create_pos_order(
            self.db,
            self.user,
            OrderCreate(
                items=[OrderItemIn(product_id=self.bare.id, quantity=1)],
                customer_name=None,
                customer_phone=None,
                customer_car_plate=None,
                payment_method="cash",
                notes=None,
            ),
        )
        order_id = order.id
        for item in order.items:
            item.line_status = "cancelled"
        order_service.recompute_order_totals(self.db, order)
        order.status = "cancelled"
        self.db.flush()

        order_service.delete_cancelled_order(self.db, order)
        self.db.expire_all()
        self.assertIsNone(self.db.get(Order, order_id))

    def test_app_imports_cleanly(self):
        from app.main import app  # noqa: F401
        from app.services import order_service as osvc  # noqa: F401
        from app.services import sync_service  # noqa: F401

        self.assertTrue(callable(osvc.create_pos_order))
        self.assertTrue(callable(sync_service.sync_device_orders))


if __name__ == "__main__":
    unittest.main()
