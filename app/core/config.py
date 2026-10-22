import os
from functools import lru_cache
from pathlib import Path

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


def normalize_database_url(url: str) -> str:
    """
    Acepta la URL tal como la entregan Render, Neon o Supabase ("postgres://..." o
    "postgresql://...?sslmode=require") y la adapta al driver asyncpg.
    """
    url = url.strip()
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+asyncpg://" + url[len(prefix):]
            break
    if not url.startswith("postgresql+asyncpg://"):
        return url

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    # asyncpg no entiende "sslmode"; su equivalente es "ssl".
    if "sslmode" in query:
        query["ssl"] = query.pop("sslmode")
    query.pop("channel_binding", None)
    return urlunsplit(parts._replace(query=urlencode(query)))


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
    cors_allowed_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,https://autocv.me",
        validation_alias="CORS_ALLOWED_ORIGINS",
    )

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/bautocv",
        validation_alias="DATABASE_URL",
    )
    database_echo: bool = Field(default=False, validation_alias="DATABASE_ECHO")

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        return normalize_database_url(value)

    rendercv_enabled: bool = Field(default=False, validation_alias="RENDERCV_ENABLED")
    rendercv_bin: str = Field(default="rendercv", validation_alias="RENDERCV_BIN")
    rendercv_output_dir: str = Field(
        default="generated_cvs", validation_alias="RENDERCV_OUTPUT_DIR"
    )

    ocr_space_api_key: str | None = Field(
        default=None, validation_alias="OCR_SPACE_API_KEY"
    )
    ocr_space_endpoint: str = Field(
        default="https://api.ocr.space/parse/image",
        validation_alias="OCR_SPACE_ENDPOINT",
    )
    ocr_default_language: str = Field(
        default="spa", validation_alias="OCR_DEFAULT_LANGUAGE"
    )
    ocr_timeout_seconds: float = Field(
        default=30.0, validation_alias="OCR_TIMEOUT_SECONDS"
    )

    gemini_api_key: str | None = Field(
        default=None, validation_alias="GEMINI_API_KEY"
    )
    gemini_model: str = Field(
        default="gemini-1.5-flash", validation_alias="GEMINI_MODEL"
    )
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta",
        validation_alias="GEMINI_BASE_URL",
    )
    gemini_timeout_seconds: float = Field(
        default=20.0, validation_alias="GEMINI_TIMEOUT_SECONDS"
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
        default="v1.2.0", validation_alias="ESCO_SELECTED_VERSION"
    )

    experiment_allow_forced_group: bool = Field(
        default=False, validation_alias="EXPERIMENT_ALLOW_FORCED_GROUP"
    )
    research_api_key: str | None = Field(
        default=None, validation_alias="RESEARCH_API_KEY"
    )

    model_config = SettingsConfigDict(extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
