import yaml
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.experiment_controller import require_research_key
from app.db.database import get_db_session
from app.entities.saved_cv import SavedCv
from app.schemas.saved_cv import SavedCvResponse, SavedCvSummary, SavedCvWrite

# Los CV guardados tienen datos personales: mismo acceso que la consola del investigador.
router = APIRouter(prefix="/cv/saved", tags=["CV guardados"], dependencies=[Depends(require_research_key)])


def _unclosed_quote_line(content: str) -> int | None:
    """Primera línea con comillas dobles impares: una comilla sin cerrar se traga el resto del archivo."""
    for number, line in enumerate(content.splitlines(), start=1):
        code = line.split(" #", 1)[0]
        if code.lstrip().startswith("#"):
            continue
        if code.replace('\\"', "").count('"') % 2:
            return number
    return None


def _validate_yaml(content: str) -> None:
    """Rechaza YAML mal formado antes de guardarlo, indicando la línea del error."""
    try:
        document = yaml.safe_load(content)
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        context_mark = getattr(error, "context_mark", None)
        where = f" (línea {mark.line + 1}, columna {mark.column + 1})" if mark else ""
        problem = getattr(error, "problem", None) or "formato inválido"
        detail = f"El YAML no es válido{where}: {problem}"
        if context_mark and mark and context_mark.line != mark.line:
            detail += f". El bloque con el error empieza en la línea {context_mark.line + 1}"
        quote_line = _unclosed_quote_line(content)
        if quote_line:
            detail += f". Revisa la línea {quote_line}: tiene una comilla sin cerrar"
        raise HTTPException(status_code=422, detail=detail) from error
    if not isinstance(document, dict) or not isinstance(document.get("cv"), dict):
        raise HTTPException(status_code=422, detail="El YAML debe tener una sección 'cv' en la raíz")


async def _get(db: AsyncSession, cv_id: int) -> SavedCv:
    saved = await db.get(SavedCv, cv_id)
    if saved is None:
        raise HTTPException(status_code=404, detail="Hoja de vida no encontrada")
    return saved


async def _commit(db: AsyncSession, name: str) -> None:
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"Ya existe una hoja de vida llamada '{name}'") from error


@router.get("", response_model=list[SavedCvSummary])
async def list_saved_cvs(db: AsyncSession = Depends(get_db_session)) -> list[SavedCv]:
    result = await db.execute(select(SavedCv).order_by(SavedCv.name))
    return list(result.scalars())


@router.get("/{cv_id}", response_model=SavedCvResponse)
async def get_saved_cv(cv_id: int, db: AsyncSession = Depends(get_db_session)) -> SavedCv:
    return await _get(db, cv_id)


@router.post("", response_model=SavedCvResponse, status_code=201)
async def create_saved_cv(payload: SavedCvWrite, db: AsyncSession = Depends(get_db_session)) -> SavedCv:
    _validate_yaml(payload.yaml_content)
    saved = SavedCv(name=payload.name, yaml_content=payload.yaml_content)
    db.add(saved)
    await _commit(db, payload.name)
    await db.refresh(saved)
    return saved


@router.put("/{cv_id}", response_model=SavedCvResponse)
async def update_saved_cv(cv_id: int, payload: SavedCvWrite, db: AsyncSession = Depends(get_db_session)) -> SavedCv:
    _validate_yaml(payload.yaml_content)
    saved = await _get(db, cv_id)
    saved.name = payload.name
    saved.yaml_content = payload.yaml_content
    await _commit(db, payload.name)
    await db.refresh(saved)
    return saved


@router.delete("/{cv_id}", status_code=204)
async def delete_saved_cv(cv_id: int, db: AsyncSession = Depends(get_db_session)) -> Response:
    saved = await _get(db, cv_id)
    await db.delete(saved)
    await db.commit()
    return Response(status_code=204)
