from fastapi import APIRouter

from app.controllers.cv_controller import router as cv_router
from app.controllers.esco_controller import router as esco_router
from app.controllers.health_controller import router as health_router
from app.controllers.ocr_controller import router as ocr_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(cv_router)
api_router.include_router(esco_router)
api_router.include_router(ocr_router)
