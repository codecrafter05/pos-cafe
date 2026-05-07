from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.product_modifier import ProductModifier
    from app.models.product_recipe import ProductRecipe


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(150), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=Decimal("0"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    category: Mapped["Category"] = relationship("Category", back_populates="products")
    modifiers: Mapped[list["ProductModifier"]] = relationship(
        "ProductModifier", back_populates="product", cascade="all, delete-orphan"
    )
    recipe_lines: Mapped[list["ProductRecipe"]] = relationship(
        "ProductRecipe", back_populates="product", cascade="all, delete-orphan"
    )
