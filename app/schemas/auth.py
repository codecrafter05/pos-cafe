from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str
    # Handheld POS devices stay signed in across shifts. The web admin keeps
    # the shorter default (ACCESS_TOKEN_EXPIRE_MINUTES, 8 hours).
    client: Literal["web", "device"] = "web"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    name: str
    username: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
