import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Area(Base):
    __tablename__ = "areas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160))
    query: Mapped[str | None] = mapped_column(String(160))
    selection_method: Mapped[str] = mapped_column(String(24))
    geometry = mapped_column(Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False)
    area_sq_km: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(160), default="User-selected map area")
    source_id: Mapped[str] = mapped_column(String(220), default="legacy:unknown")
    source_url: Mapped[str | None] = mapped_column(Text)
    source_license: Mapped[str | None] = mapped_column(String(120))
    boundary_type: Mapped[str] = mapped_column(String(32), default="user-selected")
    boundary_lookup_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_official: Mapped[bool] = mapped_column(Boolean, default=False)
    is_approximate: Mapped[bool] = mapped_column(Boolean, default=False)
    approximation_warning: Mapped[str | None] = mapped_column(Text)
    resolver_cache_age_seconds: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AreaAnalysis(Base):
    __tablename__ = "area_analyses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    area_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("areas.id"), index=True)
    requested_by_role: Mapped[str] = mapped_column(String(32), default="bd-manager")
    status: Mapped[str] = mapped_column(String(24), default="queued")
    scoring_version: Mapped[str] = mapped_column(String(40), default="area-fitness-v2")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    area: Mapped[Area] = relationship()


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("area_analyses.id"), index=True)
    report_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("area_reports.id"))
    status: Mapped[str] = mapped_column(String(24), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    status_detail: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    error_code: Mapped[str | None] = mapped_column(String(80))
    retryable: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AreaReport(Base):
    __tablename__ = "area_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("area_analyses.id"), unique=True)
    area_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("areas.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    score: Mapped[float] = mapped_column(Float)
    rating: Mapped[str] = mapped_column(String(40))
    summary: Mapped[str] = mapped_column(Text)
    scoring_version: Mapped[str] = mapped_column(String(40))
    source_snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_cached_evidence: Mapped[bool] = mapped_column(Boolean, default=False)
    cache_age_seconds: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    area: Mapped[Area] = relationship()
    metrics: Mapped[list["AreaMetricEvidence"]] = relationship(
        cascade="all, delete-orphan", order_by="AreaMetricEvidence.category"
    )
    suggestions: Mapped[list["ScoutingSuggestion"]] = relationship(
        cascade="all, delete-orphan", order_by="ScoutingSuggestion.rank"
    )


class AreaMetricEvidence(Base):
    __tablename__ = "area_metric_evidence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("area_reports.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(100))
    raw_value: Mapped[float | None] = mapped_column(Float)
    raw_unit: Mapped[str] = mapped_column(String(40))
    normalized_value: Mapped[float] = mapped_column(Float)
    weight: Mapped[float] = mapped_column(Float)
    contribution: Mapped[float] = mapped_column(Float)
    source_name: Mapped[str] = mapped_column(String(120))
    source_url: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    geography: Mapped[str] = mapped_column(Text)
    transformation: Mapped[str] = mapped_column(Text)
    limitations: Mapped[str] = mapped_column(Text)
    evidence_kind: Mapped[str] = mapped_column(String(24))
    cache_age_seconds: Mapped[int | None] = mapped_column(Integer)


class ScoutingSuggestion(Base):
    __tablename__ = "scouting_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("area_reports.id", ondelete="CASCADE"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(120))
    point = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=False)
    rationale: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB)


class ScoutAssignment(Base):
    __tablename__ = "scout_assignments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    area_report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("area_reports.id"), index=True)
    suggestion_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scouting_suggestions.id"), index=True)
    target_label: Mapped[str] = mapped_column(String(160))
    target_geometry = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=False)
    assignee_id: Mapped[str] = mapped_column(String(64), index=True)
    assignee_name: Mapped[str] = mapped_column(String(120))
    created_by_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="assigned")
    instructions: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    report: Mapped[AreaReport] = relationship()
    suggestion: Mapped[ScoutingSuggestion | None] = relationship()


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scout_assignments.id"), index=True)
    captured_by_id: Mapped[str] = mapped_column(String(64), index=True)
    location = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=False)
    address: Mapped[str] = mapped_column(String(240))
    rent_monthly: Mapped[float] = mapped_column(Float)
    size_sq_ft: Mapped[float] = mapped_column(Float)
    frontage_ft: Mapped[float | None] = mapped_column(Float)
    road_width_ft: Mapped[float | None] = mapped_column(Float)
    property_type: Mapped[str] = mapped_column(String(40))
    floor_level: Mapped[str] = mapped_column(String(40))
    visibility_rating: Mapped[int] = mapped_column(Integer)
    condition_rating: Mapped[int] = mapped_column(Integer)
    parking_available: Mapped[bool] = mapped_column(Boolean, default=False)
    power_backup: Mapped[bool] = mapped_column(Boolean, default=False)
    water_available: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    stage: Mapped[str] = mapped_column(String(32), default="scouted", index=True)
    duplicate_review: Mapped[bool] = mapped_column(Boolean, default=False)
    suspicious_gps: Mapped[bool] = mapped_column(Boolean, default=False)
    review_flags: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    assignment: Mapped[ScoutAssignment] = relationship()
    photos: Mapped[list["PropertyPhoto"]] = relationship(cascade="all, delete-orphan", order_by="PropertyPhoto.created_at")
    evaluations: Mapped[list["PropertyEvaluation"]] = relationship(cascade="all, delete-orphan", order_by="PropertyEvaluation.version")
    transitions: Mapped[list["PropertyStageTransition"]] = relationship(cascade="all, delete-orphan", order_by="PropertyStageTransition.created_at")


