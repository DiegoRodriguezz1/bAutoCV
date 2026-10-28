"""Limpia los datos del CV antes de RenderCV, para que una entrada rara no tumbe el PDF.

Casos que hacían fallar el render (ver tests/test_rendercv_service.py):
- Texto con `#palabra` o `$$...$$`: RenderCV los trata como comandos o fórmulas de Typst.
- Fechas en español, con barras o inválidas, y fechas de fin anteriores a las de inicio.
- Teléfonos sin indicativo internacional.
"""

import re
from typing import Any

import phonenumbers

DEFAULT_PHONE_REGION = "CO"
PRESENT = "present"

# Carácter invisible que separa "#" de la palabra siguiente: RenderCV deja de verlo como
# comando de Typst y lo escapa, así que en el PDF se sigue leyendo "#remoto".
_WORD_JOINER = "⁠"
_TYPST_COMMAND = re.compile(r"#(?=[A-Za-z])")
_TYPST_MATH = re.compile(r"\$\$")
# "<b>" se interpretaría como HTML en el Markdown de RenderCV y desaparecería del PDF.
_HTML_TAG_START = re.compile(r"<(?=[A-Za-z/!])")

_PRESENT_WORDS = {"present", "presente", "actual", "actualmente", "hoy", "now", "current", "ahora"}
_MONTHS = {
    "ene": 1, "enero": 1, "jan": 1, "january": 1,
    "feb": 2, "febrero": 2, "february": 2,
    "mar": 3, "marzo": 3, "march": 3,
    "abr": 4, "abril": 4, "apr": 4, "april": 4,
    "may": 5, "mayo": 5,
    "jun": 6, "junio": 6, "june": 6,
    "jul": 7, "julio": 7, "july": 7,
    "ago": 8, "agosto": 8, "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "septiembre": 9, "setiembre": 9, "september": 9,
    "oct": 10, "octubre": 10, "october": 10,
    "nov": 11, "noviembre": 11, "november": 11,
    "dic": 12, "diciembre": 12, "dec": 12, "december": 12,
}

# Campos que no son texto libre: no se tocan (RenderCV los valida con su propio formato).
_NON_TEXT_KEYS = {"email", "phone", "website", "url", "doi", "photo", "start_date", "end_date", "date"}


def neutralize_typst(text: str) -> str:
    text = _TYPST_COMMAND.sub("#" + _WORD_JOINER, text)
    text = _HTML_TAG_START.sub("<" + _WORD_JOINER, text)
    return _TYPST_MATH.sub("$" + _WORD_JOINER + "$", text)


def sanitize_text_fields(value: Any, key: str | None = None) -> Any:
    """Aplica `neutralize_typst` a todo el texto libre, recorriendo listas y diccionarios."""
    if isinstance(value, str):
        return value if key in _NON_TEXT_KEYS else neutralize_typst(value)
    if isinstance(value, list):
        return [sanitize_text_fields(item, key) for item in value]
    if isinstance(value, dict):
        return {k: sanitize_text_fields(v, k) for k, v in value.items()}
    return value


def normalize_date(raw: Any) -> str | None:
    """
    Devuelve una fecha que RenderCV acepta (YYYY, YYYY-MM, YYYY-MM-DD o "present"),
    o None si no se puede interpretar.
    """
    if raw is None:
        return None
    text = str(raw).strip().lower()
    if not text:
        return None
    if text in _PRESENT_WORDS:
        return PRESENT

    if match := re.fullmatch(r"(\d{4})(?:[-/.](\d{1,2}))?(?:[-/.](\d{1,2}))?", text):
        year, month, day = match.groups()
        if month and not 1 <= int(month) <= 12:
            return None
        if day:
            return f"{year}-{int(month):02d}-{int(day):02d}"
        return f"{year}-{int(month):02d}" if month else year

    # 02/2024 o 2-2024
    if match := re.fullmatch(r"(\d{1,2})[-/.](\d{4})", text):
        month, year = match.groups()
        return f"{year}-{int(month):02d}" if 1 <= int(month) <= 12 else None

    # "enero 2024", "ene. de 2024", "january 2024"
    if match := re.fullmatch(r"([a-záéíóú]+)\.?\s+(?:de\s+|del\s+)?(\d{4})", text):
        month_name, year = match.groups()
        month = _MONTHS.get(month_name)
        return f"{year}-{month:02d}" if month else None

    return None


def _sortable(date: str) -> str:
    return "9999-99-99" if date == PRESENT else date


def normalize_entry_dates(entry: dict[str, Any]) -> dict[str, Any]:
    """Corrige start_date/end_date de una entrada; si no se pueden leer, quedan como texto en `date`."""
    if "start_date" not in entry and "end_date" not in entry:
        return entry

    entry = dict(entry)
    raw_start, raw_end = entry.pop("start_date", None), entry.pop("end_date", None)
    start, end = normalize_date(raw_start), normalize_date(raw_end)
    unreadable = (raw_start not in (None, "") and start is None) or (raw_end not in (None, "") and end is None)

    if unreadable:
        # RenderCV acepta texto libre en `date`; así no se pierde lo que escribió la persona.
        parts = [str(part).strip() for part in (raw_start, raw_end) if part not in (None, "")]
        if parts and "date" not in entry:
            entry["date"] = " – ".join(parts)
        return entry

    if start == PRESENT:
        # "actual – 2024" no tiene sentido: lo conocido pasa a inicio y queda en curso.
        start, end = (end if end != PRESENT else None), PRESENT
    if start and end and end != PRESENT and _sortable(end) < _sortable(start):
        start, end = end, start
    if start:
        entry["start_date"] = start
        if end:
            entry["end_date"] = end
    elif end and end != PRESENT:
        entry["date"] = end
    return entry


def normalize_section_dates(sections: dict[str, list[Any]]) -> dict[str, list[Any]]:
    return {
        title: [normalize_entry_dates(entry) if isinstance(entry, dict) else entry for entry in entries]
        for title, entries in sections.items()
    }


def normalize_phone(phone: str, default_region: str = DEFAULT_PHONE_REGION) -> str | None:
    """Formato internacional (+57 300 1234567) o None si el número no es válido."""
    try:
        parsed = phonenumbers.parse(phone, default_region)
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_valid_number(parsed):
        return None
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
