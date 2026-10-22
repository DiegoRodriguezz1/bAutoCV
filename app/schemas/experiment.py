from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field, field_validator

from app.entities.experiment import EventType, Section, SkillSource, as_utc

# SQLite devuelve fechas sin zona; se marcan como UTC para que el navegador no las lea como hora local.
UtcDatetime = Annotated[datetime, AfterValidator(as_utc)]

SURVEY_ITEMS: dict[int, str] = {
    1: "El CV final representa bien mi perfil",
    2: "El proceso fue fácil de completar",
    3: "Usaría la herramienta para postularme",
    4: "Confío en que el CV pasa filtros ATS",
}

ESCO_SKILL_URI_PREFIX = "http://data.europa.eu/esco/skill/"


class StartExperimentRequest(BaseModel):
    consent: bool
    group: str | None = Field(default=None, pattern="^[AB]$")
    participant_code: str | None = Field(default=None, max_length=120)
    user_agent: str | None = Field(default=None, max_length=500)
    a11y_prefs: dict | None = None


class SessionResponse(BaseModel):
    id: UUID
    group: str
    started_at: UtcDatetime
    consent_given_at: UtcDatetime


class SessionState(BaseModel):
    id: UUID
    group: str
    started_at: UtcDatetime
    exported_at: UtcDatetime | None
    ended_at: UtcDatetime | None
    section_times: dict[str, float]
    survey_done: bool


ClientEventType = Literal["section_enter", "section_complete", "field_edit"]


class EventMetadata(BaseModel):
    section: Section | None = None
    field: str | None = Field(default=None, max_length=120)

    model_config = {"extra": "allow"}


class EventCreate(BaseModel):
    event_type: EventType
    detail: str | None = Field(default=None, max_length=2000)
    metadata: EventMetadata | None = None


class EventResponse(BaseModel):
    id: int
    session_id: UUID
    event_type: EventType
    detail: str | None
    ts: UtcDatetime
    metadata: dict | None = None


class EventRow(EventResponse):
    group: str


class SkillCreate(BaseModel):
    input_label: str = Field(min_length=1, max_length=200)
    esco_uri: str | None = Field(default=None, max_length=500)
    preferred_label: str | None = Field(default=None, max_length=300)
    source: SkillSource = SkillSource.MANUAL

    @field_validator("input_label")
    @classmethod
    def strip_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("La habilidad no puede estar vacía")
        return value

    @field_validator("esco_uri")
    @classmethod
    def validate_uri(cls, value: str | None) -> str | None:
        if value and not value.startswith(ESCO_SKILL_URI_PREFIX):
            raise ValueError(f"La URI ESCO debe empezar por {ESCO_SKILL_URI_PREFIX}")
        return value or None


class SkillResponse(BaseModel):
    id: int
    input_label: str
    esco_uri: str | None
    preferred_label: str | None
    source: str


class CvSnapshotEducation(BaseModel):
    degree: str = ""
    institution: str = ""
    period: str = ""


class CvSnapshotExperience(BaseModel):
    position: str = ""
    company: str = ""
    period: str = ""


class CvSnapshot(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    summary: str = ""
    education: list[CvSnapshotEducation] = Field(default_factory=list)
    experience: list[CvSnapshotExperience] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class AtsPreviewRequest(CvSnapshot):
    esco_coverage_pct: float = Field(default=0, ge=0, le=100)


class AtsBreakdown(BaseModel):
    S: float
    P: float
    H: float
    E: float
    C: float
    F: float


class AtsResult(BaseModel):
    ats_score: int
    ats_breakdown: AtsBreakdown


class ExportResult(BaseModel):
    time_to_cv_min: float | None
    esco_coverage_pct: float | None
    ats_score: float | None
    ats_breakdown: AtsBreakdown | None
    section_times: dict[str, float]
    repeat: bool = False


class SurveyItem(BaseModel):
    item: int = Field(ge=1, le=4)
    score: int = Field(ge=1, le=5)


class SurveyCreate(BaseModel):
    responses: list[SurveyItem] = Field(min_length=4, max_length=4)

    @field_validator("responses")
    @classmethod
    def all_items(cls, value: list[SurveyItem]) -> list[SurveyItem]:
        if sorted(item.item for item in value) != [1, 2, 3, 4]:
            raise ValueError("La encuesta debe responder los ítems 1, 2, 3 y 4 una sola vez")
        return value


class SessionLiveMetrics(BaseModel):
    elapsed_min: float
    section_times: dict[str, float]
    esco_coverage_pct: float | None
    skills_count: int
    edits: int


class GroupMetrics(BaseModel):
    n: int
    time_to_cv_avg: float | None
    time_to_cv_sd: float | None
    esco_coverage_avg: float | None
    ats_score_avg: float | None
    satisfaction_avg: float | None
    edits_avg: float | None
    section_seconds_avg: dict[str, float | None]


class MetricTargets(BaseModel):
    time_to_cv_b_max: float = 30
    esco_coverage_b_min: float = 80
    ats_min: float = 75
    satisfaction_min: float = 4.0


class ExperimentMetrics(BaseModel):
    sessions_started: int
    sessions_completed: int
    events: int
    by_group: dict[str, GroupMetrics]
    targets: MetricTargets = Field(default_factory=MetricTargets)


class SessionRow(BaseModel):
    id: UUID
    group: str
    started_at: UtcDatetime
    exported_at: UtcDatetime | None
    ended_at: UtcDatetime | None
    time_to_cv_min: float | None
    esco_coverage_pct: float | None
    ats_score: float | None
    satisfaction: float | None
    edits: int
    section_times: dict[str, float]