class PropertyPhoto(Base):
    __tablename__ = "property_photos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    storage_key: Mapped[str] = mapped_column(String(240), unique=True)
    original_filename: Mapped[str] = mapped_column(String(240))
    content_type: Mapped[str] = mapped_column(String(40))
    byte_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PropertyEvaluation(Base):
    __tablename__ = "property_evaluations"
    __table_args__ = (UniqueConstraint("property_id", "version", name="uq_property_evaluation_version"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    scoring_version: Mapped[str] = mapped_column(String(48))
    score: Mapped[float] = mapped_column(Float)
    rating: Mapped[str] = mapped_column(String(40))
    recommendation: Mapped[str] = mapped_column(Text)
    metrics: Mapped[list[Any]] = mapped_column(JSONB)
    insights: Mapped[list[Any]] = mapped_column(JSONB)
    risks: Mapped[list[Any]] = mapped_column(JSONB)
    limitations: Mapped[list[Any]] = mapped_column(JSONB)
    source_snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PropertyStageTransition(Base):
    __tablename__ = "property_stage_transitions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    from_stage: Mapped[str | None] = mapped_column(String(32))
    to_stage: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[str] = mapped_column(String(64))
    actor_name: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CatchmentStudy(Base):
    __tablename__ = "catchment_studies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("properties.id"), index=True)
    area_report_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("area_reports.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(24))
    target_label: Mapped[str] = mapped_column(String(200))
    target_geometry = mapped_column(Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False)
    survey_geometry = mapped_column(Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="requested", index=True)
    requested_by_id: Mapped[str] = mapped_column(String(64))
    requested_by_name: Mapped[str] = mapped_column(String(120))
    source_study_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("catchment_studies.id"))
    source_study_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    reuse_coverage: Mapped[float] = mapped_column(Float, default=0)
    reuse_age_days: Mapped[float | None] = mapped_column(Float)
    reuse_max_age_days: Mapped[int] = mapped_column(Integer)
    reuse_min_coverage: Mapped[float] = mapped_column(Float)
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    property: Mapped[Property | None] = relationship()
    area_report: Mapped[AreaReport | None] = relationship()
    source_study: Mapped["CatchmentStudy | None"] = relationship(remote_side="CatchmentStudy.id")
    zones: Mapped[list["SurveyZone"]] = relationship(
        back_populates="study", cascade="all, delete-orphan", order_by="SurveyZone.label"
    )


class SurveyZone(Base):
    __tablename__ = "survey_zones"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    study_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catchment_studies.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(120))
    geometry = mapped_column(Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False)
    assignee_id: Mapped[str] = mapped_column(String(64), index=True)
    assignee_name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(24), default="assigned", index=True)
    mismatch_review: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    study: Mapped[CatchmentStudy] = relationship(back_populates="zones")
    submissions: Mapped[list["LaneCapture"]] = relationship(
        cascade="all, delete-orphan", order_by="LaneCapture.observed_at"
    )


class LaneCapture(Base):
    __tablename__ = "lane_captures"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    zone_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("survey_zones.id", ondelete="CASCADE"), index=True
    )
    study_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catchment_studies.id", ondelete="CASCADE"), index=True
    )
    client_submission_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, index=True)
    submitted_by_id: Mapped[str] = mapped_column(String(64), index=True)
    submitted_by_name: Mapped[str] = mapped_column(String(120))
    lane_name: Mapped[str] = mapped_column(String(160))
    location = mapped_column(Geometry("POINT", srid=4326, spatial_index=False), nullable=False)
    gps_accuracy_m: Mapped[float] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    residential_units: Mapped[int] = mapped_column(Integer)
    commercial_units: Mapped[int] = mapped_column(Integer)
    pedestrian_activity: Mapped[int] = mapped_column(Integer)
    vehicle_activity: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="submitted")
    evidence_kind: Mapped[str] = mapped_column(String(24), default="field-survey")
    location_mismatch: Mapped[bool] = mapped_column(Boolean, default=False)
    mismatch_distance_m: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    zone: Mapped[SurveyZone] = relationship(back_populates="submissions")


class ExternalDataSnapshot(Base):
    __tablename__ = "external_data_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    cache_key: Mapped[str] = mapped_column(String(220), index=True)
    source_name: Mapped[str] = mapped_column(String(120))
    geography: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
