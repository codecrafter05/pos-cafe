"""log rejected Sunmi device order sync attempts

Revision ID: g1c2_sync_rejections
Revises: e6b3_mod_recipe_sub
Create Date: 2026-09-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g1c2_sync_rejections"
down_revision: Union[str, None] = "e6b3_mod_recipe_sub"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sync_rejections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("client_uuid", sa.String(length=36), nullable=False),
        sa.Column("attempted_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("payload_snapshot", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_rejections_device_id", "sync_rejections", ["device_id"])
    op.create_index("ix_sync_rejections_client_uuid", "sync_rejections", ["client_uuid"])
    op.create_index("ix_sync_rejections_attempted_at", "sync_rejections", ["attempted_at"])


def downgrade() -> None:
    op.drop_index("ix_sync_rejections_attempted_at", table_name="sync_rejections")
    op.drop_index("ix_sync_rejections_client_uuid", table_name="sync_rejections")
    op.drop_index("ix_sync_rejections_device_id", table_name="sync_rejections")
    op.drop_table("sync_rejections")
