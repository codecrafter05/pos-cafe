from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.time import UtcDateTime


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
    created_at: UtcDateTime

    model_config = ConfigDict(from_attributes=True)


class ModifierIn(BaseModel):
    group_name: str = Field(..., max_length=100)
    option_name: str = Field(..., max_length=100)
    extra_price: Decimal = Decimal("0")


class ModifierOut(BaseModel):
    id: int
    group_name: str
    option_name: str
    extra_price: Decimal = Decimal("0")

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
    created_at: UtcDateTime
    modifiers: list[ModifierOut] = []

    model_config = ConfigDict(from_attributes=True)
