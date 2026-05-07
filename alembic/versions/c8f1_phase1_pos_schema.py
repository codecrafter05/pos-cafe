"""phase 1 POS schema: menu, inventory, orders, user roles

Revision ID: c8f1_phase1_pos
Revises: bfdba3781ae2
Create Date: 2026-05-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8f1_phase1_pos"
down_revision: Union[str, None] = "bfdba3781ae2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("name_ar", sa.String(length=100), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_categories_id"), "categories", ["id"], unique=False)

    op.create_table(
        "raw_materials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("current_stock", sa.Numeric(10, 3), server_default="0", nullable=False),
        sa.Column("min_stock_alert", sa.Numeric(10, 3), server_default="0", nullable=False),
        sa.Column("cost_per_unit", sa.Numeric(10, 3), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_raw_materials_id"), "raw_materials", ["id"], unique=False)

    op.add_column("users", sa.Column("name", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("username", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("role", sa.String(length=20), nullable=True))

    op.execute(
        "UPDATE users SET name = COALESCE(name, 'Administrator'), "
        "username = COALESCE(username, email), "
        "role = COALESCE(role, 'owner')"
    )

    op.alter_column("users", "name", existing_type=sa.String(length=100), nullable=False)
    op.alter_column("users", "username", existing_type=sa.String(length=50), nullable=False)
    op.alter_column("users", "role", existing_type=sa.String(length=20), nullable=False)

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_column("users", "email")
    op.execute("ALTER TABLE users CHANGE hashed_password password_hash VARCHAR(255) NOT NULL")
    op.drop_column("users", "updated_at")
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("name_ar", sa.String(length=150), nullable=True),
        sa.Column("price", sa.Numeric(10, 3), nullable=False),
        sa.Column("cost_price", sa.Numeric(10, 3), server_default="0", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_category_id"), "products", ["category_id"], unique=False)
    op.create_index(op.f("ix_products_id"), "products", ["id"], unique=False)

    op.create_table(
        "product_modifiers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("group_name", sa.String(length=100), nullable=False),
        sa.Column("option_name", sa.String(length=100), nullable=False),
        sa.Column("extra_price", sa.Numeric(10, 3), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_product_modifiers_id"), "product_modifiers", ["id"], unique=False)

    op.create_table(
        "product_recipes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("raw_material_id", sa.Integer(), nullable=False),
        sa.Column("quantity_used", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["raw_material_id"],
            ["raw_materials.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_product_recipes_id"), "product_recipes", ["id"], unique=False)
    op.create_index(
        op.f("ix_product_recipes_raw_material_id"),
        "product_recipes",
        ["raw_material_id"],
        unique=False,
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("customer_name", sa.String(length=100), nullable=True),
        sa.Column("customer_phone", sa.String(length=20), nullable=True),
        sa.Column("total_amount", sa.Numeric(10, 3), nullable=False),
        sa.Column("total_cost", sa.Numeric(10, 3), server_default="0", nullable=False),
        sa.Column("profit", sa.Numeric(10, 3), server_default="0", nullable=False),
        sa.Column("payment_method", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=20), server_default="pos", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="delivered", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_id"), "orders", ["id"], unique=False)
    op.create_index(op.f("ix_orders_user_id"), "orders", ["user_id"], unique=False)

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(10, 3), server_default="0", nullable=False),
        sa.Column("modifiers_snapshot", sa.JSON(), nullable=True),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_items_id"), "order_items", ["id"], unique=False)

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_material_id", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(length=30), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["raw_material_id"],
            ["raw_materials.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inventory_movements_id"), "inventory_movements", ["id"], unique=False)
    op.create_index(
        op.f("ix_inventory_movements_order_id"),
        "inventory_movements",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_movements_raw_material_id"),
        "inventory_movements",
        ["raw_material_id"],
        unique=False,
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade would require restoring the legacy users schema; "
        "restore from backup or recreate DB if needed."
    )
