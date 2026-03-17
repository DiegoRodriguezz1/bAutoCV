from typing import Any

from pydantic import BaseModel, Field

from app.schemas.cv import CvOneLineEntry


class EscoOccupation(BaseModel):
    """Single occupation result from ESCO API."""

    uri: str = Field(..., description="ESCO URI identifier")
    title: str = Field(..., description="Occupation title")
    code: str | None = Field(default=None, description="ESCO/ISCO code when available")
    search_hit: str | None = Field(default=None, description="Matched label from ESCO search")
    description: str | None = Field(default=None, description="Occupation description")
    alternative_labels: list[str] = Field(default_factory=list, description="Alternative names")


class EscoSkill(BaseModel):
    """Single skill result from ESCO API."""

    uri: str = Field(..., description="ESCO URI identifier")
    title: str = Field(..., description="Skill title")
    description: str | None = Field(default=None, description="Skill description")
    skill_type: str | None = Field(default=None, description="Type of skill")
    reuse_level: str | None = Field(default=None, description="ESCO skill reuse level")
    alternative_labels: list[str] = Field(default_factory=list, description="Alternative names")


class EscoSearchResponse(BaseModel):
    """Generic ESCO search response."""

    results: list[dict[str, Any]] = Field(default_factory=list)
    total: int = Field(default=0, description="Total results found")


class EscoOccupationSearchResponse(BaseModel):
    """Response for occupation search."""

    occupations: list[EscoOccupation] = Field(default_factory=list)
    total: int = Field(default=0)


class EscoSkillSearchResponse(BaseModel):
    """Response for skill search."""

    skills: list[EscoSkill] = Field(default_factory=list)
    total: int = Field(default=0)


class EscoOccupationSkillsResponse(BaseModel):
    """Occupation with essential and optional skills."""

    occupation: EscoOccupation
    essential_skills: list[EscoSkill] = Field(default_factory=list)
    optional_skills: list[EscoSkill] = Field(default_factory=list)


class EscoDescriptionAssistantRequest(BaseModel):
    occupation_uri: str = Field(..., description="Selected ESCO occupation URI")
    selected_skill_uris: list[str] = Field(
        default_factory=list,
        description="ESCO skill URIs selected by the user",
    )
    language: str = Field(default="es", description="Language code")
    additional_context: list[str] = Field(
        default_factory=list,
        description="Optional user notes to weave into the description suggestions",
    )
    skill_limit: int = Field(
        default=12,
        ge=1,
        le=50,
        description="Maximum essential and optional skills to retrieve for the occupation",
    )


class EscoDescriptionAssistantResponse(BaseModel):
    occupation: EscoOccupation
    selected_skills: list[EscoSkill] = Field(default_factory=list)
    essential_skills: list[EscoSkill] = Field(default_factory=list)
    optional_skills: list[EscoSkill] = Field(default_factory=list)
    suggested_headline: str | None = Field(default=None)
    suggested_summary: str = Field(..., description="Suggested professional summary")
    suggested_highlights: list[str] = Field(default_factory=list)
    suggested_skills_section: list[CvOneLineEntry] = Field(default_factory=list)
    suggested_cv_patch: dict[str, Any] = Field(
        default_factory=dict,
        description="Partial RenderCV 'cv' payload ready to merge into the YAML",
    )
    suggested_yaml_fragment: str = Field(
        ...,
        description="YAML fragment containing headline and suggested sections",
    )
