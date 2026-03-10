from typing import Any

import httpx

from app.schemas.esco import (
    EscoOccupation,
    EscoOccupationSearchResponse,
    EscoSkill,
    EscoSkillSearchResponse,
)


class EscoService:
    """Service for interacting with ESCO API."""

    BASE_URL = "https://ec.europa.eu/esco/api"

    def __init__(self) -> None:
        self.timeout = httpx.Timeout(10.0)

    async def search_occupations(
        self,
        text: str,
        language: str = "es",
        limit: int = 10,
    ) -> EscoOccupationSearchResponse:
        """
        Search for occupations in ESCO API.

        Args:
            text: Search query text
            language: Language code (es, en, fr, etc.)
            limit: Maximum number of results

        Returns:
            EscoOccupationSearchResponse with matching occupations
        """
        url = f"{self.BASE_URL}/search"
        params = {
            "text": text,
            "language": language,
            "type": "occupation",
            "limit": limit,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                occupations = []
                results = data.get("_embedded", {}).get("results", [])

                for item in results:
                    occupations.append(
                        EscoOccupation(
                            uri=item.get("uri", ""),
                            title=item.get("title", ""),
                            description=item.get("description"),
                            alternative_labels=item.get("alternativeLabels", []),
                        )
                    )

                return EscoOccupationSearchResponse(
                    occupations=occupations,
                    total=data.get("total", 0),
                )

        except httpx.HTTPError as e:
            return EscoOccupationSearchResponse(occupations=[], total=0)

    async def search_skills(
        self,
        text: str,
        language: str = "es",
        limit: int = 10,
    ) -> EscoSkillSearchResponse:
        """
        Search for skills in ESCO API.

        Args:
            text: Search query text
            language: Language code (es, en, fr, etc.)
            limit: Maximum number of results

        Returns:
            EscoSkillSearchResponse with matching skills
        """
        url = f"{self.BASE_URL}/search"
        params = {
            "text": text,
            "language": language,
            "type": "skill",
            "limit": limit,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                skills = []
                results = data.get("_embedded", {}).get("results", [])

                for item in results:
                    skills.append(
                        EscoSkill(
                            uri=item.get("uri", ""),
                            title=item.get("title", ""),
                            description=item.get("description"),
                            skill_type=item.get("skillType"),
                            alternative_labels=item.get("alternativeLabels", []),
                        )
                    )

                return EscoSkillSearchResponse(
                    skills=skills,
                    total=data.get("total", 0),
                )

        except httpx.HTTPError as e:
            return EscoSkillSearchResponse(skills=[], total=0)

    async def get_occupation_details(
        self,
        uri: str,
        language: str = "es",
    ) -> dict[str, Any] | None:
        """
        Get detailed information about a specific occupation.

        Args:
            uri: ESCO URI of the occupation
            language: Language code

        Returns:
            Occupation details or None if not found
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    uri,
                    params={"language": language},
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError:
            return None

    async def get_skill_details(
        self,
        uri: str,
        language: str = "es",
    ) -> dict[str, Any] | None:
        """
        Get detailed information about a specific skill.

        Args:
            uri: ESCO URI of the skill
            language: Language code

        Returns:
            Skill details or None if not found
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    uri,
                    params={"language": language},
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError:
            return None
