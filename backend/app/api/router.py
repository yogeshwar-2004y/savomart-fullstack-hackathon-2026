from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.areas import router as areas_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.reports import router as reports_router
from app.api.routes.m2 import router as m2_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(areas_router, tags=["M1 areas"])
api_router.include_router(jobs_router, tags=["jobs"])
api_router.include_router(reports_router, tags=["M1 reports"])
api_router.include_router(m2_router, tags=["M2 property scouting"])
