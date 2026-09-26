from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import to_naive_utc


class SyncRejection(Base):
    """A device order the Sunmi tried to sync and the server refused."""

    __tablename__ = "sync_rejections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    client_uuid: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: to_naive_utc(datetime.now(timezone.utc)),
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    payload_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
