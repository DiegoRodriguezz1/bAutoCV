import csv
import io
import random
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.entities.experiment import (
    EventLog,
    EventType,
    ExperimentGroup,
    ExperimentSession,
    Skill,
    SurveyResponse,
)
from app.schemas.experiment import (
    EventCreate,
    EventResponse,
    EventRow,
    ExperimentMetrics,
    SessionResponse,
    SessionRow,
    StartExperimentRequest,
    SurveyCreate,
)

router = APIRouter(prefix="/experiment", tags=["Experiment"])


def _session_or_404(session: ExperimentSession | None) -> ExperimentSession:
    if session is None:
        raise HTTPException(status_code=404, detail="Experiment session not found")
    return session


@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def start_session(
    payload: StartExperimentRequest,
    db: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    group = payload.group or random.choice(list(ExperimentGroup))
    session = ExperimentSession(group=group, participant_code=payload.participant_code)
    db.add(session)
    await db.flush()

    db.add(
        EventLog(
            session_id=session.id,
            event_type=EventType.CONSENT_GIVEN.value,
            detail="experimental_flow",
        )
    )
    db.add(EventLog(session_id=session.id, event_type=EventType.SESSION_START.value, detail=f"group={group}"))
    await db.commit()
    await db.refresh(session)
    return SessionResponse(
        id=session.id,
        group=session.group,
        started_at=session.started_at,
        consent_given_at=session.consent_given_at,
    )


@router.post("/sessions/{session_id}/events", response_model=EventResponse, status_code=201)
async def record_event(
    session_id: UUID,
    payload: EventCreate,
    db: AsyncSession = Depends(get_db_session),
) -> EventResponse:
    session = _session_or_404(await db.get(ExperimentSession, session_id))
    if payload.event_type in {EventType.CONSENT_GIVEN, EventType.SESSION_START}:
        raise HTTPException(status_code=400, detail="This event is recorded when the session starts")

    event = EventLog(
        session_id=session.id,
        event_type=payload.event_type.value,
        detail=payload.detail,
        metadata_json=payload.metadata,
    )
    db.add(event)
    if payload.event_type == EventType.FIELD_EDIT:
        session.edits += 1
    if payload.event_type == EventType.CV_EXPORT:
        session.exported_at = func.now()
    if payload.event_type == EventType.SESSION_END:
        session.ended_at = func.now()
    await db.commit()
    await db.refresh(event)
    return EventResponse(
        id=event.id,
        session_id=event.session_id,
        event_type=EventType(event.event_type),
        detail=event.detail,
        ts=event.ts,
    )


@router.post("/sessions/{session_id}/survey", status_code=201)
async def save_survey(
    session_id: UUID,
    payload: SurveyCreate,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, float]:
    session = _session_or_404(await db.get(ExperimentSession, session_id))
    invalid_scores = [score for score in payload.responses.values() if score < 1 or score > 5]
    if invalid_scores:
        raise HTTPException(status_code=422, detail="Survey scores must be between 1 and 5")

    for question, score in payload.responses.items():
        db.add(SurveyResponse(session_id=session.id, question=question, score=score))
    average = sum(payload.responses.values()) / len(payload.responses)
    session.satisfaction = round(average, 2)
    await db.commit()
    return {"satisfaction": session.satisfaction}


@router.post("/sessions/{session_id}/skills", status_code=201)
async def save_skill(
    session_id: UUID,
    input_label: str,
    esco_uri: str | None = None,
    preferred_label: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, int]:
    session = _session_or_404(await db.get(ExperimentSession, session_id))
    skill = Skill(
        session_id=session.id,
        input_label=input_label,
        esco_uri=esco_uri,
        preferred_label=preferred_label,
    )
    db.add(skill)
    await db.commit()
    return {"id": skill.id}


@router.get("/metrics", response_model=ExperimentMetrics)
async def get_metrics(db: AsyncSession = Depends(get_db_session)) -> ExperimentMetrics:
    result = await db.execute(
        select(
            func.count(ExperimentSession.id),
            func.avg(ExperimentSession.time_to_cv_min),
            func.avg(ExperimentSession.esco_coverage_pct),
            func.avg(ExperimentSession.ats_score),
            func.avg(ExperimentSession.satisfaction),
        )
    )
    sessions, time_to_cv, esco_coverage, ats_score, satisfaction = result.one()
    return ExperimentMetrics(
        sessions=sessions,
        time_to_cv_avg=time_to_cv,
        esco_coverage_avg=esco_coverage,
        ats_score_avg=ats_score,
        satisfaction_avg=satisfaction,
    )


@router.get("/sessions", response_model=list[SessionRow])
async def list_sessions(db: AsyncSession = Depends(get_db_session)) -> list[SessionRow]:
    result = await db.execute(select(ExperimentSession).order_by(ExperimentSession.started_at.desc()))
    return [
        SessionRow(
            id=session.id,
            group=session.group,
            started_at=session.started_at,
            exported_at=session.exported_at,
            time_to_cv_min=session.time_to_cv_min,
            esco_coverage_pct=session.esco_coverage_pct,
            ats_score=session.ats_score,
            satisfaction=session.satisfaction,
            edits=session.edits,
        )
        for session in result.scalars()
    ]


@router.get("/events", response_model=list[EventRow])
async def list_events(db: AsyncSession = Depends(get_db_session)) -> list[EventRow]:
    result = await db.execute(
        select(EventLog, ExperimentSession.group)
        .join(ExperimentSession, ExperimentSession.id == EventLog.session_id)
        .order_by(EventLog.ts.desc())
        .limit(500)
    )
    return [
        EventRow(
            id=event.id,
            session_id=event.session_id,
            group=group,
            event_type=EventType(event.event_type),
            detail=event.detail,
            ts=event.ts,
        )
        for event, group in result.all()
    ]


@router.get("/export/{resource}.csv")
async def export_csv(resource: str, db: AsyncSession = Depends(get_db_session)) -> StreamingResponse:
    if resource not in {"sessions", "events"}:
        raise HTTPException(status_code=404, detail="Unknown export resource")

    output = io.StringIO()
    writer = csv.writer(output)
    if resource == "sessions":
        rows = await list_sessions(db)
        writer.writerow(SessionRow.model_fields.keys())
        writer.writerows(row.model_dump().values() for row in rows)
    else:
        rows = await list_events(db)
        writer.writerow(EventRow.model_fields.keys())
        writer.writerows(row.model_dump().values() for row in rows)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={resource}.csv"},
    )