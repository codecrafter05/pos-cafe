"""order customer car plate (drive-thru / pickup identification)

Revision ID: a1c9_car_plate
Revises: f8b4_sunmi_sync
Create Date: 2026-08-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1c9_car_plate"
down_revision: Union[str, None] = "f8b4_sunmi_sync"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("customer_car_plate", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "customer_car_plate")
