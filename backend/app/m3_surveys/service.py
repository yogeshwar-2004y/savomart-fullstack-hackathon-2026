import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from geoalchemy2 import Geography
from geoalchemy2.shape import from_shape, to_shape
from pyproj import Transformer
from shapely.geometry import MultiPolygon, Point, Polygon, box, mapping
from shapely.ops import transform, unary_union
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import DEMO_USERS, Principal
from app.core.config import Settings, get_settings
from app.db.models import (
    AreaReport,
    CatchmentStudy,
    LaneCapture,
    Property,
    PropertyEvaluation,
    PropertyStageTransition,
    SurveyZone,
)
from app.m2_properties.service import get_property_record
from app.m3_surveys.schemas import (
    CatchmentStudyResponse,
    LaneSubmissionCreate,
    LaneSubmissionResponse,
    StudyCreate,
    SurveyZoneResponse,
    ZonePlan,
)
from app.scoring.property_v2 import SCORING_VERSION, score_with_catchment

_TO_CHENNAI_METRES = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True)
_FROM_CHENNAI_METRES = Transformer.from_crs("EPSG:32644", "EPSG:4326", always_xy=True)


def _to_metric(geometry):
    return transform(_TO_CHENNAI_METRES.transform, geometry)


def _to_wgs84(geometry):
    return transform(_FROM_CHENNAI_METRES.transform, geometry)


def _multi(geometry) -> MultiPolygon:
    if not geometry.is_valid:
        geometry = geometry.buffer(0)
    if isinstance(geometry, Polygon):
        return MultiPolygon([geometry])
    if isinstance(geometry, MultiPolygon):
        return geometry
    polygons = [part for part in getattr(geometry, "geoms", []) if isinstance(part, Polygon)]
    if not polygons:
        raise ValueError("Catchment geometry does not contain a surveyable polygon")
    return MultiPolygon(polygons)


def geometry_overlap_ratio(target: MultiPolygon, coverage: MultiPolygon) -> float:
    metric_target = _to_metric(target)
    if target.is_empty or metric_target.area <= 0:
        return 0
    return max(0.0, min(1.0, metric_target.intersection(_to_metric(coverage)).area / metric_target.area))


def zones_overlap(left: MultiPolygon, right: MultiPolygon) -> bool:
    return _to_metric(left).intersection(_to_metric(right)).area > 1e-6


def _target_geometry(db: Session, payload: StudyCreate, settings: Settings):
    if payload.target_type == "property":
        prop = get_property_record(db, payload.target_id)
        if not prop:
            raise LookupError("Property not found")
        raw = db.scalar(
            select(func.ST_AsGeoJSON(func.ST_Buffer(cast(Property.location, Geography), settings.catchment_radius_m)))
            .where(Property.id == prop.id)
        )
        geometry = _multi(Polygon(json.loads(raw)["coordinates"][0]))
        return geometry, prop.address, prop, None

    report = db.scalar(
        select(AreaReport)
        .where(AreaReport.id == payload.target_id)
        .options(selectinload(AreaReport.area))
    )
    if not report:
        raise LookupError("Area report not found")
    return _multi(to_shape(report.area.geometry)), report.area.name, None, report


def _append_property_evaluation(
    db: Session, prop: Property, study: CatchmentStudy, principal_name: str,
) -> None:
    if not study.summary:
        return
    previous = max(prop.evaluations, key=lambda item: item.version)
    created_at = study.completed_at or datetime.now(UTC)
    result = score_with_catchment(previous.metrics, study.summary, created_at)
    version = previous.version + 1
    result["insights"].append(
        f"Score changed from {previous.score:.1f} to {result['score']:.1f} after catchment study {study.id}."
    )
    prop.evaluations.append(
        PropertyEvaluation(
            property_id=prop.id,
            version=version,
            scoring_version=SCORING_VERSION,
            **result,
        )
    )
    if prop.stage == "survey_requested":
        prop.stage = "under_review"
        prop.transitions.append(
            PropertyStageTransition(
                property_id=prop.id,
                from_stage="survey_requested",
                to_stage="under_review",
                actor_id="catchment-system",
                actor_name=principal_name,
                reason=f"Catchment study {study.id} completed; evaluation version {version} created.",
            )
        )
    study.summary["evaluation_version"] = version
    study.summary["previous_score"] = previous.score
    study.summary["updated_score"] = result["score"]


