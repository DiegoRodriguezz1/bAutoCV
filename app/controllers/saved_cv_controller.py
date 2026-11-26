import yaml
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.experiment_controller import require_research_key
from app.db.database import get_db_session
from app.entities.saved_cv import SavedCv
from app.schemas.saved_cv import SavedCvResponse, SavedCvSummary, SavedCvWrite
from app.services.implementations.yaml_errors import yaml_syntax_error

# Los CV guardados tienen datos personales: mismo acceso que la consola del investigador.
router = APIRouter(prefix="/cv/saved", tags=["CV guardados"], dependencies=[Depends(require_research_key)])


def _validate_yaml(content: str) -> None:
    """Rechaza YAML mal formado antes de guardarlo, indicando la línea del error."""
    error = yaml_syntax_error(content)
    if error:
        raise HTTPException(status_code=422, detail=error)
    document = yaml.safe_load(content)
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
