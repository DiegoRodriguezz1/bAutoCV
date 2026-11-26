import pytest

YAML_OK = "cv:\n  name: Ana Pérez\n  email: ana@example.com\ndesign:\n  theme: classic\n"


@pytest.mark.asyncio
async def test_crud_saved_cv(client):
    created = await client.post("/cv/saved", json={"name": "  CV de Ana ", "yaml_content": YAML_OK})
    assert created.status_code == 201, created.text
    cv_id = created.json()["id"]
    assert created.json()["name"] == "CV de Ana"

    listed = await client.get("/cv/saved")
    assert any(item["id"] == cv_id and "yaml_content" not in item for item in listed.json())

    updated_yaml = YAML_OK.replace("Ana Pérez", "Ana María Pérez")
    updated = await client.put(f"/cv/saved/{cv_id}", json={"name": "CV de Ana", "yaml_content": updated_yaml})
    assert updated.status_code == 200, updated.text

    fetched = await client.get(f"/cv/saved/{cv_id}")
    assert fetched.json()["yaml_content"] == updated_yaml

    assert (await client.delete(f"/cv/saved/{cv_id}")).status_code == 204
    assert (await client.get(f"/cv/saved/{cv_id}")).status_code == 404


@pytest.mark.asyncio
async def test_rejects_broken_yaml_with_line(client):
    broken = 'cv:\n  name: Ana\n  sections:\n    X:\n      - end_date: "2026-05\n        location: Colombia\n'
    response = await client.post("/cv/saved", json={"name": "Roto", "yaml_content": broken})
    assert response.status_code == 422
    assert "Revisa la línea 5: tiene una comilla sin cerrar" in response.json()["detail"]


@pytest.mark.asyncio
async def test_requires_cv_root(client):
    response = await client.post("/cv/saved", json={"name": "Sin cv", "yaml_content": "design:\n  theme: classic\n"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_name_conflict(client):
    first = await client.post("/cv/saved", json={"name": "Duplicado", "yaml_content": YAML_OK})
    assert first.status_code == 201
    second = await client.post("/cv/saved", json={"name": "Duplicado", "yaml_content": YAML_OK})
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_render_explains_broken_yaml_before_rendercv(client):
    broken = 'cv:\n  name: Ana\n  sections:\n    X:\n      - end_date: "2026-05\n        location: Colombia\n'
    response = await client.post("/cv/render", json={"profile_yaml": broken})
    assert response.status_code == 200
    assert response.json()["accepted"] is False
    assert response.json()["message"].startswith("Revisa la línea 5: tiene una comilla sin cerrar")


def test_syntax_error_without_quotes_names_the_line():
    from app.services.implementations.yaml_errors import yaml_syntax_error

    assert yaml_syntax_error(YAML_OK) is None
    message = yaml_syntax_error("cv:\n  name: Ana\n   email: ana@example.com\n")
    assert message is not None and "línea 3" in message
