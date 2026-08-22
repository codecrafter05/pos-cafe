from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.product_modifier import ProductModifier
    from app.models.raw_material import RawMaterial


class ModifierRecipe(Base):
    """Optional extra ingredients consumed when a modifier option is selected."""

    __tablename__ = "modifier_recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    modifier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("product_modifiers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    raw_material_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("raw_materials.id"), nullable=False, index=True
    )
    quantity_used: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)

    modifier: Mapped["ProductModifier"] = relationship(
        "ProductModifier", back_populates="recipe_lines"
    )
    raw_material: Mapped["RawMaterial"] = relationship(
        "RawMaterial", back_populates="modifier_recipe_lines"
    )
