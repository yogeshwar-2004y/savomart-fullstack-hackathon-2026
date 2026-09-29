from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class StudyCreate(BaseModel):
    target_type: Literal["property", "area_report"]
    target_id: UUID


class ZonePlan(BaseModel):
    zone_count: int = Field(ge=1, le=8)
    assignee_ids: list[str] = Field(min_length=1, max_length=8)


class LaneSubmissionCreate(BaseModel):
    client_submission_id: UUID
    lane_name: str = Field(min_length=2, max_length=160)
    latitude: float = Field(ge=12.75, le=13.30)
    longitude: float = Field(ge=80.05, le=80.35)
    gps_accuracy_m: float = Field(gt=0, le=5000)
    observed_at: datetime
    residential_units: int = Field(ge=0, le=10_000)
    commercial_units: int = Field(ge=0, le=5_000)
    pedestrian_activity: int = Field(ge=1, le=5)
    vehicle_activity: int = Field(ge=1, le=5)
    notes: str | None = Field(default=None, max_length=3000)
    status: Literal["submitted"] = "submitted"
    evidence_kind: Literal["field-survey", "demo"] = "field-survey"

    @field_validator("lane_name")
    @classmethod
    def clean_lane_name(cls, value: str) -> str:
        return value.strip()


class LaneSubmissionResponse(BaseModel):
    id: UUID
    client_submission_id: UUID
    zone_id: UUID
    lane_name: str
    latitude: float
    longitude: float
    gps_accuracy_m: float
    observed_at: datetime
    residential_units: int
    commercial_units: int
    pedestrian_activity: int
    vehicle_activity: int
    notes: str | None
    status: str
    evidence_kind: str
    location_mismatch: bool
    mismatch_distance_m: float
    created_at: datetime


class SurveyZoneResponse(BaseModel):
    id: UUID
    study_id: UUID
    study_label: str
    label: str
    geometry: dict[str, Any]
    assignee_id: str
    assignee_name: str
    status: str
    mismatch_review: bool
    submission_count: int
    submissions: list[LaneSubmissionResponse]
    created_at: datetime
    completed_at: datetime | None


class CatchmentStudyResponse(BaseModel):
    id: UUID
    property_id: UUID | None
    area_report_id: UUID | None
    target_type: str
    target_label: str
    target_geometry: dict[str, Any]
    survey_geometry: dict[str, Any]
    status: str
    source_study_id: UUID | None
    source_study_ids: list[UUID]
    reuse_coverage: float
    reuse_age_days: float | None
    reuse_max_age_days: int
    reuse_min_coverage: float
    progress_percent: float
    summary: dict[str, Any] | None
    zones: list[SurveyZoneResponse]
    created_at: datetime
    completed_at: datetime | None


class SurveyAssigneeResponse(BaseModel):
    id: str
    name: str
