from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    openapi_url="/openapi.json",
)


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    return {"message": "bAutoCV API online"}


app.include_router(api_router, prefix=settings.api_v1_prefix)
