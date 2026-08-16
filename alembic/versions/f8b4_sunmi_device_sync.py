"""sunmi device sync: order client_uuid + device_id

Revision ID: f8b4_sunmi_sync
Revises: e7a3_shop_settings
Create Date: 2026-08-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f8b4_sunmi_sync"
down_revision: Union[str, None] = "e7a3_shop_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("client_uuid", sa.String(length=36), nullable=True))
    op.add_column("orders", sa.Column("device_id", sa.String(length=64), nullable=True))
    op.create_index("ix_orders_client_uuid", "orders", ["client_uuid"], unique=True)
    op.create_index("ix_orders_device_id", "orders", ["device_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_orders_device_id", table_name="orders")
    op.drop_index("ix_orders_client_uuid", table_name="orders")
    op.drop_column("orders", "device_id")
    op.drop_column("orders", "client_uuid")
