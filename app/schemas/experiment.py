from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.entities.experiment import EventType


class StartExperimentRequest(BaseModel):
    group: str | None = Field(default=None, pattern="^[AB]$")
    participant_code: str | None = Field(default=None, max_length=120)


class EventCreate(BaseModel):
    event_type: EventType
    detail: str | None = Field(default=None, max_length=2000)
    metadata: dict | None = None


class EventResponse(BaseModel):
    id: int
    session_id: UUID
    event_type: EventType
    detail: str | None
    ts: datetime


class SessionResponse(BaseModel):
    id: UUID
    group: str
    started_at: datetime
    consent_given_at: datetime


class SurveyCreate(BaseModel):
    responses: dict[str, int] = Field(min_length=1)


class ExperimentMetrics(BaseModel):
    sessions: int
    time_to_cv_avg: float | None
    esco_coverage_avg: float | None
    ats_score_avg: float | None
    satisfaction_avg: float | None


class SessionRow(BaseModel):
    id: UUID
    group: str
    started_at: datetime
    exported_at: datetime | None
    time_to_cv_min: float | None
    esco_coverage_pct: float | None
    ats_score: float | None
    satisfaction: float | None
    edits: int


class EventRow(EventResponse):
    group: str