def create_study(
    db: Session,
    payload: StudyCreate,
    principal: Principal,
    settings: Settings | None = None,
) -> CatchmentStudy:
    settings = settings or get_settings()
    target, label, prop, report = _target_geometry(db, payload, settings)
    target_element = from_shape(target, srid=4326)
    cutoff = datetime.now(UTC) - timedelta(days=settings.catchment_reuse_max_age_days)
    candidates = db.scalars(
        select(CatchmentStudy)
        .where(
            CatchmentStudy.status == "completed",
            CatchmentStudy.completed_at >= cutoff,
            func.ST_Intersects(CatchmentStudy.target_geometry, target_element),
        )
        .order_by(CatchmentStudy.completed_at.desc())
    ).all()
    source_studies: list[CatchmentStudy] = []
    covered = MultiPolygon([])
    for candidate in candidates:
        candidate_geometry = _multi(to_shape(candidate.target_geometry))
        newly_covered = candidate_geometry if covered.is_empty else candidate_geometry.difference(covered)
        if newly_covered.is_empty:
            continue
        newly_covered = _multi(newly_covered)
        if _to_metric(newly_covered).area > 1.0:
            source_studies.append(candidate)
            covered = _multi(unary_union([covered, candidate_geometry])) if not covered.is_empty else candidate_geometry

    best = source_studies[0] if source_studies else None
    best_coverage = geometry_overlap_ratio(target, covered) if source_studies else 0.0

    now = datetime.now(UTC)
    eligible = best is not None and best_coverage >= settings.catchment_reuse_min_coverage
    survey_geometry = MultiPolygon([]) if eligible else target
    if source_studies and not eligible:
        survey_geometry = _multi(target.difference(covered))
    study = CatchmentStudy(
        property_id=prop.id if prop else None,
        area_report_id=report.id if report else None,
        target_type=payload.target_type,
        target_label=label,
        target_geometry=target_element,
        survey_geometry=from_shape(survey_geometry, srid=4326),
        status="reused" if eligible else "requested",
        requested_by_id=principal.id,
        requested_by_name=principal.name,
        source_study_id=best.id if best else None,
        source_study_ids=[str(item.id) for item in source_studies],
        reuse_coverage=round(best_coverage, 4),
        reuse_age_days=round((now - best.completed_at).total_seconds() / 86400, 2) if best and best.completed_at else None,
        reuse_max_age_days=settings.catchment_reuse_max_age_days,
        reuse_min_coverage=settings.catchment_reuse_min_coverage,
        summary=dict(best.summary) if eligible and best and best.summary else None,
        completed_at=now if eligible else None,
    )
    if study.summary is not None:
        study.summary["reused_from_study_ids"] = [str(item.id) for item in source_studies]
        study.summary["reuse_coverage_percent"] = round(best_coverage * 100, 1)
    db.add(study)
    db.flush()
    if eligible and prop:
        _append_property_evaluation(db, prop, study, "Savo SiteScout catchment reuse")
    db.commit()
    return get_study(db, study.id)  # type: ignore[return-value]


def _study_query():
    return select(CatchmentStudy).options(
        selectinload(CatchmentStudy.zones).selectinload(SurveyZone.submissions)
    )


def get_study(db: Session, study_id: UUID) -> CatchmentStudy | None:
    return db.scalar(_study_query().where(CatchmentStudy.id == study_id))


def list_studies(db: Session, principal: Principal) -> list[CatchmentStudy]:
    query = _study_query().order_by(CatchmentStudy.created_at.desc())
    if principal.role == "survey-executive":
        query = query.join(SurveyZone).where(SurveyZone.assignee_id == principal.id).distinct()
    return list(db.scalars(query).unique().all())


def plan_zones(db: Session, study: CatchmentStudy, payload: ZonePlan) -> CatchmentStudy:
    if study.status in {"completed", "reused"}:
        raise ValueError("Completed or reused studies do not need new zones")
    if study.zones:
        raise ValueError("Zones have already been created for this study")
    assignees = []
    for user_id in payload.assignee_ids:
        user = DEMO_USERS.get(user_id)
        if not user or user.role != "survey-executive":
            raise ValueError("Choose valid Survey Executives")
        assignees.append(user)

    survey = _multi(to_shape(study.survey_geometry))
    metric_survey = _to_metric(survey)
    min_x, min_y, max_x, max_y = metric_survey.bounds
    width = (max_x - min_x) / payload.zone_count
    zones = []
    for index in range(payload.zone_count):
        right = max_x if index == payload.zone_count - 1 else min_x + width * (index + 1)
        strip = box(min_x + width * index, min_y, right, max_y)
        geometry = _multi(_to_wgs84(metric_survey.intersection(strip)))
        if geometry.is_empty:
            raise ValueError("The requested split produced an empty work zone")
        assignee = assignees[index % len(assignees)]
        zones.append(
            SurveyZone(
                study_id=study.id,
                label=f"Zone {index + 1}",
                geometry=from_shape(geometry, srid=4326),
                assignee_id=assignee.id,
                assignee_name=assignee.name,
            )
        )
    for index, zone in enumerate(zones):
        left = _multi(to_shape(zone.geometry))
        if any(zones_overlap(left, _multi(to_shape(other.geometry))) for other in zones[index + 1 :]):
            raise ValueError("Survey zones must not overlap")
    db.add_all(zones)
    study.status = "assigned"
    db.commit()
    return get_study(db, study.id)  # type: ignore[return-value]


