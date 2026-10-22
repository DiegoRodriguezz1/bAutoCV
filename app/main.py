from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.db.database import create_database_schema

settings = get_settings()
allowed_origins = [
    origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()
]

app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-ESCO-Degraded"],
)


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    return {"message": "bAutoCV API online"}


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.on_event("startup")
async def startup_database() -> None:
    await create_database_schema()
