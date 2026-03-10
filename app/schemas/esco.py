from typing import Any

from pydantic import BaseModel, Field


class EscoOccupation(BaseModel):
    """Single occupation result from ESCO API."""

    uri: str = Field(..., description="ESCO URI identifier")
    title: str = Field(..., description="Occupation title")
    description: str | None = Field(default=None, description="Occupation description")
    alternative_labels: list[str] = Field(default_factory=list, description="Alternative names")


class EscoSkill(BaseModel):
    """Single skill result from ESCO API."""

    uri: str = Field(..., description="ESCO URI identifier")
    title: str = Field(..., description="Skill title")
    description: str | None = Field(default=None, description="Skill description")
    skill_type: str | None = Field(default=None, description="Type of skill")
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
