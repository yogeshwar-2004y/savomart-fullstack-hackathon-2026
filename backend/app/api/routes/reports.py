from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.m1_areas.repository import get_report, list_reports
from app.m1_areas.schemas import AreaReportResponse, ReportComparisonResponse, ReportSummaryResponse

router = APIRouter(prefix="/area-reports")


@router.get("", response_model=list[ReportSummaryResponse])
def report_list(db: Annotated[Session, Depends(get_db)]) -> list[ReportSummaryResponse]:
    return list_reports(db)


@router.get("/compare", response_model=ReportComparisonResponse)
def compare_reports(
    db: Annotated[Session, Depends(get_db)],
    left_id: Annotated[UUID, Query()],
    right_id: Annotated[UUID, Query()],
) -> ReportComparisonResponse:
    left, right = get_report(db, left_id), get_report(db, right_id)
    if not left or not right:
        raise HTTPException(status_code=404, detail="One or both reports were not found")
    left_metrics = {metric.key: metric.contribution for metric in left.metrics}
    right_metrics = {metric.key: metric.contribution for metric in right.metrics}
    keys = left_metrics.keys() | right_metrics.keys()
    return ReportComparisonResponse(
        left=left, right=right, score_delta=round(right.score - left.score, 1),
        metric_deltas={key: round(right_metrics.get(key, 0) - left_metrics.get(key, 0), 2) for key in keys},
    )


@router.get("/{report_id}", response_model=AreaReportResponse)
def report_detail(report_id: UUID, db: Annotated[Session, Depends(get_db)]) -> AreaReportResponse:
    report = get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
