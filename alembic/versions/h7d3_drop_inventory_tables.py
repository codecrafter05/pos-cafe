"""drop inventory / recipe / purchases tables (pure POS)

Revision ID: h7d3_drop_inventory
Revises: g1c2_sync_rejections
Create Date: 2026-10-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h7d3_drop_inventory"
down_revision: Union[str, None] = "g1c2_sync_rejections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Child tables first (FK dependents).
    op.drop_table("modifier_recipes")
    op.drop_table("product_recipes")
    op.drop_table("inventory_movements")
    op.drop_table("purchases")
    op.drop_table("raw_materials")


def downgrade() -> None:
    """Recreate empty inventory tables (no data restore)."""
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

    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_material_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(10, 3), nullable=False),
        sa.Column("total_cost", sa.Numeric(10, 3), nullable=False),
        sa.Column("purchased_at", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["raw_material_id"], ["raw_materials.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchases_id"), "purchases", ["id"], unique=False)

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_material_id", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(length=30), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("order_item_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["raw_material_id"], ["raw_materials.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inventory_movements_id"), "inventory_movements", ["id"], unique=False)
    op.create_index(
        op.f("ix_inventory_movements_order_id"), "inventory_movements", ["order_id"], unique=False
    )
    op.create_index(
        op.f("ix_inventory_movements_order_item_id"),
        "inventory_movements",
        ["order_item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_movements_raw_material_id"),
        "inventory_movements",
        ["raw_material_id"],
        unique=False,
    )

    op.create_table(
        "product_recipes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("raw_material_id", sa.Integer(), nullable=False),
        sa.Column("quantity_used", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["raw_material_id"], ["raw_materials.id"]),
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
        "modifier_recipes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("modifier_id", sa.Integer(), nullable=False),
        sa.Column("raw_material_id", sa.Integer(), nullable=False),
        sa.Column("quantity_used", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("substitutes_raw_material_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["modifier_id"], ["product_modifiers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["raw_material_id"], ["raw_materials.id"]),
        sa.ForeignKeyConstraint(["substitutes_raw_material_id"], ["raw_materials.id"]),
    )
    op.create_index("ix_modifier_recipes_id", "modifier_recipes", ["id"])
    op.create_index("ix_modifier_recipes_modifier_id", "modifier_recipes", ["modifier_id"])
    op.create_index("ix_modifier_recipes_raw_material_id", "modifier_recipes", ["raw_material_id"])
    op.create_index(
        "ix_modifier_recipes_substitutes_raw_material_id",
        "modifier_recipes",
        ["substitutes_raw_material_id"],
    )
