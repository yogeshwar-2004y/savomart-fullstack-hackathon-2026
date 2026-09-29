from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

PipelineStage = Literal["scouted", "shortlisted", "survey_requested", "under_review", "approved", "rejected"]


class AssigneeResponse(BaseModel):
    id: str
    name: str


class AssignmentCreate(BaseModel):
    area_report_id: UUID
    suggestion_id: UUID
    assignee_id: str
    instructions: str | None = Field(default=None, max_length=1000)


class AssignmentResponse(BaseModel):
    id: UUID
    area_report_id: UUID
    area_name: str
    suggestion_id: UUID | None
    target_label: str
    latitude: float
    longitude: float
    assignee_id: str
    assignee_name: str
    status: str
    instructions: str | None
    property_id: UUID | None = None
    created_at: datetime


class PropertyCapture(BaseModel):
    latitude: float = Field(ge=12.75, le=13.30)
    longitude: float = Field(ge=80.05, le=80.35)
    address: str = Field(min_length=5, max_length=240)
    rent_monthly: float = Field(gt=0, le=10_000_000)
    size_sq_ft: float = Field(ge=100, le=100_000)
    frontage_ft: float | None = Field(default=None, ge=1, le=1000)
    road_width_ft: float | None = Field(default=None, ge=1, le=1000)
    property_type: Literal["street_shop", "standalone", "mall_unit", "mixed_use"]
    floor_level: Literal["ground", "ground_plus_one", "upper_floor", "basement"]
    visibility_rating: int = Field(ge=1, le=5)
    condition_rating: int = Field(ge=1, le=5)
    parking_available: bool = False
    power_backup: bool = False
    water_available: bool = False
    notes: str | None = Field(default=None, max_length=3000)

    @field_validator("address")
    @classmethod
    def clean_address(cls, value: str) -> str:
        return value.strip()


class PhotoResponse(BaseModel):
    id: UUID
    filename: str
    content_type: str
    byte_size: int
    url: str


class EvaluationResponse(BaseModel):
    id: UUID
    version: int
    scoring_version: str
    score: float
    rating: str
    recommendation: str
    metrics: list[dict[str, Any]]
    insights: list[str]
    risks: list[str]
    limitations: list[str]
    source_snapshot_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class TransitionResponse(BaseModel):
    id: UUID
    from_stage: str | None
    to_stage: str
    actor_name: str
    reason: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PropertyResponse(BaseModel):
    id: UUID
    assignment_id: UUID
    area_report_id: UUID
    area_name: str
    target_label: str
    assignee_name: str
    latitude: float
    longitude: float
    address: str
    rent_monthly: float
    size_sq_ft: float
    frontage_ft: float | None
    road_width_ft: float | None
    property_type: str
    floor_level: str
    visibility_rating: int
    condition_rating: int
    parking_available: bool
    power_backup: bool
    water_available: bool
    notes: str | None
    stage: PipelineStage
    duplicate_review: bool
    suspicious_gps: bool
    review_flags: list[str]
    photos: list[PhotoResponse]
    evaluations: list[EvaluationResponse]
    transitions: list[TransitionResponse]
    created_at: datetime


class StageChange(BaseModel):
    stage: PipelineStage
    reason: str = Field(min_length=3, max_length=1000)

