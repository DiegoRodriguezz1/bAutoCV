import asyncio
from time import monotonic
from typing import Any
from urllib.parse import urlencode

import httpx
import yaml

from app.core.config import get_settings
from app.schemas.cv import CvOneLineEntry
from app.schemas.esco import (
    EscoDescriptionAssistantRequest,
    EscoDescriptionAssistantResponse,
    EscoOccupation,
    EscoOccupationSkillsResponse,
    EscoOccupationSearchResponse,
    EscoSkill,
    EscoSkillSearchResponse,
)


class EscoService:
    """Service for interacting with ESCO API."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.esco_base_url.rstrip("/")
        self.timeout = httpx.Timeout(self.settings.esco_timeout_seconds)
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={"Accept": "application/json"},
        )
        self.cache_ttl_seconds = self.settings.esco_cache_ttl_seconds
        self.cache_max_entries = self.settings.esco_cache_max_entries
        self.selected_version = self.settings.esco_selected_version
        self._cache: dict[str, tuple[float, Any]] = {}
        self._cache_lock = asyncio.Lock()

    async def _get_cached(self, key: str) -> Any | None:
        async with self._cache_lock:
            cached = self._cache.get(key)
            if cached is None:
                return None

            expires_at, value = cached
            if expires_at <= monotonic():
                self._cache.pop(key, None)
                return None

            return value

    async def _set_cached(self, key: str, value: Any) -> None:
        async with self._cache_lock:
            if len(self._cache) >= self.cache_max_entries:
                expired_keys = [
                    entry_key
                    for entry_key, (expires_at, _) in self._cache.items()
                    if expires_at <= monotonic()
                ]
                for entry_key in expired_keys:
                    self._cache.pop(entry_key, None)

                while len(self._cache) >= self.cache_max_entries:
                    oldest_key = next(iter(self._cache))
                    self._cache.pop(oldest_key, None)

            self._cache[key] = (monotonic() + self.cache_ttl_seconds, value)

    def _normalize_params(self, params: dict[str, Any]) -> dict[str, Any]:
        normalized = {
            key: value
            for key, value in params.items()
            if value is not None and value != "" and value != []
        }
        if self.selected_version and "selectedVersion" not in normalized:
            normalized["selectedVersion"] = self.selected_version
        return normalized

    async def _get_json(self, path: str, params: dict[str, Any], *, cached: bool = True) -> Any:
        normalized = self._normalize_params(params)
        cache_key = f"{path}?{urlencode(sorted(normalized.items()), doseq=True)}"

        if cached:
            cached_value = await self._get_cached(cache_key)
            if cached_value is not None:
                return cached_value

        response = await self.client.get(f"{self.base_url}{path}", params=normalized)
        response.raise_for_status()
        payload = response.json()

        if cached:
            await self._set_cached(cache_key, payload)

        return payload

    @staticmethod
    def _flatten_label_values(value: Any) -> list[str]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, str)]
        if isinstance(value, dict):
            return [item for item in value.values() if isinstance(item, str)]
        if isinstance(value, str):
            return [value]
        return []

    @classmethod
    def _extract_text(cls, value: Any, language: str) -> str | None:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            text_parts = [item for item in value if isinstance(item, str)]
            return " ".join(text_parts) if text_parts else None
        if isinstance(value, dict):
            preferred_keys = [language, language.lower(), "es", "en", "en-us"]
            for key in preferred_keys:
                text = value.get(key)
                if isinstance(text, str) and text.strip():
                    return text.strip()
            for text in value.values():
                if isinstance(text, str) and text.strip():
                    return text.strip()
        return None

    @classmethod
    def _parse_occupation(cls, item: dict[str, Any], language: str) -> EscoOccupation:
        return EscoOccupation(
            uri=item.get("uri", ""),
            title=item.get("title")
            or cls._extract_text(item.get("preferredLabel"), language)
            or "",
            code=item.get("code"),
            search_hit=item.get("searchHit"),
            description=cls._extract_text(item.get("description"), language)
            or cls._extract_text(item.get("definition"), language),
            alternative_labels=cls._flatten_label_values(
                item.get("alternativeLabels") or item.get("alternativeLabel")
            ),
        )

    @classmethod
    def _parse_skill(cls, item: dict[str, Any], language: str) -> EscoSkill:
        skill_type_value = item.get("skillType")
        if skill_type_value is None:
            has_skill_type = item.get("hasSkillType")
            if isinstance(has_skill_type, list) and has_skill_type:
                skill_type_value = has_skill_type[0].rsplit("/", 1)[-1]

        reuse_level_value = None
        has_reuse_level = item.get("hasReuseLevel")
        if isinstance(has_reuse_level, list) and has_reuse_level:
            reuse_level_value = has_reuse_level[0].rsplit("/", 1)[-1]

        return EscoSkill(
            uri=item.get("uri", ""),
            title=item.get("title")
            or cls._extract_text(item.get("preferredLabel"), language)
            or "",
            description=cls._extract_text(item.get("description"), language)
            or cls._extract_text(item.get("definition"), language),
            skill_type=skill_type_value,
            reuse_level=reuse_level_value,
            alternative_labels=cls._flatten_label_values(
                item.get("alternativeLabels") or item.get("alternativeLabel")
            ),
        )

    async def autocomplete_occupations(
        self,
        text: str,
        language: str = "es",
        limit: int = 10,
    ) -> EscoOccupationSearchResponse:
        params = {
            "text": text,
            "language": language,
            "type": "occupation",
            "limit": limit,
            "alt": "true",
        }

        try:
            data = await self._get_json("/suggest2", params)
            results = data.get("_embedded", {}).get("results", [])
            occupations = [self._parse_occupation(item, language) for item in results]
            return EscoOccupationSearchResponse(occupations=occupations, total=data.get("total", 0))
        except httpx.HTTPError:
            return EscoOccupationSearchResponse(occupations=[], total=0)

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
        params = {
            "text": text,
            "language": language,
            "type": "occupation",
            "limit": limit,
        }

        try:
            data = await self._get_json("/search", params)
            results = data.get("_embedded", {}).get("results", [])
            occupations = [self._parse_occupation(item, language) for item in results]
            return EscoOccupationSearchResponse(
                occupations=occupations,
                total=data.get("total", 0),
            )
        except httpx.HTTPError:
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
        params = {
            "text": text,
            "language": language,
            "type": "skill",
            "limit": limit,
            "alt": "true",
        }

        try:
            data = await self._get_json("/suggest2", params)
            results = data.get("_embedded", {}).get("results", [])
            skills = [self._parse_skill(item, language) for item in results]
            return EscoSkillSearchResponse(skills=skills, total=data.get("total", 0))
        except httpx.HTTPError:
            return EscoSkillSearchResponse(skills=[], total=0)

    async def _get_related_skills(
        self,
        occupation_uri: str,
        relation: str,
        language: str,
        limit: int,
    ) -> list[EscoSkill]:
        data = await self._get_json(
            "/resource/related",
            {
                "uri": occupation_uri,
                "relation": relation,
                "language": language,
                "limit": limit,
            },
        )
        items = data.get("_embedded", {}).get(relation, [])
        return [self._parse_skill(item, language) for item in items]

    async def get_occupation_skills(
        self,
        occupation_uri: str,
        language: str = "es",
        limit: int = 20,
    ) -> EscoOccupationSkillsResponse | None:
        occupation_payload = await self.get_occupation_details(uri=occupation_uri, language=language)
        if occupation_payload is None:
            return None

        try:
            essential_skills, optional_skills = await asyncio.gather(
                self._get_related_skills(occupation_uri, "hasEssentialSkill", language, limit),
                self._get_related_skills(occupation_uri, "hasOptionalSkill", language, limit),
            )
        except httpx.HTTPError:
            essential_skills, optional_skills = [], []

        occupation = self._parse_occupation(occupation_payload, language)
        return EscoOccupationSkillsResponse(
            occupation=occupation,
            essential_skills=essential_skills,
            optional_skills=optional_skills,
        )

    async def _load_selected_skills(
        self,
        skill_uris: list[str],
        language: str,
    ) -> list[EscoSkill]:
        if not skill_uris:
            return []

        tasks = [self.get_skill_details(uri=skill_uri, language=language) for skill_uri in skill_uris]
        details_list = await asyncio.gather(*tasks)
        return [
            self._parse_skill(detail, language)
            for detail in details_list
            if isinstance(detail, dict)
        ]

    @staticmethod
    def _to_sentence_list(values: list[str]) -> str:
        clean_values = [value.strip() for value in values if value and value.strip()]
        if not clean_values:
            return ""
        if len(clean_values) == 1:
            return clean_values[0]
        if len(clean_values) == 2:
            return f"{clean_values[0]} y {clean_values[1]}"
        return f"{', '.join(clean_values[:-1])} y {clean_values[-1]}"

    def _build_summary(
        self,
        occupation: EscoOccupation,
        selected_skills: list[EscoSkill],
        additional_context: list[str],
    ) -> str:
        skill_titles = [skill.title for skill in selected_skills[:5]]
        summary_parts = []

        headline = occupation.title.strip()
        if headline:
            summary_parts.append(
                f"Perfil orientado a {headline.lower()}, con capacidad para traducir requerimientos en entregables concretos y sostenibles."
            )

        if occupation.description:
            summary_parts.append(occupation.description.strip())

        if skill_titles:
            summary_parts.append(
                f"Fortalezas destacadas en {self._to_sentence_list(skill_titles)}."
            )

        if additional_context:
            summary_parts.append(" ".join(context.strip() for context in additional_context if context.strip()))

        return " ".join(part for part in summary_parts if part).strip()

    def _build_highlights(
        self,
        occupation: EscoOccupation,
        selected_skills: list[EscoSkill],
        additional_context: list[str],
    ) -> list[str]:
        highlights = [
            f"Aplicar buenas practicas alineadas con el perfil de {occupation.title.lower()}.",
            "Traducir requerimientos funcionales y tecnicos en tareas implementables y medibles.",
        ]

        for skill in selected_skills[:4]:
            highlights.append(f"Demostrar dominio en {skill.title.lower()} dentro de flujos de trabajo reales.")

        for note in additional_context[:2]:
            cleaned_note = note.strip()
            if cleaned_note:
                highlights.append(cleaned_note)

        return highlights[:6]

    def _build_skills_section(self, selected_skills: list[EscoSkill]) -> list[CvOneLineEntry]:
        if not selected_skills:
            return []

        grouped_titles = self._to_sentence_list([skill.title for skill in selected_skills[:8]])
        return [CvOneLineEntry(label="Competencias ESCO", details=grouped_titles)]

    def _build_cv_patch(
        self,
        occupation: EscoOccupation,
        summary: str,
        highlights: list[str],
        skills_section: list[CvOneLineEntry],
    ) -> dict[str, Any]:
        sections: dict[str, Any] = {
            "Perfil profesional": [summary],
        }
        if highlights:
            sections["Logros o enfoque profesional"] = [
                {"bullet": highlight} for highlight in highlights
            ]
        if skills_section:
            sections["Habilidades clave"] = [entry.model_dump(exclude_none=True) for entry in skills_section]

        patch: dict[str, Any] = {"sections": sections}
        if occupation.title:
            patch["headline"] = occupation.title
        return patch

    async def build_description_assistant(
        self,
        payload: EscoDescriptionAssistantRequest,
    ) -> EscoDescriptionAssistantResponse | None:
        occupation_bundle = await self.get_occupation_skills(
            occupation_uri=payload.occupation_uri,
            language=payload.language,
            limit=payload.skill_limit,
        )
        if occupation_bundle is None:
            return None

        selected_skills = await self._load_selected_skills(
            payload.selected_skill_uris,
            payload.language,
        )
        if not selected_skills:
            selected_skills = occupation_bundle.essential_skills[: min(5, len(occupation_bundle.essential_skills))]

        suggested_summary = self._build_summary(
            occupation_bundle.occupation,
            selected_skills,
            payload.additional_context,
        )
        suggested_highlights = self._build_highlights(
            occupation_bundle.occupation,
            selected_skills,
            payload.additional_context,
        )
        suggested_skills_section = self._build_skills_section(selected_skills)
        suggested_cv_patch = self._build_cv_patch(
            occupation_bundle.occupation,
            suggested_summary,
            suggested_highlights,
            suggested_skills_section,
        )
        suggested_yaml_fragment = yaml.safe_dump(
            suggested_cv_patch,
            allow_unicode=True,
            sort_keys=False,
        )

        return EscoDescriptionAssistantResponse(
            occupation=occupation_bundle.occupation,
            selected_skills=selected_skills,
            essential_skills=occupation_bundle.essential_skills,
            optional_skills=occupation_bundle.optional_skills,
            suggested_headline=occupation_bundle.occupation.title,
            suggested_summary=suggested_summary,
            suggested_highlights=suggested_highlights,
            suggested_skills_section=suggested_skills_section,
            suggested_cv_patch=suggested_cv_patch,
            suggested_yaml_fragment=suggested_yaml_fragment,
        )

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
            return await self._get_json(
                "/resource/occupation",
                {"uri": uri, "language": language},
            )
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
            return await self._get_json(
                "/resource/skill",
                {"uri": uri, "language": language},
            )
        except httpx.HTTPError:
            return None
