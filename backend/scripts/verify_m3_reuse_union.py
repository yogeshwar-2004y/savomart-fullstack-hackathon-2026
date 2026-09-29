"""Verify PostGIS-backed catchment reuse across multiple recent studies."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from geoalchemy2.shape import from_shape, to_shape
from pyproj import Transformer
from shapely.geometry import MultiPolygon, box
from shapely.ops import transform
from sqlalchemy import delete, select

from app.api.dependencies import DEMO_USERS
from app.core.config import get_settings
from app.db.models import Area, AreaAnalysis, AreaReport, CatchmentStudy
from app.db.session import SessionLocal
from app.m1_areas.geometry import area_sq_km
from app.m3_surveys.schemas import StudyCreate
from app.m3_surveys.service import _multi, create_study, geometry_overlap_ratio

TO_METRES = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True)
TO_WGS84 = Transformer.from_crs("EPSG:32644", "EPSG:4326", always_xy=True)


def metric_geometry(geometry):
    return transform(TO_METRES.transform, geometry)


def wgs84_geometry(geometry):
    return transform(TO_WGS84.transform, geometry)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def cut_x(geometry, fraction: float) -> float:
    projected = metric_geometry(geometry)
    min_x, min_y, max_x, max_y = projected.bounds
    target_area = projected.area * fraction
    low, high = min_x, max_x
    for _ in range(50):
        middle = (low + high) / 2
        left_area = projected.intersection(box(min_x - 1, min_y - 1, middle, max_y + 1)).area
        if left_area < target_area:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def segment(geometry, start_fraction: float, end_fraction: float) -> MultiPolygon:
    projected = metric_geometry(geometry)
    min_x, min_y, max_x, max_y = projected.bounds
    start = min_x - 1 if start_fraction == 0 else cut_x(geometry, start_fraction)
    end = max_x + 1 if end_fraction == 1 else cut_x(geometry, end_fraction)
    return _multi(wgs84_geometry(projected.intersection(box(start, min_y - 1, end, max_y + 1))))


def run_scenario(report_id: UUID, target: MultiPolygon, source_specs: list[tuple[MultiPolygon, datetime]], label: str) -> dict:
    settings = get_settings()
    with SessionLocal() as db:
        report = db.scalar(select(AreaReport).where(AreaReport.id == report_id))
        check(report is not None, "Verification report disappeared before scenario execution")
        source_studies = [
            CatchmentStudy(
                area_report_id=report.id,
                target_type="area_report",
                target_label=f"{label} source {index}",
                target_geometry=from_shape(geometry, srid=4326),
                survey_geometry=from_shape(geometry, srid=4326),
                status="completed",
                requested_by_id="bd-manager-1",
                requested_by_name="M1-M3 integration verification",
                reuse_max_age_days=settings.catchment_reuse_max_age_days,
                reuse_min_coverage=settings.catchment_reuse_min_coverage,
                summary={"observation_count": 1, "evidence_kind": "demo"},
                completed_at=completed_at,
            )
            for index, (geometry, completed_at) in enumerate(source_specs)
        ]
        db.add_all(source_studies)
        db.flush()
        source_ids = [item.id for item in source_studies]
        created = create_study(
            db,
            StudyCreate(target_type="area_report", target_id=report.id),
            DEMO_USERS["bd-manager-1"],
            settings,
        )
        result = {
            "status": created.status,
            "source_ids": [UUID(value) for value in (created.source_study_ids or [])],
            "coverage": created.reuse_coverage,
            "zone_count": len(created.zones),
            "remaining_ratio": geometry_overlap_ratio(target, _multi(to_shape(created.survey_geometry))),
        }
        db.delete(created)
        for source in source_studies:
            db.delete(source)
        db.commit()
        check(set(result["source_ids"]).issubset(set(source_ids)), "Unexpected source study was included")
        return result


def main() -> None:
    settings = get_settings()
    now = datetime.now(UTC)
    fixture_name = f"Reuse verification area {uuid4()}"
    isolated_area = MultiPolygon([box(80.061, 12.761, 80.081, 12.781)])
    with SessionLocal() as db:
        area = Area(
            name=fixture_name,
            selection_method="cells",
            geometry=from_shape(isolated_area, srid=4326),
            area_sq_km=area_sq_km(isolated_area),
            source="Automated PostGIS verification fixture",
            source_id=f"verification:{uuid4()}",
            boundary_type="user-selected",
        )
        analysis = AreaAnalysis(area=area, status="completed", scoring_version="area-fitness-v2")
        db.add_all([area, analysis])
        db.flush()
        report = AreaReport(
            analysis_id=analysis.id,
            area_id=area.id,
            title="Reuse verification report",
            score=50,
            rating="Needs validation",
            summary="Automated PostGIS verification fixture",
            scoring_version="area-fitness-v2",
            source_snapshot_at=now,
        )
        db.add(report)
        db.commit()
        target = _multi(to_shape(report.area.geometry))
        report_id = report.id
        west = segment(target, 0.0, 0.40)
        east = segment(target, 0.40, 0.82)
        partial = segment(target, 0.0, 0.40)
        expired = [(target, now - timedelta(days=settings.catchment_reuse_max_age_days + 1))]
        no_overlap = [(MultiPolygon([box(80.051, 12.751, 80.052, 12.752)]), now)]

    try:
        union_result = run_scenario(report_id, target, [(west, now), (east, now - timedelta(hours=1))], "union")
        partial_result = run_scenario(report_id, target, [(partial, now)], "partial")
        expired_result = run_scenario(report_id, target, expired, "expired")
        no_overlap_result = run_scenario(report_id, target, no_overlap, "no-overlap")
    finally:
        with SessionLocal() as db:
            area_record = db.scalar(select(Area).where(Area.name == fixture_name))
            if area_record:
                report_record = db.scalar(select(AreaReport).where(AreaReport.area_id == area_record.id))
                if report_record:
                    db.execute(delete(CatchmentStudy).where(CatchmentStudy.area_report_id == report_record.id))
                    db.execute(delete(AreaReport).where(AreaReport.id == report_record.id))
                    db.execute(delete(AreaAnalysis).where(AreaAnalysis.id == report_record.analysis_id))
                db.delete(area_record)
            db.commit()

    check(union_result["status"] == "reused", "Combined recent coverage was not reused")
    check(len(union_result["source_ids"]) == 2, "Both source studies were not recorded")
    check(union_result["coverage"] >= settings.catchment_reuse_min_coverage, "Combined coverage missed the reuse threshold")
    check(union_result["zone_count"] == 0, "Fully reused coverage created duplicate zones")
    check(union_result["remaining_ratio"] == 0, "Fully reused study retained survey geometry")
    check(partial_result["status"] == "requested", "Partial coverage incorrectly completed the study")
    check(len(partial_result["source_ids"]) == 1, "Partial source study was not recorded")
    check(0.5 < partial_result["remaining_ratio"] < 0.7, "Partial study did not retain only uncovered geometry")
    check(expired_result["status"] == "requested" and not expired_result["source_ids"], "Expired coverage was reused")
    check(no_overlap_result["status"] == "requested" and not no_overlap_result["source_ids"], "Non-overlapping coverage was reused")

    print({
        "combined_recent_coverage": union_result,
        "partial_coverage": partial_result,
        "expired_coverage": expired_result,
        "no_overlap": no_overlap_result,
    })


if __name__ == "__main__":
    main()
