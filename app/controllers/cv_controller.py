from fastapi import APIRouter

from app.schemas.cv import RenderCvRequest, RenderCvResponse
from app.services.implementations.rendercv_service import RenderCvService

router = APIRouter(prefix="/cv", tags=["CV"])
renderer = RenderCvService()


@router.post("/render", response_model=RenderCvResponse)
async def render_cv(payload: RenderCvRequest) -> RenderCvResponse:
    return await renderer.render(payload)
