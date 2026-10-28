"""Pruebas del creador de hojas de vida (RenderCV).

- Las pruebas unitarias revisan cómo se arma el YAML a partir de lo que envía el frontend.
- Las marcadas con `rendercv` generan el PDF de verdad con datos difíciles, para encontrar
  entradas que hagan fallar a RenderCV. Se omiten si RenderCV no está instalado.
"""

import shutil
from copy import deepcopy

import pytest
import yaml
from pydantic import ValidationError

from app.schemas.cv import RenderCvRequest
from app.services.implementations.rendercv_service import RenderCvService


def front_payload(**cv_overrides) -> dict:
    """Misma forma que produce `mapCVDataToCvRequest` en el frontend (dto/cv-api.ts)."""
    cv = {
        "name": "Ana María Pérez Gómez",
        "headline": "Desarrolladora web",
        "location": "Bogotá D.C., Colombia",
        "email": "ana.perez@correo.com",
        "phone": "+57 3001234567",
        "sections": {
            "Sobre mí": ["Tecnóloga en desarrollo de software con experiencia en aplicaciones web"],
            "Educación": [
                {
                    "institution": "Escuela Tecnológica Instituto Técnico Central (ETITC)",
                    "area": "Tecnología en Desarrollo de Software",
                    "start_date": "2023-02",
                    "end_date": "present",
                    "location": "Bogotá D.C., Colombia",
                    "highlights": [],
                }
            ],
            "Experiencia": [
                {
                    "company": "Acme S.A.S.",
                    "position": "Desarrolladora web",
                    "start_date": "2024-01",
                    "end_date": "2025-06",
                    "location": "Bogotá D.C., Colombia",
                    "summary": "Desarrollo de un portal de empleo en React.",
                    "highlights": ["Desarrollé un portal de empleo en React", "Reduje en 30 % el tiempo de carga"],
                }
            ],
            "Habilidades": [
                {"label": "Competencia técnica", "details": "Python"},
                {"label": "Competencia técnica", "details": "Trabajo en equipo"},
            ],
        },
    }
    cv.update(cv_overrides)
    return {
        "cv": cv,
        "design": {"theme": "classic"},
        "locale": {"language": "spanish"},
        "settings": {"current_date": "2026-10-28"},
        "output_name": "prueba_cv",
    }


def build(payload: dict) -> dict:
    return RenderCvService._build_document(RenderCvRequest(**payload))


# ---------------------------------------------------------------- unitarias (rápidas)


class TestThemes:
    @pytest.mark.parametrize(
        ("sent", "expected"),
        [("classic", "classic"), ("modern", "moderncv"), ("casual", "sb2nov"), ("Modern", "moderncv"),
         ("engineeringresumes", "engineeringresumes"), ("harvard", "harvard")],
    )
    def test_friendly_names_map_to_rendercv_built_in_themes(self, sent, expected):
        payload = front_payload()
        payload["design"] = {"theme": sent}
        assert build(payload)["design"]["theme"] == expected

    def test_unknown_theme_is_rejected_before_calling_rendercv(self):
        payload = front_payload()
        payload["design"] = {"theme": "futurista"}
        with pytest.raises(ValidationError, match="Tema de CV desconocido"):
            RenderCvRequest(**payload)


class TestContactCleanup:
    @pytest.mark.parametrize("email", ["", "   ", "sin-arroba.com", "ana@", "ana@correo", "ana@correo.c"])
    def test_invalid_email_is_dropped(self, email):
        assert "email" not in build(front_payload(email=email))["cv"]

    def test_valid_email_is_trimmed(self):
        assert build(front_payload(email="  ana+cv@correo.com.co "))["cv"]["email"] == "ana+cv@correo.com.co"

    @pytest.mark.parametrize("phone", ["", "123", "+57 12"])
    def test_short_phone_is_dropped(self, phone):
        assert "phone" not in build(front_payload(phone=phone))["cv"]

    @pytest.mark.parametrize(
        ("sent", "expected"),
        [(" +57 300 123 4567 ", "+57 300 1234567"), ("3001234567", "+57 300 1234567"), ("+34 612 345 678", "+34 612 34 56 78")],
    )
    def test_phone_is_normalized_to_international_format(self, sent, expected):
        assert build(front_payload(phone=sent))["cv"]["phone"] == expected

    def test_phone_that_is_not_a_real_number_is_dropped(self):
        assert "phone" not in build(front_payload(phone="+57 1234567890123"))["cv"]

    def test_blank_optional_fields_are_removed(self):
        cv = build(front_payload(headline="  ", location="", email=["", " "]))["cv"]
        assert "headline" not in cv
        assert "location" not in cv
        assert "email" not in cv

    def test_headline_and_location_are_trimmed(self):
        cv = build(front_payload(headline="  Desarrolladora  ", location=" Cali "))["cv"]
        assert cv["headline"] == "Desarrolladora"
        assert cv["location"] == "Cali"