def get_zone_for_principal(db: Session, zone_id: UUID, principal: Principal) -> SurveyZone | None:
    zone = db.scalar(
        select(SurveyZone)
        .where(SurveyZone.id == zone_id)
        .options(selectinload(SurveyZone.study), selectinload(SurveyZone.submissions))
    )
    if zone and principal.role == "survey-executive" and zone.assignee_id != principal.id:
        return None
    return zone


def list_zones(db: Session, principal: Principal) -> list[SurveyZone]:
    query = (
        select(SurveyZone)
        .options(selectinload(SurveyZone.study), selectinload(SurveyZone.submissions))
        .order_by(SurveyZone.created_at.desc())
    )
    if principal.role == "survey-executive":
        query = query.where(SurveyZone.assignee_id == principal.id)
    return list(db.scalars(query).unique().all())


def submit_lane(
    db: Session,
    zone: SurveyZone,
    payload: LaneSubmissionCreate,
    principal: Principal,
    settings: Settings | None = None,
) -> LaneCapture:
    existing = db.scalar(select(LaneCapture).where(LaneCapture.client_submission_id == payload.client_submission_id))
    if existing:
        if existing.zone_id != zone.id or existing.submitted_by_id != principal.id:
            raise PermissionError("Submission ID already belongs to different survey work")
        return existing
    settings = settings or get_settings()
    point = from_shape(Point(payload.longitude, payload.latitude), srid=4326)
    distance = float(
        db.scalar(
            select(func.ST_Distance(cast(point, Geography), cast(SurveyZone.geometry, Geography)))
            .where(SurveyZone.id == zone.id)
        )
        or 0
    )
    mismatch = distance > max(settings.survey_location_tolerance_m, payload.gps_accuracy_m)
    capture = LaneCapture(
        zone_id=zone.id,
        study_id=zone.study_id,
        submitted_by_id=principal.id,
        submitted_by_name=principal.name,
        location=point,
        location_mismatch=mismatch,
        mismatch_distance_m=round(distance, 1),
        **payload.model_dump(exclude={"latitude", "longitude"}),
    )
    db.add(capture)
    zone.status = "in_progress"
    zone.mismatch_review = zone.mismatch_review or mismatch
    if zone.study.status in {"requested", "assigned"}:
        zone.study.status = "in_progress"
    db.commit()
    db.refresh(capture)
    return capture


def complete_zone(db: Session, zone: SurveyZone) -> CatchmentStudy:
    if zone.status == "completed":
        return get_study(db, zone.study_id)  # type: ignore[return-value]
    count = db.scalar(select(func.count(LaneCapture.id)).where(LaneCapture.zone_id == zone.id)) or 0
    if count == 0:
        raise ValueError("Submit at least one lane observation before completing a zone")
    zone.status = "completed"
    zone.completed_at = datetime.now(UTC)
    db.flush()
    remaining = db.scalar(
        select(func.count(SurveyZone.id)).where(
            SurveyZone.study_id == zone.study_id,
            SurveyZone.status != "completed",
        )
    )
    if remaining == 0:
        _complete_study(db, zone.study_id)
    db.commit()
    return get_study(db, zone.study_id)  # type: ignore[return-value]


