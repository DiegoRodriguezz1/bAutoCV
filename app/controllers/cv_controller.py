from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import ROOT_DIR, get_settings
from app.schemas.cv import RenderCvRequest, RenderCvResponse, RenderCvYamlResponse
from app.services.implementations.rendercv_service import RenderCvService

router = APIRouter(prefix="/cv", tags=["CV"])
renderer = RenderCvService()


@router.post("/render", response_model=RenderCvResponse)
async def render_cv(payload: RenderCvRequest) -> RenderCvResponse:
    return await renderer.render(payload)


@router.post("/yaml", response_model=RenderCvYamlResponse)
async def generate_rendercv_yaml(payload: RenderCvRequest) -> RenderCvYamlResponse:
    return renderer.generate_yaml(payload)


@router.get("/download/{filename}")
async def download_cv(filename: str) -> FileResponse:
    """Download a generated PDF by filename."""
    settings = get_settings()
    output_dir = ROOT_DIR / settings.rendercv_output_dir
    pdf_path = output_dir / filename

    if not pdf_path.exists() or pdf_path.suffix != ".pdf":
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=filename,
    )
