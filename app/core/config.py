from pathlib import Path
from urllib.parse import quote_plus

from pydantic import AliasChoices, Field
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Always load project-root .env (not cwd) — avoids wrong values when running from another folder.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ALGORITHM: str = "HS256"

    # Evolution / WhatsApp (optional — Phase 3). README: EVOLUTION_API_URL
    evolution_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "EVOLUTION_BASE_URL",
            "EVOLUTION_API_URL",
            "evolution_base_url",
        ),
    )
    evolution_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EVOLUTION_API_KEY", "evolution_api_key"),
    )
    evolution_instance_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EVOLUTION_INSTANCE_NAME", "evolution_instance_name"),
    )

    # WhatsApp: if customers enter local mobile without country code (e.g. 3733xxxx in BH)
    whatsapp_default_country_code: str = Field(
        default="973",
        validation_alias=AliasChoices(
            "WHATSAPP_DEFAULT_COUNTRY_CODE",
            "whatsapp_default_country_code",
        ),
    )
    whatsapp_national_number_length: int = Field(
        default=8,
        validation_alias=AliasChoices(
            "WHATSAPP_NATIONAL_NUMBER_LENGTH",
            "whatsapp_national_number_length",
        ),
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        password = quote_plus(self.DB_PASSWORD)
        return (
            f"mysql+pymysql://{self.DB_USER}:{password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()
