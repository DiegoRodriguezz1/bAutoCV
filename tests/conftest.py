import os
import tempfile
from pathlib import Path

# La configuración se lee al importar la app, así que la BD de prueba se fija antes.
_DB_FILE = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL_TEST", f"sqlite+aiosqlite:///{_DB_FILE.as_posix()}")
os.environ["DATABASE_ECHO"] = "false"
os.environ["EXPERIMENT_ALLOW_FORCED_GROUP"] = "true"
os.environ["RESEARCH_API_KEY"] = ""

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402

from app.db.database import create_database_schema  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def client():
    await create_database_schema()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test/api/v1") as test_client:
        yield test_client


@pytest.fixture
def cv_snapshot() -> dict:
    return {
        "name": "Ana Pérez",
        "email": "ana@example.com",
        "phone": "3001234567",
        "summary": " ".join(["palabra"] * 50),
        "education": [{"degree": "Tecnología en Desarrollo de Software", "institution": "ETITC", "period": "2023-02 – 2026-06"}],
        "experience": [{"position": "Desarrolladora", "company": "Acme", "period": "2024-01 – actual"}],
        "skills": ["Python", "SQL", "Git", "Scrum", "Docker"],
    }
