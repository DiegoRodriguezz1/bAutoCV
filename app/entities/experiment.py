from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import Base


class ExperimentGroup(StrEnum):
    CONTROL = "A"
    AUTOCV = "B"


class EventType(StrEnum):
    CONSENT_GIVEN = "consent_given"
    SESSION_START = "session_start"
    SECTION_ENTER = "section_enter"
    FIELD_EDIT = "field_edit"
    SECTION_COMPLETE = "section_complete"
    SKILL_ADDED = "skill_added"
    SKILL_NORMALIZED = "skill_normalized"
    ATS_SCORED = "ats_scored"
    CV_EXPORT = "cv_export"
    SURVEY_SUBMITTED = "survey_submitted"
    SESSION_END = "session_end"


class ExperimentSession(Base):
    __tablename__ = "EXPERIMENT_SESSION"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    participant_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    group: Mapped[str] = mapped_column(String(1), nullable=False)
    consent_given_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_to_cv_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    esco_coverage_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    ats_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    satisfaction: Mapped[float | None] = mapped_column(Float, nullable=True)
    edits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class EventLog(Base):
    __tablename__ = "EVENT_LOG"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("EXPERIMENT_SESSION.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Skill(Base):
    __tablename__ = "SKILL"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("EXPERIMENT_SESSION.id", ondelete="CASCADE"), nullable=False
    )
    input_label: Mapped[str] = mapped_column(String(200), nullable=False)
    esco_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preferred_label: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SurveyResponse(Base):
    __tablename__ = "SURVEY_RESPONSE"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("EXPERIMENT_SESSION.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(String(300), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApplicationStatus(Base):
    __tablename__ = "APPLICATION_STATUS"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("EXPERIMENT_SESSION.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())