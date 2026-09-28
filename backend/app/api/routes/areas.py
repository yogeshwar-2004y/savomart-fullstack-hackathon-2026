from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2 import Geography
from geoalchemy2.shape import from_shape
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_bd_manager
from app.db.dependencies import get_db
from app.db.models import AnalysisJob, Area, AreaAnalysis
from app.jobs.queue import enqueue_area_analysis
from app.m1_areas.adapters import search_chennai_areas
from app.m1_areas.geometry import InvalidAreaGeometry, area_sq_km, normalize_area_geometry
from app.m1_areas.schemas import AnalysisAccepted, AnalysisCreate, AreaSearchResult
from app.scoring.area_v1 import SCORING_VERSION

router = APIRouter(prefix="/areas")


@router.get("/search", response_model=list[AreaSearchResult])
def search_areas(
    q: Annotated[str, Query(min_length=2, max_length=120)],
    method: Annotated[str, Query(pattern="^(locality|pincode)$")] = "locality",
) -> list[AreaSearchResult]:
    results = search_chennai_areas(q, method)
    if not results:
        raise HTTPException(status_code=404, detail="No Chennai boundary found. Try a locality or six-digit pincode.")
    return results


@router.post("/analyses", response_model=AnalysisAccepted, status_code=status.HTTP_202_ACCEPTED)
def create_analysis(
    payload: AnalysisCreate,
    db: Annotated[Session, Depends(get_db)],
    role: Annotated[str, Depends(require_bd_manager)],
) -> AnalysisAccepted:
    try:
        geometry = normalize_area_geometry(payload.area.geometry)
    except InvalidAreaGeometry as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    area = Area(
        name=payload.area.name, query=payload.area.query,
        selection_method=payload.area.selection_method,
        geometry=from_shape(geometry, srid=4326), area_sq_km=area_sq_km(geometry),
    )
    analysis = AreaAnalysis(area=area, requested_by_role=role, scoring_version=SCORING_VERSION)
    db.add_all([area, analysis])
    db.flush()
    postgis_area = db.scalar(
        select(func.ST_Area(cast(Area.geometry, Geography)) / 1_000_000).where(Area.id == area.id)
    )
    if postgis_area is not None:
        area.area_sq_km = round(float(postgis_area), 3)
    job = AnalysisJob(
        analysis_id=analysis.id, status="queued", progress=0,
        status_detail="Waiting for analysis worker", attempts=1, retryable=True,
    )
    db.add(job)
    db.commit()
    try:
        enqueue_area_analysis(str(job.id), job.attempts)
    except Exception as exc:
        job.status = "failed"
        job.status_detail = "Redis queue unavailable. Start Redis and retry."
        job.error_code = exc.__class__.__name__
        analysis.status = "failed"
        db.commit()
    db.refresh(job)
    return AnalysisAccepted(analysis_id=analysis.id, job_id=job.id, status=job.status)
