import csv
import io
import json
import random
import statistics
from time import monotonic
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.database import get_db_session
from app.entities.experiment import (
    EventLog,
    EventType,
    ExperimentGroup,
    ExperimentSession,
    Section,
    Skill,
    SurveyResponse,
    as_utc,
    utc_now,
)
from app.schemas.experiment import (
    SURVEY_ITEMS,
    AtsBreakdown,
    AtsPreviewRequest,
    AtsResult,
    CvSnapshot,
    EventCreate,
    EventResponse,
    EventRow,
    ExperimentMetrics,
    ExportResult,
    GroupMetrics,
    SessionLiveMetrics,
    SessionResponse,
    SessionRow,
    SessionState,
    SkillCreate,
    SkillResponse,
    StartExperimentRequest,
    SurveyCreate,
)
from app.services.implementations.ats_service import compute_ats

router = APIRouter(prefix="/experiment", tags=["Experiment"])

# Solo estos eventos los puede enviar el cliente; el resto los generan endpoints dedicados.
CLIENT_EVENTS = {EventType.SECTION_ENTER, EventType.SECTION_COMPLETE, EventType.FIELD_EDIT}
FORM_SECTIONS = [Section.PERSONAL, Section.EDUCATION, Section.EXPERIENCE, Section.SKILLS]
FIELD_EDIT_THROTTLE_SECONDS = 2.0
_last_field_edit: dict[tuple[UUID, str], float] = {}


def require_research_key(x_research_key: str | None = Header(default=None)) -> None:
    expected = get_settings().research_api_key
    if expected and x_research_key != expected:
        raise HTTPException(status_code=401, detail="Clave de investigador inválida o ausente")


