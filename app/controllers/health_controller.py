from fastapi import APIRouter
from fastapi import Response

from app.core.config import get_settings
from app.db.database import check_db_connection
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])
settings = get_settings()


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    database_ok = await check_db_connection()
    return HealthResponse(
        status="ok",
        app_env=settings.app_env,
        database="up" if database_ok else "down",
    )


@router.head("")
async def health_check_head() -> Response:
    # Lightweight probe for load balancers/health checks.
    return Response(status_code=200)
