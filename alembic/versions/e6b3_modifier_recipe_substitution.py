"""modifier recipe can replace a base product ingredient

Revision ID: e6b3_mod_recipe_sub
Revises: d5a2_modifier_recipes
Create Date: 2026-08-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6b3_mod_recipe_sub"
down_revision: Union[str, None] = "d5a2_modifier_recipes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "modifier_recipes",
        sa.Column("substitutes_raw_material_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_modifier_recipes_substitutes_raw_material_id",
        "modifier_recipes",
        ["substitutes_raw_material_id"],
    )
    op.create_foreign_key(
        "fk_modifier_recipes_substitutes_raw_material_id",
        "modifier_recipes",
        "raw_materials",
        ["substitutes_raw_material_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_modifier_recipes_substitutes_raw_material_id",
        "modifier_recipes",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_modifier_recipes_substitutes_raw_material_id",
        table_name="modifier_recipes",
    )
    op.drop_column("modifier_recipes", "substitutes_raw_material_id")
