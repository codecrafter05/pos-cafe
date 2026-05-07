"""phase 2: purchases table

Revision ID: d4e2_phase2
Revises: c8f1_phase1_pos
Create Date: 2026-05-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e2_phase2"
down_revision: Union[str, None] = "c8f1_phase1_pos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_index(op.f("ix_purchases_id"), table_name="purchases")
    op.drop_table("purchases")
