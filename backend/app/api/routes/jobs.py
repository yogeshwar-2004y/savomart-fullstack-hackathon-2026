from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import require_bd_manager
from app.db.dependencies import get_db
from app.db.models import AnalysisJob, AreaAnalysis
from app.jobs.queue import enqueue_area_analysis
from app.jobs.service import JobRetryError, prepare_retry
from app.m1_areas.schemas import JobResponse, RetryResponse

router = APIRouter(prefix="/jobs")


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID, db: Annotated[Session, Depends(get_db)]) -> AnalysisJob:
    job = db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/retry", response_model=RetryResponse)
def retry_job(
    job_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(require_bd_manager)],
) -> RetryResponse:
    job = db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        prepare_retry(job)
    except JobRetryError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if job.analysis_id:
        analysis = db.get(AreaAnalysis, job.analysis_id)
        if analysis:
            analysis.status = "queued"
    db.commit()
    try:
        enqueue_area_analysis(str(job.id), job.attempts)
    except Exception as exc:
        job.status = "failed"
        job.status_detail = "Redis queue unavailable. Start Redis and retry."
        job.error_code = exc.__class__.__name__
        if job.analysis_id:
            analysis = db.get(AreaAnalysis, job.analysis_id)
            if analysis:
                analysis.status = "failed"
        db.commit()
    return RetryResponse(job_id=job.id, status=job.status, attempts=job.attempts)
