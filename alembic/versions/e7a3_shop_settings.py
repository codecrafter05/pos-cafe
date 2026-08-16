"""shop settings single-row table

Revision ID: e7a3_shop_settings
Revises: d4e2_phase2
Create Date: 2026-08-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7a3_shop_settings"
down_revision: Union[str, None] = "d4e2_phase2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shop_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cafe_name", sa.String(length=150), nullable=False),
        sa.Column("phone_number", sa.String(length=40), nullable=True),
        sa.Column("logo_url", sa.String(length=255), nullable=True),
        sa.Column("payment_qr_url", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO shop_settings (id, cafe_name, created_at, updated_at) "
        "VALUES (1, 'My Cafe', UTC_TIMESTAMP(), UTC_TIMESTAMP())"
    )


def downgrade() -> None:
    op.drop_table("shop_settings")
