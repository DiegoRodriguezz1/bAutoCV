import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


def _load_environment_file() -> str:
    app_env = os.getenv("APP_ENV", "dev").lower()
    env_file = ROOT_DIR / f".env.{app_env}"
    if env_file.exists():
        load_dotenv(env_file, override=False)
    return app_env


ACTIVE_ENV = _load_environment_file()


class Settings(BaseSettings):
    app_name: str = Field(default="bAutoCV API", validation_alias="APP_NAME")
    app_description: str = Field(
        default="Backend service for CV automation workflows.",
        validation_alias="APP_DESCRIPTION",
    )
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")
    app_env: str = Field(default=ACTIVE_ENV, validation_alias="APP_ENV")

    api_v1_prefix: str = Field(default="/api/v1", validation_alias="API_V1_PREFIX")
    docs_url: str = Field(default="/docs", validation_alias="DOCS_URL")
    redoc_url: str = Field(default="/redoc", validation_alias="REDOC_URL")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/bautocv",
        validation_alias="DATABASE_URL",
    )
    database_echo: bool = Field(default=False, validation_alias="DATABASE_ECHO")

    rendercv_enabled: bool = Field(default=False, validation_alias="RENDERCV_ENABLED")
    rendercv_bin: str = Field(default="rendercv", validation_alias="RENDERCV_BIN")
    rendercv_output_dir: str = Field(
        default="generated_cvs", validation_alias="RENDERCV_OUTPUT_DIR"
    )

    esco_base_url: str = Field(
        default="https://ec.europa.eu/esco/api", validation_alias="ESCO_BASE_URL"
    )
    esco_timeout_seconds: float = Field(
        default=10.0, validation_alias="ESCO_TIMEOUT_SECONDS"
    )
    esco_cache_ttl_seconds: int = Field(
        default=900, validation_alias="ESCO_CACHE_TTL_SECONDS"
    )
    esco_cache_max_entries: int = Field(
        default=512, validation_alias="ESCO_CACHE_MAX_ENTRIES"
    )
    esco_selected_version: str | None = Field(
        default=None, validation_alias="ESCO_SELECTED_VERSION"
    )

    model_config = SettingsConfigDict(extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
