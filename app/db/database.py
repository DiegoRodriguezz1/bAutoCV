from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.entities.base import Base
from app.entities import experiment  # noqa: F401

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def check_db_connection() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _safe_target() -> str:
    """Host, puerto y base de datos de DATABASE_URL, sin usuario ni contraseña."""
    url = engine.url
    return f"{url.host}:{url.port or 5432}/{url.database}"


async def create_database_schema() -> None:
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    except OSError as error:
        raise RuntimeError(
            f"No se pudo conectar a PostgreSQL en {_safe_target()} (APP_ENV={settings.app_env}). "
            "Revisa la variable DATABASE_URL del entorno: en Render debe ser la URL de tu base de datos, "
            "no la de localhost que trae .env.dev."
        ) from error
