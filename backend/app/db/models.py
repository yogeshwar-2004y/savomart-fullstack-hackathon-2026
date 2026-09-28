import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func
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
    scoring_version: Mapped[str] = mapped_column(String(40), default="area-fitness-v1")
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


class ExternalDataSnapshot(Base):
    __tablename__ = "external_data_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    cache_key: Mapped[str] = mapped_column(String(220), index=True)
    source_name: Mapped[str] = mapped_column(String(120))
    geography: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
