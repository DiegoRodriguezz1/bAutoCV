import json
import unicodedata
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter(prefix="/catalog", tags=["Catalog"])
DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@lru_cache
def _load(name: str) -> list[dict[str, str]]:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def _fold(value: str) -> str:
    """Minúsculas y sin tildes, para que 'bogota' encuentre 'Bogotá'."""
    normalized = unicodedata.normalize("NFD", value.casefold())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").strip()


def _filter(items: list[dict[str, str]], text: str, fields: tuple[str, ...], limit: int) -> list[dict[str, str]]:
    query = _fold(text)
    if not query:
        return items[:limit]
    starts, contains = [], []
    for item in items:
        haystacks = [_fold(item[field]) for field in fields]
        if any(value.startswith(query) for value in haystacks):
            starts.append(item)
        elif any(query in value for value in haystacks):
            contains.append(item)
    return (starts + contains)[:limit]


@router.get("/cities")
async def list_cities(
    country: str = Query(default="CO", min_length=2, max_length=2),
    text: str = Query(default=""),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[dict[str, str]]:
    """Ciudades y municipios principales de Colombia (lista inicial; completar con DIVIPOLA del DANE)."""
    if country.upper() != "CO":
        return []
    return _filter(_load("co_cities.json"), text, ("name", "department"), limit)


@router.get("/institutions")
async def list_institutions(
    text: str = Query(default=""),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[dict[str, str]]:
    """Instituciones de educación superior de Colombia (lista inicial; completar con SNIES)."""
    return _filter(_load("co_institutions.json"), text, ("name",), limit)
