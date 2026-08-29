from pydantic import BaseModel, ConfigDict, Field

from app.core.time import UtcDateTime


class ShopSettingsUpdate(BaseModel):
    cafe_name: str = Field(..., max_length=150)
    phone_number: str | None = Field(None, max_length=40)


class ShopSettingsOut(BaseModel):
    id: int
    cafe_name: str
    phone_number: str | None
    logo_url: str | None
    payment_qr_url: str | None
    created_at: UtcDateTime
    updated_at: UtcDateTime

    model_config = ConfigDict(from_attributes=True)
