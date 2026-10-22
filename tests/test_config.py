from app.core.config import normalize_database_url


def test_render_style_urls_use_asyncpg():
    assert normalize_database_url("postgres://u:p@h:5432/db") == "postgresql+asyncpg://u:p@h:5432/db"
    assert normalize_database_url("postgresql://u:p@h/db") == "postgresql+asyncpg://u:p@h/db"


def test_sslmode_becomes_ssl_for_asyncpg():
    url = normalize_database_url("postgresql://u:p@h/db?sslmode=require&channel_binding=require")
    assert url == "postgresql+asyncpg://u:p@h/db?ssl=require"


def test_other_urls_are_left_alone():
    assert normalize_database_url("postgresql+asyncpg://u:p@h/db") == "postgresql+asyncpg://u:p@h/db"
    assert normalize_database_url("sqlite+aiosqlite:///x.db") == "sqlite+aiosqlite:///x.db"