def _complete_study(db: Session, study_id: UUID) -> None:
    study = get_study(db, study_id)
    if not study or study.status in {"completed", "reused"}:
        return
    captures = [capture for zone in study.zones for capture in zone.submissions]
    if not captures:
        raise ValueError("A completed study requires lane observations")
    source_summary = study.source_study.summary if study.source_study and study.source_study.summary else {}
    source_count = int(source_summary.get("observation_count", 0))
    count = source_count + len(captures)
    residential = int(source_summary.get("residential_units", 0)) + sum(item.residential_units for item in captures)
    commercial = int(source_summary.get("commercial_units", 0)) + sum(item.commercial_units for item in captures)
    pedestrian_total = float(source_summary.get("average_pedestrian_activity", 0)) * source_count + sum(
        item.pedestrian_activity for item in captures
    )
    vehicle_total = float(source_summary.get("average_vehicle_activity", 0)) * source_count + sum(
        item.vehicle_activity for item in captures
    )
    target = _multi(to_shape(study.target_geometry))
    covered_geometries = [_multi(to_shape(zone.geometry)) for zone in study.zones if zone.status == "completed"]
    source_ids = [UUID(value) for value in (study.source_study_ids or [])]
    if not source_ids and study.source_study_id:
        source_ids = [study.source_study_id]
    source_studies = db.scalars(
        select(CatchmentStudy).where(CatchmentStudy.id.in_(source_ids))
    ).all() if source_ids else []
    covered_geometries.extend(_multi(to_shape(item.target_geometry)) for item in source_studies)
    coverage = geometry_overlap_ratio(target, _multi(unary_union(covered_geometries)))
    now = datetime.now(UTC)
    study.status = "completed"
    study.completed_at = now
    has_demo = any(item.evidence_kind == "demo" for item in captures) or source_summary.get("evidence_kind") == "demo"
    study.summary = {
        "observation_count": count,
        "new_observation_count": len(captures),
        "residential_units": residential,
        "commercial_units": commercial,
        "average_pedestrian_activity": round(pedestrian_total / count, 2),
        "average_vehicle_activity": round(vehicle_total / count, 2),
        "location_mismatch_count": int(source_summary.get("location_mismatch_count", 0))
        + sum(item.location_mismatch for item in captures),
        "coverage_percent": round(coverage * 100, 1),
        "source": "Demo/simulated lane observations" if has_demo else "Submitted Savo SiteScout lane observations",
        "source_study_id": str(study.source_study_id) if study.source_study_id else None,
        "completed_at": now.isoformat(),
        "limitations": (
            "Field counts are timestamped executive observations; they are not census, income, or continuous footfall data."
        ),
        "evidence_kind": "demo" if has_demo else "field-survey",
    }
    if study.property_id:
        prop = get_property_record(db, study.property_id)
        if prop:
            _append_property_evaluation(db, prop, study, "Savo SiteScout catchment completion")


def _geojson(geometry) -> dict:
    return json.loads(json.dumps(mapping(to_shape(geometry))))


def serialize_lane(item: LaneCapture) -> LaneSubmissionResponse:
    point = to_shape(item.location)
    return LaneSubmissionResponse(
        id=item.id,
        client_submission_id=item.client_submission_id,
        zone_id=item.zone_id,
        lane_name=item.lane_name,
        latitude=point.y,
        longitude=point.x,
        gps_accuracy_m=item.gps_accuracy_m,
        observed_at=item.observed_at,
        residential_units=item.residential_units,
        commercial_units=item.commercial_units,
        pedestrian_activity=item.pedestrian_activity,
        vehicle_activity=item.vehicle_activity,
        notes=item.notes,
        status=item.status,
        evidence_kind=item.evidence_kind,
        location_mismatch=item.location_mismatch,
        mismatch_distance_m=item.mismatch_distance_m,
        created_at=item.created_at,
    )


def serialize_zone(item: SurveyZone) -> SurveyZoneResponse:
    return SurveyZoneResponse(
        id=item.id,
        study_id=item.study_id,
        study_label=item.study.target_label,
        label=item.label,
        geometry=_geojson(item.geometry),
        assignee_id=item.assignee_id,
        assignee_name=item.assignee_name,
        status=item.status,
        mismatch_review=item.mismatch_review,
        submission_count=len(item.submissions),
        submissions=[serialize_lane(capture) for capture in item.submissions],
        created_at=item.created_at,
        completed_at=item.completed_at,
    )


def serialize_study(item: CatchmentStudy) -> CatchmentStudyResponse:
    completed = sum(zone.status == "completed" for zone in item.zones)
    progress = 100.0 if item.status in {"completed", "reused"} else round(completed / len(item.zones) * 100, 1) if item.zones else 0.0
    return CatchmentStudyResponse(
        id=item.id,
        property_id=item.property_id,
        area_report_id=item.area_report_id,
        target_type=item.target_type,
        target_label=item.target_label,
        target_geometry=_geojson(item.target_geometry),
        survey_geometry=_geojson(item.survey_geometry),
        status=item.status,
        source_study_id=item.source_study_id,
        source_study_ids=[UUID(value) for value in (item.source_study_ids or [])],
        reuse_coverage=round(item.reuse_coverage * 100, 1),
        reuse_age_days=item.reuse_age_days,
        reuse_max_age_days=item.reuse_max_age_days,
        reuse_min_coverage=round(item.reuse_min_coverage * 100, 1),
        progress_percent=progress,
        summary=item.summary,
        zones=[serialize_zone(zone) for zone in item.zones],
        created_at=item.created_at,
        completed_at=item.completed_at,
    )
