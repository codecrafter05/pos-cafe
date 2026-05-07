from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    name: str
    name_ar: str | None = None
    sort_order: int = 0
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = None
    name_ar: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryOut(CategoryBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModifierIn(BaseModel):
    group_name: str = Field(..., max_length=100)
    option_name: str = Field(..., max_length=100)
    extra_price: Decimal = Decimal("0")


class ModifierOut(ModifierIn):
    id: int
    model_config = ConfigDict(from_attributes=True)


class RawMaterialBase(BaseModel):
    name: str
    unit: str
    current_stock: Decimal = Decimal("0")
    min_stock_alert: Decimal = Decimal("0")
    cost_per_unit: Decimal = Decimal("0")


class RawMaterialCreate(RawMaterialBase):
    pass


class RawMaterialUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None
    min_stock_alert: Decimal | None = None
    cost_per_unit: Decimal | None = None


class RawMaterialOut(RawMaterialBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecipeLineIn(BaseModel):
    raw_material_id: int
    quantity_used: Decimal
    unit: str


class RecipeLineOut(RecipeLineIn):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    category_id: int
    name: str
    name_ar: str | None = None
    price: Decimal
    description: str | None = None
    image_url: str | None = None
    is_active: bool = True
    sort_order: int = 0


class ProductCreate(ProductBase):
    modifiers: list[ModifierIn] = []


class ProductUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = None
    name_ar: str | None = None
    price: Decimal | None = None
    description: str | None = None
    image_url: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None
    modifiers: list[ModifierIn] | None = None


class ProductOut(ProductBase):
    id: int
    cost_price: Decimal
    created_at: datetime
    modifiers: list[ModifierOut] = []
    recipe: list[RecipeLineOut] = []

    model_config = ConfigDict(from_attributes=True)


class RecipeReplaceRequest(BaseModel):
    lines: list[RecipeLineIn]


class ManualStockAdjustRequest(BaseModel):
    quantity_delta: Decimal
    notes: str | None = None
