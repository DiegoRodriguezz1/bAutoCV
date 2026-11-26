"""Mensajes legibles para YAML mal formado, antes de guardarlo o pasarlo a RenderCV.

RenderCV responde a estos errores con una tabla dibujada con caracteres que no cabe en
pantalla, y PyYAML suele señalar la línea donde se rindió, no donde está el error.
"""

import yaml


def _unclosed_quote_line(content: str) -> int | None:
    """Primera línea con comillas dobles impares: una comilla sin cerrar se traga el resto del archivo."""
    for number, line in enumerate(content.splitlines(), start=1):
        code = line.split(" #", 1)[0]
        if code.lstrip().startswith("#"):
            continue
        if code.replace('\\"', "").count('"') % 2:
            return number
    return None


def yaml_syntax_error(content: str) -> str | None:
    """Explica por qué el YAML no se puede leer, empezando por la línea a corregir; None si está bien."""
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        context_mark = getattr(error, "context_mark", None)
        problem = getattr(error, "problem", None) or "formato inválido"
        quote_line = _unclosed_quote_line(content)
        if quote_line:
            detail = f"Revisa la línea {quote_line}: tiene una comilla sin cerrar"
            if mark:
                detail += f" (el lector de YAML se detuvo en la línea {mark.line + 1})"
            return detail + "."
        where = f" en la línea {mark.line + 1}, columna {mark.column + 1}" if mark else ""
        detail = f"El YAML no es válido{where}: {problem}"
        if context_mark and mark and context_mark.line != mark.line:
            detail += f". El bloque con el error empieza en la línea {context_mark.line + 1}"
        return detail + "."
    return None
