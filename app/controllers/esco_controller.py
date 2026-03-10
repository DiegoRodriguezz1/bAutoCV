from typing import Any

from fastapi import APIRouter, Query

from app.schemas.esco import EscoOccupationSearchResponse, EscoSkillSearchResponse
from app.services.implementations.esco_service import EscoService

router = APIRouter(prefix="/esco", tags=["ESCO"])
esco_service = EscoService()


@router.get("/occupations/search", response_model=EscoOccupationSearchResponse)
async def search_occupations(
    text: str = Query(..., description="Search query text", min_length=2),
    language: str = Query(default="es", description="Language code (es, en, fr, etc.)"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum results"),
) -> EscoOccupationSearchResponse:
    """
    Search occupations in ESCO database.
    
    Example:
    ```
    GET /api/v1/esco/occupations/search?text=desarrollador&language=es&limit=10
    ```
    """
    return await esco_service.search_occupations(text=text, language=language, limit=limit)


@router.get("/skills/search", response_model=EscoSkillSearchResponse)
async def search_skills(
    text: str = Query(..., description="Search query text", min_length=2),
    language: str = Query(default="es", description="Language code (es, en, fr, etc.)"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum results"),
) -> EscoSkillSearchResponse:
    """
    Search skills in ESCO database.
    
    Example:
    ```
    GET /api/v1/esco/skills/search?text=java&language=es&limit=10
    ```
    """
    return await esco_service.search_skills(text=text, language=language, limit=limit)


@router.get("/occupations/details")
async def get_occupation_details(
    uri: str = Query(..., description="ESCO URI of the occupation"),
    language: str = Query(default="es", description="Language code"),
) -> dict[str, Any]:
    """
    Get detailed information about a specific occupation by URI.
    
    Example:
    ```
    GET /api/v1/esco/occupations/details?uri=http://data.europa.eu/esco/occupation/...
    ```
    """
    details = await esco_service.get_occupation_details(uri=uri, language=language)
    if details is None:
        return {"error": "Occupation not found"}
    return details


@router.get("/skills/details")
async def get_skill_details(
    uri: str = Query(..., description="ESCO URI of the skill"),
    language: str = Query(default="es", description="Language code"),
) -> dict[str, Any]:
    """
    Get detailed information about a specific skill by URI.
    
    Example:
    ```
    GET /api/v1/esco/skills/details?uri=http://data.europa.eu/esco/skill/...
    ```
    """
    details = await esco_service.get_skill_details(uri=uri, language=language)
    if details is None:
        return {"error": "Skill not found"}
    return details
