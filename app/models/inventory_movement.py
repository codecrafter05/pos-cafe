from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.raw_material import RawMaterial


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    raw_material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("raw_materials.id"), nullable=False, index=True
    )
    movement_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # purchase | sale_deduction | manual_adjustment | waste
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    order_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    raw_material: Mapped["RawMaterial"] = relationship("RawMaterial", back_populates="movements")
    order: Mapped["Order | None"] = relationship("Order", back_populates="inventory_movements")
