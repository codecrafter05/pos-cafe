"""per-item waste / cancel (line_status + movement link)

Revision ID: c3e1_item_line_status
Revises: b2d8_refresh_tokens
Create Date: 2026-08-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3e1_item_line_status"
down_revision: Union[str, None] = "b2d8_refresh_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "order_items",
        sa.Column(
            "line_status",
            sa.String(length=20),
            nullable=False,
            server_default="sold",
        ),
    )
    op.add_column(
        "inventory_movements",
        sa.Column("order_item_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_inventory_movements_order_item_id"),
        "inventory_movements",
        ["order_item_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_inventory_movements_order_item_id",
        "inventory_movements",
        "order_items",
        ["order_item_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_inventory_movements_order_item_id",
        "inventory_movements",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_inventory_movements_order_item_id"),
        table_name="inventory_movements",
    )
    op.drop_column("inventory_movements", "order_item_id")
    op.drop_column("order_items", "line_status")