async def _get_session(db: AsyncSession, session_id: UUID) -> ExperimentSession:
    session = await db.get(ExperimentSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión del experimento no encontrada")
    return session


def _ensure_open(session: ExperimentSession) -> None:
    if session.ended_at is not None:
        raise HTTPException(status_code=409, detail="La sesión ya terminó")


def _log(db: AsyncSession, session: ExperimentSession, event_type: EventType, detail: str | None = None,
         metadata: dict | None = None) -> EventLog:
    event = EventLog(session_id=session.id, event_type=event_type.value, detail=detail, metadata_json=metadata)
    db.add(event)
    return event


async def _active_skills(db: AsyncSession, session_id: UUID) -> list[Skill]:
    result = await db.execute(
        select(Skill).where(Skill.session_id == session_id, Skill.removed_at.is_(None)).order_by(Skill.id)
    )
    return list(result.scalars())


def _coverage(skills: list[Skill]) -> float | None:
    if not skills:
        return None
    return round(sum(1 for skill in skills if skill.esco_uri) / len(skills) * 100, 1)


def _skill_response(skill: Skill) -> SkillResponse:
    return SkillResponse(
        id=skill.id,
        input_label=skill.input_label,
        esco_uri=skill.esco_uri,
        preferred_label=skill.preferred_label,
        source=skill.source,
    )


async def _assign_group(db: AsyncSession) -> str:
    """Aleatorización por bloques: si un grupo se adelanta más de 2 sesiones, va al otro."""
    result = await db.execute(select(ExperimentSession.group, func.count()).group_by(ExperimentSession.group))
    counts = {ExperimentGroup.CONTROL.value: 0, ExperimentGroup.AUTOCV.value: 0, **dict(result.all())}
    a, b = counts[ExperimentGroup.CONTROL.value], counts[ExperimentGroup.AUTOCV.value]
    if abs(a - b) > 2:
        return ExperimentGroup.CONTROL.value if a < b else ExperimentGroup.AUTOCV.value
    return random.choice([ExperimentGroup.CONTROL.value, ExperimentGroup.AUTOCV.value])


@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def start_session(payload: StartExperimentRequest, db: AsyncSession = Depends(get_db_session)) -> SessionResponse:
    if not payload.consent:
        raise HTTPException(status_code=422, detail="Se requiere el consentimiento informado para iniciar")

    if payload.group and get_settings().experiment_allow_forced_group:
        group = payload.group
    else:
        group = await _assign_group(db)

    consent_at = utc_now()
    session = ExperimentSession(
        group=group,
        participant_code=payload.participant_code,
        user_agent=payload.user_agent,
        a11y_prefs=payload.a11y_prefs,
        consent_given_at=consent_at,
        section_times={},
    )
    db.add(session)
    await db.flush()

    db.add(EventLog(session_id=session.id, event_type=EventType.CONSENT_GIVEN.value,
                    detail="ley_1581_2012", ts=consent_at))
    start_at = utc_now()
    session.started_at = start_at
    db.add(EventLog(session_id=session.id, event_type=EventType.SESSION_START.value,
                    detail=f"group={group}", metadata_json={"group": group}, ts=start_at))
    await db.commit()
    return SessionResponse(id=session.id, group=session.group, started_at=session.started_at,
                           consent_given_at=session.consent_given_at)


@router.get("/sessions/{session_id}", response_model=SessionState)
async def get_session_state(session_id: UUID, db: AsyncSession = Depends(get_db_session)) -> SessionState:
    session = await _get_session(db, session_id)
    survey_count = await db.scalar(select(func.count()).where(SurveyResponse.session_id == session_id))
    return SessionState(
        id=session.id,
        group=session.group,
        started_at=session.started_at,
        exported_at=session.exported_at,
        ended_at=session.ended_at,
        section_times=session.section_times or {},
        survey_done=bool(survey_count),
    )


@router.post("/sessions/{session_id}/events", response_model=EventResponse, status_code=201)
async def record_event(
    session_id: UUID,
    payload: EventCreate,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> EventResponse:
    session = await _get_session(db, session_id)
    _ensure_open(session)
    if payload.event_type not in CLIENT_EVENTS:
        raise HTTPException(status_code=400, detail="Este evento lo registra el servidor con su endpoint propio")

    metadata = payload.metadata.model_dump(exclude_none=True, mode="json") if payload.metadata else {}
    detail = payload.detail

    if payload.event_type in {EventType.SECTION_ENTER, EventType.SECTION_COMPLETE}:
        section = metadata.get("section")
        if not section:
            raise HTTPException(status_code=422, detail="metadata.section es obligatorio en eventos de sección")
        detail = section

    if payload.event_type == EventType.SECTION_COMPLETE:
        entered_at = await db.scalar(
            select(func.max(EventLog.ts)).where(
                EventLog.session_id == session.id,
                EventLog.event_type == EventType.SECTION_ENTER.value,
                EventLog.detail == detail,
            )
        )
        if entered_at is None:
            raise HTTPException(status_code=409, detail="No hay un section_enter previo para esta sección")
        seconds = round((utc_now() - as_utc(entered_at)).total_seconds(), 1)
        metadata["seconds"] = seconds
        times = dict(session.section_times or {})
        times[detail] = round(times.get(detail, 0) + seconds, 1)
        session.section_times = times

    if payload.event_type == EventType.FIELD_EDIT:
        field = metadata.get("field") or detail or "unknown"
        key = (session.id, field)
        now = monotonic()
        if now - _last_field_edit.get(key, 0) < FIELD_EDIT_THROTTLE_SECONDS:
            response.status_code = 202
            return EventResponse(id=0, session_id=session.id, event_type=payload.event_type, detail="throttled",
                                 ts=utc_now(), metadata=metadata)
        _last_field_edit[key] = now
        detail = detail or field
        session.edits += 1

    event = _log(db, session, payload.event_type, detail, metadata or None)
    await db.commit()
    return EventResponse(id=event.id, session_id=event.session_id, event_type=payload.event_type,
                         detail=event.detail, ts=event.ts, metadata=event.metadata_json)


@router.get("/sessions/{session_id}/skills", response_model=list[SkillResponse])
async def list_skills(session_id: UUID, db: AsyncSession = Depends(get_db_session)) -> list[SkillResponse]:
    await _get_session(db, session_id)
    return [_skill_response(skill) for skill in await _active_skills(db, session_id)]


@router.post("/sessions/{session_id}/skills", response_model=SkillResponse, status_code=201)
async def add_skill(
    session_id: UUID,
    payload: SkillCreate,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> SkillResponse:
    session = await _get_session(db, session_id)
    _ensure_open(session)
    if payload.esco_uri and session.group == ExperimentGroup.CONTROL.value:
        raise HTTPException(status_code=400, detail="El grupo A (control) no recibe normalización ESCO")

    key = payload.input_label.casefold()
    for existing in await _active_skills(db, session_id):
        if existing.input_label.casefold() == key:
            response.status_code = 200
            return _skill_response(existing)

    now = utc_now()
    skill = Skill(
        session_id=session.id,
        input_label=payload.input_label,
        esco_uri=payload.esco_uri,
        preferred_label=payload.preferred_label if payload.esco_uri else None,
        source=payload.source.value,
        normalized_at=now if payload.esco_uri else None,
    )
    db.add(skill)
    _log(db, session, EventType.SKILL_ADDED, payload.input_label, {"source": payload.source.value})
    if payload.esco_uri:
        _log(db, session, EventType.SKILL_NORMALIZED, f"{payload.input_label} → {payload.preferred_label or ''}",
             {"esco_uri": payload.esco_uri, "preferred_label": payload.preferred_label})
    await db.commit()
    return _skill_response(skill)


@router.delete("/sessions/{session_id}/skills/{skill_id}", status_code=204)
async def remove_skill(session_id: UUID, skill_id: int, db: AsyncSession = Depends(get_db_session)) -> Response:
    session = await _get_session(db, session_id)
    _ensure_open(session)
    skill = await db.get(Skill, skill_id)
    if skill is None or skill.session_id != session.id or skill.removed_at is not None:
        raise HTTPException(status_code=404, detail="Habilidad no encontrada")
    skill.removed_at = utc_now()
    session.edits += 1
    _log(db, session, EventType.FIELD_EDIT, "skills", {"field": "skills", "action": "remove",
                                                       "label": skill.input_label})
    await db.commit()
    return Response(status_code=204)


@router.get("/sessions/{session_id}/metrics", response_model=SessionLiveMetrics)
async def session_metrics(session_id: UUID, db: AsyncSession = Depends(get_db_session)) -> SessionLiveMetrics:
    session = await _get_session(db, session_id)
    skills = await _active_skills(db, session_id)
    end = as_utc(session.exported_at) if session.exported_at else utc_now()
    return SessionLiveMetrics(
        elapsed_min=round((end - as_utc(session.started_at)).total_seconds() / 60, 2),
        section_times=session.section_times or {},
        esco_coverage_pct=_coverage(skills),
        skills_count=len(skills),
        edits=session.edits,
    )


@router.post("/ats/preview", response_model=AtsResult)
async def ats_preview(payload: AtsPreviewRequest) -> AtsResult:
    return compute_ats(payload, payload.esco_coverage_pct)


@router.post("/sessions/{session_id}/export", response_model=ExportResult)
async def export_cv(session_id: UUID, payload: CvSnapshot, db: AsyncSession = Depends(get_db_session)) -> ExportResult:
    session = await _get_session(db, session_id)
    _ensure_open(session)

    if session.exported_at is not None:
        # Solo la primera exportación fija TimeToCV; las siguientes quedan como repetición.
        _log(db, session, EventType.CV_EXPORT, "repeat", {"repeat": True})
        await db.commit()
        return ExportResult(
            time_to_cv_min=session.time_to_cv_min,
            esco_coverage_pct=session.esco_coverage_pct,
            ats_score=session.ats_score,
            ats_breakdown=AtsBreakdown(**session.ats_breakdown) if session.ats_breakdown else None,
            section_times=session.section_times or {},
            repeat=True,
        )

    coverage = _coverage(await _active_skills(db, session_id))
    ats = compute_ats(payload, coverage or 0)
    exported_at = utc_now()
    session.exported_at = exported_at
    session.time_to_cv_min = round((exported_at - as_utc(session.started_at)).total_seconds() / 60, 2)
    session.esco_coverage_pct = coverage if coverage is not None else 0.0
    session.ats_score = ats.ats_score
    session.ats_breakdown = ats.ats_breakdown.model_dump()

    _log(db, session, EventType.ATS_SCORED, f"puntaje={ats.ats_score}", ats.ats_breakdown.model_dump())
    db.add(EventLog(session_id=session.id, event_type=EventType.CV_EXPORT.value,
                    detail=f"TimeToCV={session.time_to_cv_min} min", ts=exported_at,
                    metadata_json={"time_to_cv_min": session.time_to_cv_min}))
    await db.commit()
    return ExportResult(
        time_to_cv_min=session.time_to_cv_min,
        esco_coverage_pct=session.esco_coverage_pct,
        ats_score=session.ats_score,
        ats_breakdown=ats.ats_breakdown,
        section_times=session.section_times or {},
    )


@router.post("/sessions/{session_id}/survey", status_code=201)
async def save_survey(session_id: UUID, payload: SurveyCreate, db: AsyncSession = Depends(get_db_session)) -> dict[str, float]:
    session = await _get_session(db, session_id)
    _ensure_open(session)
    already = await db.scalar(select(func.count()).where(SurveyResponse.session_id == session.id))
    if already:
        raise HTTPException(status_code=409, detail="La encuesta ya fue enviada")

    for answer in sorted(payload.responses, key=lambda item: item.item):
        db.add(SurveyResponse(session_id=session.id, item=answer.item, question=SURVEY_ITEMS[answer.item],
                              score=answer.score))
    scores = [answer.score for answer in sorted(payload.responses, key=lambda item: item.item)]
    session.satisfaction = round(sum(scores) / len(scores), 2)
    _log(db, session, EventType.SURVEY_SUBMITTED, f"promedio={session.satisfaction} {scores}",
         {"scores": scores, "average": session.satisfaction})
    await db.commit()
    return {"satisfaction": session.satisfaction}


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: UUID, db: AsyncSession = Depends(get_db_session)) -> dict[str, str]:
    session = await _get_session(db, session_id)
    _ensure_open(session)
    session.ended_at = utc_now()
    abandoned = session.exported_at is None
    _log(db, session, EventType.SESSION_END, "abandoned" if abandoned else "completed",
         {"abandoned": abandoned})
    await db.commit()
    return {"ended_at": session.ended_at.isoformat()}


def _mean(values: list[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    return round(statistics.fmean(clean), 2) if clean else None


def _group_metrics(sessions: list[ExperimentSession]) -> GroupMetrics:
    done = [session for session in sessions if session.exported_at is not None]
    times = [session.time_to_cv_min for session in done if session.time_to_cv_min is not None]
    return GroupMetrics(
        n=len(done),
        time_to_cv_avg=_mean(times),
        time_to_cv_sd=round(statistics.stdev(times), 2) if len(times) > 1 else None,
        esco_coverage_avg=_mean([session.esco_coverage_pct for session in done]),
        ats_score_avg=_mean([session.ats_score for session in done]),
        satisfaction_avg=_mean([session.satisfaction for session in done]),
        edits_avg=_mean([session.edits for session in done]),
        section_seconds_avg={
            section.value: _mean([(session.section_times or {}).get(section.value) for session in done])
            for section in FORM_SECTIONS
        },
    )


@router.get("/metrics", response_model=ExperimentMetrics, dependencies=[Depends(require_research_key)])
async def get_metrics(db: AsyncSession = Depends(get_db_session)) -> ExperimentMetrics:
    sessions = list((await db.execute(select(ExperimentSession))).scalars())
    events = await db.scalar(select(func.count()).select_from(EventLog))
    return ExperimentMetrics(
        sessions_started=len(sessions),
        sessions_completed=sum(1 for session in sessions if session.exported_at is not None),
        events=events or 0,
        by_group={
            group.value: _group_metrics([session for session in sessions if session.group == group.value])
            for group in ExperimentGroup
        },
    )


def _session_row(session: ExperimentSession) -> SessionRow:
    return SessionRow(
        id=session.id,
        group=session.group,
        started_at=session.started_at,
        exported_at=session.exported_at,
        ended_at=session.ended_at,
        time_to_cv_min=session.time_to_cv_min,
        esco_coverage_pct=session.esco_coverage_pct,
        ats_score=session.ats_score,
        satisfaction=session.satisfaction,
        edits=session.edits,
        section_times=session.section_times or {},
    )


@router.get("/sessions", response_model=list[SessionRow], dependencies=[Depends(require_research_key)])
async def list_sessions(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    group: str | None = Query(default=None, pattern="^[AB]$"),
    db: AsyncSession = Depends(get_db_session),
) -> list[SessionRow]:
    query = select(ExperimentSession).order_by(ExperimentSession.started_at.desc()).limit(limit).offset(offset)
    if group:
        query = query.where(ExperimentSession.group == group)
    return [_session_row(session) for session in (await db.execute(query)).scalars()]


@router.get("/events", response_model=list[EventRow], dependencies=[Depends(require_research_key)])
async def list_events(
    session_id: UUID | None = None,
    limit: int = Query(default=500, ge=1, le=5000),
    db: AsyncSession = Depends(get_db_session),
) -> list[EventRow]:
    query = (
        select(EventLog, ExperimentSession.group)
        .join(ExperimentSession, ExperimentSession.id == EventLog.session_id)
        .order_by(EventLog.ts.desc(), EventLog.id.desc())
        .limit(limit)
    )
    if session_id:
        query = query.where(EventLog.session_id == session_id)
    return [
        EventRow(id=event.id, session_id=event.session_id, group=group, event_type=EventType(event.event_type),
                 detail=event.detail, ts=event.ts, metadata=event.metadata_json)
        for event, group in (await db.execute(query)).all()
    ]


def _iso(value) -> str:
    return as_utc(value).isoformat() if value else ""


async def _csv_rows(resource: str, db: AsyncSession) -> tuple[list[str], list[list]]:
    if resource == "sessions":
        header = ["session_id", "group", "started_at", "exported_at", "ended_at", "time_to_cv_min",
                  "esco_coverage_pct", "ats_score", *[f"ats_{key}" for key in "SPHECF"], "satisfaction", "edits",
                  *[f"sec_{section.value}_s" for section in FORM_SECTIONS], "user_agent", "a11y_prefs"]
        rows = []
        for session in (await db.execute(select(ExperimentSession).order_by(ExperimentSession.started_at))).scalars():
            breakdown = session.ats_breakdown or {}
            times = session.section_times or {}
            rows.append([
                session.id, session.group, _iso(session.started_at), _iso(session.exported_at),
                _iso(session.ended_at), session.time_to_cv_min, session.esco_coverage_pct, session.ats_score,
                *[breakdown.get(key, "") for key in "SPHECF"], session.satisfaction, session.edits,
                *[times.get(section.value, "") for section in FORM_SECTIONS], session.user_agent or "",
                json.dumps(session.a11y_prefs, ensure_ascii=False) if session.a11y_prefs else "",
            ])
        return header, rows

    if resource == "events":
        header = ["event_id", "session_id", "group", "ts", "event_type", "detail", "metadata"]
        result = await db.execute(
            select(EventLog, ExperimentSession.group)
            .join(ExperimentSession, ExperimentSession.id == EventLog.session_id)
            .order_by(EventLog.ts, EventLog.id)
        )
        rows = [[event.id, event.session_id, group, _iso(event.ts), event.event_type, event.detail or "",
                 json.dumps(event.metadata_json, ensure_ascii=False) if event.metadata_json else ""]
                for event, group in result.all()]
        return header, rows

    if resource == "skills":
        header = ["skill_id", "session_id", "group", "input_label", "esco_uri", "preferred_label", "source",
                  "created_at", "normalized_at", "removed_at"]
        result = await db.execute(
            select(Skill, ExperimentSession.group)
            .join(ExperimentSession, ExperimentSession.id == Skill.session_id)
            .order_by(Skill.id)
        )
        rows = [[skill.id, skill.session_id, group, skill.input_label, skill.esco_uri or "",
                 skill.preferred_label or "", skill.source, _iso(skill.created_at), _iso(skill.normalized_at),
                 _iso(skill.removed_at)] for skill, group in result.all()]
        return header, rows

    header = ["session_id", "group", "item", "question", "score", "created_at"]
    result = await db.execute(
        select(SurveyResponse, ExperimentSession.group)
        .join(ExperimentSession, ExperimentSession.id == SurveyResponse.session_id)
        .order_by(SurveyResponse.session_id, SurveyResponse.item)
    )
    rows = [[answer.session_id, group, answer.item, answer.question, answer.score, _iso(answer.created_at)]
            for answer, group in result.all()]
    return header, rows


@router.get("/export/{resource}.csv", dependencies=[Depends(require_research_key)])
async def export_csv(resource: str, db: AsyncSession = Depends(get_db_session)) -> StreamingResponse:
    if resource not in {"sessions", "events", "skills", "survey"}:
        raise HTTPException(status_code=404, detail="Recurso de exportación desconocido")

    header, rows = await _csv_rows(resource, db)
    output = io.StringIO()
    output.write("﻿")  # BOM para que Excel lea bien las tildes
    writer = csv.writer(output)
    writer.writerow(header)
    writer.writerows(rows)
    return StreamingResponse(
        iter([output.getvalue().encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={resource}.csv"},
    )
