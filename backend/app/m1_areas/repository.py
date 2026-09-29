import json
from uuid import UUID

from geoalchemy2.shape import to_shape
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import AreaReport
from app.m1_areas.schemas import (
    AreaReportResponse,
    MetricEvidenceResponse,
    ReportSummaryResponse,
    SuggestionResponse,
)


def list_reports(db: Session) -> list[ReportSummaryResponse]:
    reports = db.scalars(
        select(AreaReport).options(selectinload(AreaReport.area)).order_by(AreaReport.created_at.desc())
    ).all()
    return [ReportSummaryResponse(
        id=report.id, area_id=report.area_id, area_name=report.area.name, score=report.score,
        rating=report.rating, scoring_version=report.scoring_version, created_at=report.created_at,
    ) for report in reports]


def get_report(db: Session, report_id: UUID) -> AreaReportResponse | None:
    report = db.scalar(
        select(AreaReport).where(AreaReport.id == report_id).options(
            selectinload(AreaReport.area), selectinload(AreaReport.metrics), selectinload(AreaReport.suggestions)
        )
    )
    return serialize_report(report) if report else None


def serialize_report(report: AreaReport) -> AreaReportResponse:
    geometry = to_shape(report.area.geometry)
    return AreaReportResponse(
        id=report.id, analysis_id=report.analysis_id, area_id=report.area_id,
        area_name=report.area.name, title=report.title, score=report.score, rating=report.rating,
        summary=report.summary, scoring_version=report.scoring_version,
        source_snapshot_at=report.source_snapshot_at, used_cached_evidence=report.used_cached_evidence,
        cache_age_seconds=report.cache_age_seconds, created_at=report.created_at,
        selection_method=report.area.selection_method, area_sq_km=report.area.area_sq_km,
        geometry={"type": geometry.geom_type, "coordinates": json.loads(json.dumps(geometry.__geo_interface__["coordinates"]))},
        source=report.area.source, source_id=report.area.source_id, source_url=report.area.source_url,
        source_license=report.area.source_license, boundary_type=report.area.boundary_type,
        boundary_lookup_at=report.area.boundary_lookup_at, is_official=report.area.is_official,
        is_approximate=report.area.is_approximate, approximation_warning=report.area.approximation_warning,
        resolver_cache_age_seconds=report.area.resolver_cache_age_seconds,
        metrics=[MetricEvidenceResponse.model_validate(metric) for metric in report.metrics],
        suggestions=[SuggestionResponse(
            id=suggestion.id, rank=suggestion.rank, label=suggestion.label,
            latitude=to_shape(suggestion.point).y, longitude=to_shape(suggestion.point).x,
            rationale=suggestion.rationale, evidence=suggestion.evidence,
        ) for suggestion in report.suggestions],
    )