class TestYaml:
    def test_yaml_keeps_spanish_characters(self):
        service = RenderCvService()
        generated = service.generate_yaml(RenderCvRequest(**front_payload(name="Ñandú Íñiguez Ortúzar"))).generated_yaml
        assert "Ñandú Íñiguez Ortúzar" in generated
        assert yaml.safe_load(generated)["cv"]["name"] == "Ñandú Íñiguez Ortúzar"

    def test_profile_yaml_is_passed_through(self):
        raw = "cv:\n  name: Ana\n"
        result = RenderCvService().generate_yaml(RenderCvRequest(profile_yaml=raw))
        assert result.generated_yaml == raw
        assert result.document == {"cv": {"name": "Ana"}}

    def test_request_without_cv_or_yaml_is_rejected(self):
        with pytest.raises(ValidationError):
            RenderCvRequest(design={"theme": "classic"})


# ------------------------------------------------- integración (genera el PDF real)

rendercv_available = shutil.which("rendercv") is not None or RenderCvService()._resolve_rendercv_bin("rendercv") != "rendercv"
needs_rendercv = pytest.mark.skipif(not rendercv_available, reason="RenderCV no está instalado")

DIFFICULT_CASES = {
    "minimo_solo_nombre": dict(headline="", location="", email="", phone=""),
    "acentos_y_enie": dict(
        name="José Ñúñez Íñiguez",
        location="Bogotá, Cundinamarca",
    ),
    "caracteres_especiales": dict(
        headline="Dev C# & .NET — 100% remoto",
        sections={
            "Sobre mí": ["Salario esperado $5.000.000 #remoto 50% R&D_team <b>negrita</b> {llaves} [corchetes] \\ barra"],
            "Habilidades": [
                {"label": "Competencia técnica", "details": "C#, C++ & .NET"},
                {"label": "Competencia técnica", "details": "*Scrum* _ágil_ `git`"},
            ],
        },
    ),
    "emojis": dict(sections={"Sobre mí": ["Me encanta programar 🚀💻 y aprender ✅"]}),
    "texto_muy_largo": dict(
        sections={
            "Sobre mí": ["Desarrolladora apasionada por la accesibilidad. " * 60],
            "Experiencia": [
                {
                    "company": "Empresa con un nombre extremadamente largo para probar el ajuste de línea S.A.S.",
                    "position": "Cargo " * 15,
                    "start_date": "2020-01",
                    "end_date": "present",
                    "highlights": [f"Logro número {i} con bastante detalle para ocupar espacio" for i in range(25)],
                }
            ],
        },
    ),
    "fechas_solo_anio_y_actual": dict(
        sections={
            "Experiencia": [
                {"company": "Acme", "position": "Dev", "start_date": "2021", "end_date": "present"},
                {"company": "Beta", "position": "Practicante", "date": "2020"},
            ],
        },
    ),
    "fecha_fin_antes_de_inicio": dict(
        sections={
            "Experiencia": [{"company": "Acme", "position": "Dev", "start_date": "2025-06", "end_date": "2023-01"}],
        },
    ),
    "fecha_mal_escrita": dict(
        sections={
            "Experiencia": [{"company": "Acme", "position": "Dev", "start_date": "enero 2024", "end_date": "ayer"}],
        },
    ),
    "telefono_extranjero": dict(phone="+34 612 345 678"),
    "telefono_sin_indicativo": dict(phone="3001234567"),
    "listas_vacias": dict(
        sections={
            "Sobre mí": ["Perfil corto."],
            "Experiencia": [{"company": "Acme", "position": "Dev", "start_date": "2024-01", "end_date": "present", "highlights": []}],
            "Habilidades": [{"label": "Competencia técnica", "details": "Excel"}],
        },
    ),
    "seccion_vacia": dict(sections={"Sobre mí": ["Perfil."], "Habilidades": []}),
}


def merge_case(overrides: dict) -> dict:
    payload = front_payload()
    cv_overrides = deepcopy(overrides)
    sections = cv_overrides.pop("sections", None)
    payload["cv"].update(cv_overrides)
    if sections is not None:
        payload["cv"]["sections"].update(sections)
    return payload


async def render(payload: dict):
    return await RenderCvService().render(RenderCvRequest(**payload))


@pytest.mark.rendercv
@needs_rendercv
@pytest.mark.asyncio
@pytest.mark.parametrize("theme", ["classic", "modern", "casual"])
async def test_every_frontend_theme_renders_a_pdf(theme):
    payload = front_payload()
    payload["design"] = {"theme": theme}
    result = await render(payload)
    assert result.accepted, result.message
    assert result.pdf_base64 and result.pdf_base64.startswith("JVBER")  # "%PDF" en base64


@pytest.mark.rendercv
@needs_rendercv
@pytest.mark.asyncio
@pytest.mark.parametrize("case", list(DIFFICULT_CASES))
async def test_difficult_data_still_renders_a_pdf(case):
    result = await render(merge_case(DIFFICULT_CASES[case]))
    assert result.accepted, f"{case}: {result.message}"
    assert result.pdf_base64 and result.pdf_base64.startswith("JVBER")
