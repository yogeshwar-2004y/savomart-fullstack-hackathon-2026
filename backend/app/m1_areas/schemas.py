from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

SelectionMethod = Literal["locality", "pincode", "cells"]
JobStatus = Literal["queued", "fetching", "scoring", "completed", "failed"]


class AreaSearchResult(BaseModel):
    display_name: str
    selection_method: Literal["locality", "pincode"]
    query: str
    geometry: dict[str, Any]
    source: str
    limitations: str | None = None


class AreaSelection(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    query: str | None = Field(default=None, max_length=160)
    selection_method: SelectionMethod
    geometry: dict[str, Any]


class AnalysisCreate(BaseModel):
    area: AreaSelection


class AnalysisAccepted(BaseModel):
    analysis_id: UUID
    job_id: UUID
    status: JobStatus


class JobResponse(BaseModel):
    id: UUID
    analysis_id: UUID | None
    report_id: UUID | None
    status: JobStatus
    progress: int
    status_detail: str | None
    attempts: int
    error_code: str | None
    retryable: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


class MetricEvidenceResponse(BaseModel):
    key: str
    category: str
    label: str
    raw_value: float | None
    raw_unit: str
    normalized_value: float
    weight: float
    contribution: float
    source_name: str
    source_url: str | None
    fetched_at: datetime
    geography: str
    transformation: str
    limitations: str
    evidence_kind: str
    cache_age_seconds: int | None

    model_config = {"from_attributes": True}


class SuggestionResponse(BaseModel):
    rank: int
    label: str
    latitude: float
    longitude: float
    rationale: str
    evidence: dict[str, Any]


class ReportSummaryResponse(BaseModel):
    id: UUID
    area_id: UUID
    area_name: str
    score: float
    rating: str
    scoring_version: str
    created_at: datetime


class AreaReportResponse(ReportSummaryResponse):
    analysis_id: UUID
    title: str
    summary: str
    source_snapshot_at: datetime
    used_cached_evidence: bool
    cache_age_seconds: int | None
    selection_method: str
    area_sq_km: float
    geometry: dict[str, Any]
    metrics: list[MetricEvidenceResponse]
    suggestions: list[SuggestionResponse]


class ReportComparisonResponse(BaseModel):
    left: AreaReportResponse
    right: AreaReportResponse
    score_delta: float
    metric_deltas: dict[str, float]


class RetryResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    attempts: int


class SearchQuery(BaseModel):
    q: str = Field(min_length=2, max_length=120)
    method: Literal["locality", "pincode"] = "locality"

    @field_validator("q")
    @classmethod
    def validate_pincode(cls, value: str, info: Any) -> str:
        return value.strip()
