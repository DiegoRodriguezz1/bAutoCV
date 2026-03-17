from typing import Any

from fastapi import APIRouter, Query

from app.schemas.esco import (
    EscoDescriptionAssistantRequest,
    EscoDescriptionAssistantResponse,
    EscoOccupationSearchResponse,
    EscoOccupationSkillsResponse,
    EscoSkillSearchResponse,
)
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


@router.get("/occupations/suggest", response_model=EscoOccupationSearchResponse)
async def suggest_occupations(
    text: str = Query(..., description="Autocomplete text", min_length=2),
    language: str = Query(default="es", description="Language code (es, en, fr, etc.)"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum results"),
) -> EscoOccupationSearchResponse:
    """Fast occupation autocomplete using ESCO suggest2."""
    return await esco_service.autocomplete_occupations(text=text, language=language, limit=limit)


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


@router.get("/occupations/skills", response_model=EscoOccupationSkillsResponse)
async def get_occupation_skills(
    occupation_uri: str = Query(..., description="ESCO URI of the occupation"),
    language: str = Query(default="es", description="Language code"),
    limit: int = Query(default=20, ge=1, le=50, description="Maximum results per skill group"),
) -> EscoOccupationSkillsResponse:
    """Load the selected occupation with essential and optional skills."""
    response = await esco_service.get_occupation_skills(
        occupation_uri=occupation_uri,
        language=language,
        limit=limit,
    )
    if response is None:
        return EscoOccupationSkillsResponse(
            occupation={"uri": occupation_uri, "title": "", "description": None, "alternative_labels": []},
            essential_skills=[],
            optional_skills=[],
        )
    return response


@router.post("/occupations/description-assistant", response_model=EscoDescriptionAssistantResponse)
async def build_description_assistant(
    payload: EscoDescriptionAssistantRequest,
) -> EscoDescriptionAssistantResponse:
    """Suggest summary, highlights and a RenderCV YAML fragment from ESCO data."""
    response = await esco_service.build_description_assistant(payload)
    if response is None:
        return EscoDescriptionAssistantResponse(
            occupation={"uri": payload.occupation_uri, "title": "", "description": None, "alternative_labels": []},
            selected_skills=[],
            essential_skills=[],
            optional_skills=[],
            suggested_summary="",
            suggested_highlights=[],
            suggested_skills_section=[],
            suggested_cv_patch={},
            suggested_yaml_fragment="",
        )
    return response


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
