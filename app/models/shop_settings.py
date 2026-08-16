from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

SETTINGS_ROW_ID = 1
DEFAULT_CAFE_NAME = "My Cafe"


class ShopSettings(Base):
    __tablename__ = "shop_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cafe_name: Mapped[str] = mapped_column(String(150), nullable=False, default=DEFAULT_CAFE_NAME)
    phone_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_qr_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
