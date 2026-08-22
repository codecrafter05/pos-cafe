"""optional raw-material recipes on product modifiers

Revision ID: d5a2_modifier_recipes
Revises: c3e1_item_line_status
Create Date: 2026-08-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5a2_modifier_recipes"
down_revision: Union[str, None] = "c3e1_item_line_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "modifier_recipes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("modifier_id", sa.Integer(), nullable=False),
        sa.Column("raw_material_id", sa.Integer(), nullable=False),
        sa.Column("quantity_used", sa.Numeric(10, 3), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["modifier_id"], ["product_modifiers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["raw_material_id"], ["raw_materials.id"]),
    )
    op.create_index("ix_modifier_recipes_id", "modifier_recipes", ["id"])
    op.create_index("ix_modifier_recipes_modifier_id", "modifier_recipes", ["modifier_id"])
    op.create_index("ix_modifier_recipes_raw_material_id", "modifier_recipes", ["raw_material_id"])


def downgrade() -> None:
    op.drop_index("ix_modifier_recipes_raw_material_id", table_name="modifier_recipes")
    op.drop_index("ix_modifier_recipes_modifier_id", table_name="modifier_recipes")
    op.drop_index("ix_modifier_recipes_id", table_name="modifier_recipes")
    op.drop_table("modifier_recipes")
