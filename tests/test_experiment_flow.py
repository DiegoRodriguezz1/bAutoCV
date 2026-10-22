import asyncio

import pytest

ESCO_URI = "http://data.europa.eu/esco/skill/ccd0a1d9-afda-43d9-b901-96344886e14d"
SECTIONS = ["personal", "education", "experience", "skills"]


async def _start(client, group: str) -> str:
    response = await client.post("/experiment/sessions", json={"consent": True, "group": group})
    assert response.status_code == 201, response.text
    assert response.json()["group"] == group
    return response.json()["id"]


async def _complete_sections(client, session_id: str) -> None:
    for section in SECTIONS:
        enter = await client.post(f"/experiment/sessions/{session_id}/events",
                                  json={"event_type": "section_enter", "metadata": {"section": section}})
        assert enter.status_code == 201, enter.text
        done = await client.post(f"/experiment/sessions/{session_id}/events",
                                 json={"event_type": "section_complete", "metadata": {"section": section}})
        assert done.status_code == 201, done.text
        assert done.json()["metadata"]["seconds"] >= 0


@pytest.mark.asyncio
async def test_consent_is_required(client):
    response = await client.post("/experiment/sessions", json={"consent": False})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_full_flow_group_b(client, cv_snapshot):
    session_id = await _start(client, "B")
    await _complete_sections(client, session_id)

    normalized = await client.post(f"/experiment/sessions/{session_id}/skills", json={
        "input_label": "Python", "esco_uri": ESCO_URI, "preferred_label": "Python (programación informática)",
        "source": "esco_suggestion"})
    assert normalized.status_code == 201
    manual = await client.post(f"/experiment/sessions/{session_id}/skills",
                               json={"input_label": "Liderazgo", "source": "manual"})
    assert manual.status_code == 201
    duplicate = await client.post(f"/experiment/sessions/{session_id}/skills",
                                  json={"input_label": "  python ", "source": "manual"})
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == normalized.json()["id"]

    live = (await client.get(f"/experiment/sessions/{session_id}/metrics")).json()
    assert live["skills_count"] == 2
    assert live["esco_coverage_pct"] == 50.0

    await asyncio.sleep(0.05)
    export = await client.post(f"/experiment/sessions/{session_id}/export", json=cv_snapshot)
    assert export.status_code == 200, export.text
    body = export.json()
    assert body["time_to_cv_min"] >= 0  # redondeado a 2 decimales de minuto, como en el documento
    exported = (await client.get(f"/experiment/sessions/{session_id}")).json()
    assert exported["exported_at"] > exported["started_at"]
    assert body["esco_coverage_pct"] == 50.0
    assert body["ats_score"] == 90  # 100 − 20 · (1 − 0,5)
    assert body["repeat"] is False

    again = (await client.post(f"/experiment/sessions/{session_id}/export", json=cv_snapshot)).json()
    assert again["repeat"] is True
    assert again["time_to_cv_min"] == body["time_to_cv_min"]

    survey = {"responses": [{"item": i, "score": s} for i, s in zip(range(1, 5), [5, 4, 4, 5])]}
    saved = await client.post(f"/experiment/sessions/{session_id}/survey", json=survey)
    assert saved.status_code == 201
    assert saved.json()["satisfaction"] == 4.5
    assert (await client.post(f"/experiment/sessions/{session_id}/survey", json=survey)).status_code == 409

    assert (await client.post(f"/experiment/sessions/{session_id}/end")).status_code == 200
    late = await client.post(f"/experiment/sessions/{session_id}/events",
                             json={"event_type": "field_edit", "metadata": {"field": "personal.name"}})
    assert late.status_code == 409

    events = (await client.get("/experiment/events", params={"session_id": session_id})).json()
    types = [event["event_type"] for event in reversed(events)]
    assert types[:2] == ["consent_given", "session_start"]
    assert types.count("section_complete") == 4
    assert types.count("skill_added") == 2
    assert types.count("skill_normalized") == 1
    assert types.count("ats_scored") == 1
    assert types.count("cv_export") == 2
    assert types[-1] == "session_end"

    state = (await client.get(f"/experiment/sessions/{session_id}")).json()
    assert set(state["section_times"]) == set(SECTIONS)
    assert state["survey_done"] is True


@pytest.mark.asyncio
async def test_group_a_cannot_normalize(client):
    session_id = await _start(client, "A")
    response = await client.post(f"/experiment/sessions/{session_id}/skills", json={
        "input_label": "Python", "esco_uri": ESCO_URI, "source": "esco_suggestion"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_server_only_events_are_rejected(client):
    session_id = await _start(client, "A")
    for event_type in ["cv_export", "ats_scored", "skill_added", "survey_submitted", "session_start"]:
        response = await client.post(f"/experiment/sessions/{session_id}/events", json={"event_type": event_type})
        assert response.status_code == 400, event_type


@pytest.mark.asyncio
async def test_field_edit_is_throttled_and_counted(client):
    session_id = await _start(client, "A")
    url = f"/experiment/sessions/{session_id}/events"
    first = await client.post(url, json={"event_type": "field_edit", "metadata": {"field": "personal.email"}})
    second = await client.post(url, json={"event_type": "field_edit", "metadata": {"field": "personal.email"}})
    other = await client.post(url, json={"event_type": "field_edit", "metadata": {"field": "personal.phone"}})
    assert (first.status_code, second.status_code, other.status_code) == (201, 202, 201)
    live = (await client.get(f"/experiment/sessions/{session_id}/metrics")).json()
    assert live["edits"] == 2


@pytest.mark.asyncio
async def test_skill_removal_is_logical(client):
    session_id = await _start(client, "A")
    skill = (await client.post(f"/experiment/sessions/{session_id}/skills",
                               json={"input_label": "Excel"})).json()
    assert (await client.delete(f"/experiment/sessions/{session_id}/skills/{skill['id']}")).status_code == 204
    assert (await client.get(f"/experiment/sessions/{session_id}/skills")).json() == []
    csv_text = (await client.get("/experiment/export/skills.csv")).text
    assert "Excel" in csv_text


@pytest.mark.asyncio
async def test_metrics_by_group_and_csv(client, cv_snapshot):
    for group in ["A", "B"]:
        session_id = await _start(client, group)
        await _complete_sections(client, session_id)
        await client.post(f"/experiment/sessions/{session_id}/export", json=cv_snapshot)

    metrics = (await client.get("/experiment/metrics")).json()
    assert set(metrics["by_group"]) == {"A", "B"}
    assert metrics["by_group"]["A"]["n"] >= 1
    assert metrics["by_group"]["B"]["section_seconds_avg"]["personal"] is not None
    assert metrics["targets"]["ats_min"] == 75

    for resource in ["sessions", "events", "skills", "survey"]:
        response = await client.get(f"/experiment/export/{resource}.csv")
        assert response.status_code == 200
        assert response.content.startswith("﻿".encode("utf-8"))
    sessions_csv = (await client.get("/experiment/export/sessions.csv")).text
    assert "sec_personal_s" in sessions_csv.splitlines()[0]


@pytest.mark.asyncio
async def test_catalogs(client):
    cities = (await client.get("/catalog/cities", params={"text": "bogota"})).json()
    assert cities[0]["name"] == "Bogotá D.C."
    assert (await client.get("/catalog/cities", params={"country": "AR", "text": "x"})).json() == []
    institutions = (await client.get("/catalog/institutions", params={"text": "etitc"})).json()
    assert "ETITC" in institutions[0]["name"]
