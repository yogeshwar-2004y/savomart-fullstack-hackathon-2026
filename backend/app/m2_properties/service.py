from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from geoalchemy2 import Geography
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import MultiPolygon, Point, Polygon
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import DEMO_USERS, Principal
from app.core.config import Settings, get_settings
from app.db.models import (
    Area,
    AreaReport,
    Property,
    PropertyEvaluation,
    PropertyPhoto,
    PropertyStageTransition,
    ScoutAssignment,
    ScoutingSuggestion,
)
from app.m1_areas.adapters import fetch_osm_signals, fetch_store_signals
from app.m2_properties.photos import StoredPhoto
from app.m2_properties.schemas import (
    AssignmentCreate,
    AssignmentResponse,
    PropertyCapture,
    PropertyResponse,
)
from app.scoring.property_v1 import SCORING_VERSION, score_property, validate_transition


def create_assignment(db: Session, payload: AssignmentCreate, principal: Principal) -> ScoutAssignment:
    assignee = DEMO_USERS.get(payload.assignee_id)
    if not assignee or assignee.role != "bd-executive":
        raise ValueError("Choose a valid BD Executive")
    suggestion = db.scalar(select(ScoutingSuggestion).where(
        ScoutingSuggestion.id == payload.suggestion_id,
        ScoutingSuggestion.report_id == payload.area_report_id,
    ))
    if not suggestion:
        raise LookupError("The selected hotspot does not belong to this area report")
    assignment = ScoutAssignment(
        area_report_id=payload.area_report_id, suggestion_id=suggestion.id,
        target_label=suggestion.label, target_geometry=suggestion.point,
        assignee_id=assignee.id, assignee_name=assignee.name,
        created_by_id=principal.id, status="assigned", instructions=payload.instructions,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def _assignment_query():
    return select(ScoutAssignment).options(
        selectinload(ScoutAssignment.report).selectinload(AreaReport.area)
    ).order_by(ScoutAssignment.created_at.desc())


def list_assignments(db: Session, principal: Principal) -> list[AssignmentResponse]:
    query = _assignment_query()
    if principal.role == "bd-executive":
        query = query.where(ScoutAssignment.assignee_id == principal.id)
    assignments = db.scalars(query).all()
    property_ids = dict(db.execute(select(Property.assignment_id, Property.id).where(
        Property.assignment_id.in_([item.id for item in assignments])
    )).all()) if assignments else {}
    return [_serialize_assignment(item, property_ids.get(item.id)) for item in assignments]


def get_assignment(db: Session, assignment_id: UUID, principal: Principal) -> ScoutAssignment | None:
    assignment = db.scalar(_assignment_query().where(ScoutAssignment.id == assignment_id))
    if assignment and principal.role == "bd-executive" and assignment.assignee_id != principal.id:
        return None
    return assignment


def _serialize_assignment(item: ScoutAssignment, property_id: UUID | None = None) -> AssignmentResponse:
    point = to_shape(item.target_geometry)
    return AssignmentResponse(
        id=item.id, area_report_id=item.area_report_id, area_name=item.report.area.name,
        suggestion_id=item.suggestion_id, target_label=item.target_label, latitude=point.y,
        longitude=point.x, assignee_id=item.assignee_id, assignee_name=item.assignee_name,
        status=item.status, instructions=item.instructions, property_id=property_id, created_at=item.created_at,
    )


def capture_property(
    db: Session, assignment: ScoutAssignment, payload: PropertyCapture,
    principal: Principal, photos: list[StoredPhoto], settings: Settings | None = None,
) -> Property:
    settings = settings or get_settings()
    point = Point(payload.longitude, payload.latitude)
    existing = db.scalar(select(Property.id).where(
        func.ST_DWithin(cast(Property.location, Geography), cast(from_shape(point, srid=4326), Geography), settings.property_duplicate_radius_m)
    ).limit(1))
    point_element = from_shape(point, srid=4326)
    distance = db.scalar(select(func.ST_Distance(
        cast(ScoutAssignment.target_geometry, Geography), cast(point_element, Geography)
    )).where(ScoutAssignment.id == assignment.id))
    inside_area = db.scalar(select(func.ST_Covers(Area.geometry, point_element)).join(
        AreaReport, AreaReport.area_id == Area.id
    ).where(AreaReport.id == assignment.area_report_id))
    flags: list[str] = []
    if existing:
        flags.append("Possible duplicate within 75 m; manager review required.")
    if not inside_area:
        flags.append("GPS pin is outside the assigned M1 area.")
    if distance is not None and distance > settings.property_assignment_distance_m:
        flags.append(f"GPS pin is {distance / 1000:.1f} km from the assigned hotspot.")
    prop = Property(
        assignment_id=assignment.id, captured_by_id=principal.id, location=point_element,
        duplicate_review=bool(existing), suspicious_gps=not inside_area or bool(distance and distance > settings.property_assignment_distance_m),
        review_flags=flags, stage="scouted", **payload.model_dump(exclude={"latitude", "longitude"}),
    )
    prop.photos = [PropertyPhoto(**photo.__dict__) for photo in photos]
    db.add(prop)
    db.flush()
    evaluation = evaluate_property(prop, settings)
    prop.evaluations.append(PropertyEvaluation(property_id=prop.id, version=1, scoring_version=SCORING_VERSION, **evaluation))
    prop.transitions.append(PropertyStageTransition(
        property_id=prop.id, from_stage=None, to_stage="scouted", actor_id=principal.id,
        actor_name=principal.name, reason="Property captured in the field.",
    ))
    assignment.status = "captured"
    db.commit()
    return get_property_record(db, prop.id)  # type: ignore[return-value]


def evaluate_property(prop: Property, settings: Settings) -> dict:
    point = to_shape(prop.location)
    radius_degrees = settings.property_nearby_radius_m / 111_320
    polygon = point.buffer(radius_degrees)
    geometry = MultiPolygon([polygon]) if isinstance(polygon, Polygon) else polygon
    osm = fetch_osm_signals(geometry, f"property-{prop.id}", settings)
    stores = fetch_store_signals(geometry, settings)
    fetched_at = max(osm.fetched_at, stores.fetched_at, datetime.now(UTC))
    result = score_property(
        rent_monthly=prop.rent_monthly, size_sq_ft=prop.size_sq_ft, frontage_ft=prop.frontage_ft,
        road_width_ft=prop.road_width_ft, visibility_rating=prop.visibility_rating,
        condition_rating=prop.condition_rating, parking_available=prop.parking_available,
        power_backup=prop.power_backup, water_available=prop.water_available,
        osm_counts=osm.counts, osm_source=osm.source, osm_kind=osm.evidence_kind,
        osm_limitations=osm.limitations, nearest_store_km=stores.nearest_store_km,
        store_source=stores.source, store_kind=stores.evidence_kind,
        store_limitations=stores.limitations, fetched_at=fetched_at,
    )
    result["source_snapshot_at"] = fetched_at
    return result


def _property_query():
    return select(Property).options(
        selectinload(Property.assignment).selectinload(ScoutAssignment.report).selectinload(AreaReport.area),
        selectinload(Property.photos), selectinload(Property.evaluations), selectinload(Property.transitions),
    )


def get_property_record(db: Session, property_id: UUID) -> Property | None:
    return db.scalar(_property_query().where(Property.id == property_id))


def list_properties(db: Session, principal: Principal) -> list[PropertyResponse]:
    query = _property_query().order_by(Property.created_at.desc())
    if principal.role == "bd-executive":
        query = query.join(ScoutAssignment).where(ScoutAssignment.assignee_id == principal.id)
    return [serialize_property(item) for item in db.scalars(query).unique().all()]


def serialize_property(prop: Property) -> PropertyResponse:
    point = to_shape(prop.location)
    return PropertyResponse(
        id=prop.id, assignment_id=prop.assignment_id, area_report_id=prop.assignment.area_report_id,
        area_name=prop.assignment.report.area.name, target_label=prop.assignment.target_label,
        assignee_name=prop.assignment.assignee_name, latitude=point.y, longitude=point.x,
        address=prop.address, rent_monthly=prop.rent_monthly, size_sq_ft=prop.size_sq_ft,
        frontage_ft=prop.frontage_ft, road_width_ft=prop.road_width_ft,
        property_type=prop.property_type, floor_level=prop.floor_level,
        visibility_rating=prop.visibility_rating, condition_rating=prop.condition_rating,
        parking_available=prop.parking_available, power_backup=prop.power_backup,
        water_available=prop.water_available, notes=prop.notes, stage=prop.stage,
        duplicate_review=prop.duplicate_review, suspicious_gps=prop.suspicious_gps,
        review_flags=prop.review_flags,
        photos=[{"id": photo.id, "filename": photo.original_filename, "content_type": photo.content_type,
                 "byte_size": photo.byte_size, "url": f"/api/v1/properties/{prop.id}/photos/{photo.id}"} for photo in prop.photos],
        evaluations=prop.evaluations, transitions=prop.transitions, created_at=prop.created_at,
    )


def move_stage(db: Session, prop: Property, target: str, reason: str, principal: Principal) -> Property:
    validate_transition(prop.stage, target)
    previous = prop.stage
    prop.stage = target
    prop.transitions.append(PropertyStageTransition(
        property_id=prop.id, from_stage=previous, to_stage=target,
        actor_id=principal.id, actor_name=principal.name, reason=reason,
    ))
    db.commit()
    return get_property_record(db, prop.id)  # type: ignore[return-value]


def photo_path(photo: PropertyPhoto, settings: Settings | None = None) -> Path:
    return Path((settings or get_settings()).property_photo_storage_path) / photo.storage_key
