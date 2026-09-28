import hashlib
import json
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
from app.m1_areas.geometry import InvalidAreaGeometry, area_sq_km, normalize_area_geometry, normalize_chennai_point
from app.m1_areas.schemas import AnalysisAccepted, AnalysisCreate, AreaSearchResult, RadiusAreaRequest, RadiusAreaResponse
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


@router.post("/approximate-radius", response_model=RadiusAreaResponse)
def approximate_radius(
    payload: RadiusAreaRequest,
    db: Annotated[Session, Depends(get_db)],
    _role: Annotated[str, Depends(require_bd_manager)],
) -> RadiusAreaResponse:
    try:
        point = normalize_chennai_point(payload.point)
        point_geometry = func.ST_SetSRID(func.ST_MakePoint(point.x, point.y), 4326)
        raw = db.scalar(select(func.ST_AsGeoJSON(func.ST_Buffer(cast(point_geometry, Geography), payload.radius_m))))
        geometry = normalize_area_geometry(json.loads(raw))
    except (InvalidAreaGeometry, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RadiusAreaResponse(
        name=payload.display_name.split(",")[0], query=payload.query, selection_method="radius",
        geometry=json.loads(json.dumps(geometry.__geo_interface__)), source=payload.source,
        source_id=f"{payload.source_id}:radius:{payload.radius_m}m", source_url=payload.source_url,
        source_license=payload.source_license, boundary_type="approximate", lookup_at=payload.lookup_at,
        is_official=False, is_approximate=True,
        approximation_warning=f"Approximate {payload.radius_m / 1000:g} km radius around a geocoded point; this is not a locality or pincode boundary.",
        resolver_cache_age_seconds=payload.resolver_cache_age_seconds,
    )


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
    source_id = payload.area.source_id
    if payload.area.selection_method == "cells":
        source_id = f"user-cells:sha256:{hashlib.sha256(geometry.wkb).hexdigest()}"
    area = Area(
        name=payload.area.name, query=payload.area.query,
        selection_method=payload.area.selection_method,
        geometry=from_shape(geometry, srid=4326), area_sq_km=area_sq_km(geometry),
        source=payload.area.source, source_id=source_id, source_url=payload.area.source_url,
        source_license=payload.area.source_license, boundary_type=payload.area.boundary_type,
        boundary_lookup_at=payload.area.lookup_at, is_official=payload.area.is_official,
        is_approximate=payload.area.is_approximate,
        approximation_warning=payload.area.approximation_warning,
        resolver_cache_age_seconds=payload.area.resolver_cache_age_seconds,
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
