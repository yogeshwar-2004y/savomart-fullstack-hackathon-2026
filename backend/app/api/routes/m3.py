from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    DEMO_USERS,
    Principal,
    get_authenticated_principal,
    require_manager_principal,
    require_survey_executive_principal,
    require_survey_manager_principal,
)
from app.db.dependencies import get_db
from app.m3_surveys.schemas import (
    CatchmentStudyResponse,
    LaneSubmissionCreate,
    LaneSubmissionResponse,
    StudyCreate,
    SurveyAssigneeResponse,
    SurveyZoneResponse,
    ZonePlan,
)
from app.m3_surveys.service import (
    complete_zone,
    create_study,
    get_study,
    get_zone_for_principal,
    list_studies,
    list_zones,
    plan_zones,
    serialize_lane,
    serialize_study,
    serialize_zone,
    submit_lane,
)

router = APIRouter()


@router.get("/catchment-studies/assignees", response_model=list[SurveyAssigneeResponse])
def survey_assignees(
    _principal: Annotated[Principal, Depends(require_survey_manager_principal)],
) -> list[SurveyAssigneeResponse]:
    return [
        SurveyAssigneeResponse(id=user.id, name=user.name)
        for user in DEMO_USERS.values()
        if user.role == "survey-executive"
    ]


@router.post(
    "/catchment-studies",
    response_model=CatchmentStudyResponse,
    status_code=status.HTTP_201_CREATED,
)
def catchment_create(
    payload: StudyCreate,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_manager_principal)],
) -> CatchmentStudyResponse:
    try:
        return serialize_study(create_study(db, payload, principal))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/catchment-studies", response_model=list[CatchmentStudyResponse])
def catchment_list(
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_authenticated_principal)],
) -> list[CatchmentStudyResponse]:
    if principal.role not in {"bd-manager", "survey-manager", "survey-executive"}:
        raise HTTPException(status_code=403, detail="Catchment operations role required")
    return [serialize_study(item) for item in list_studies(db, principal)]


@router.get("/catchment-studies/{study_id}", response_model=CatchmentStudyResponse)
def catchment_detail(
    study_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_authenticated_principal)],
) -> CatchmentStudyResponse:
    study = get_study(db, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Catchment study not found")
    if principal.role == "survey-executive" and not any(zone.assignee_id == principal.id for zone in study.zones):
        raise HTTPException(status_code=404, detail="Catchment study not found")
    if principal.role not in {"bd-manager", "survey-manager", "survey-executive"}:
        raise HTTPException(status_code=403, detail="Catchment operations role required")
    return serialize_study(study)


@router.post("/catchment-studies/{study_id}/zones", response_model=CatchmentStudyResponse)
def catchment_plan_zones(
    study_id: UUID,
    payload: ZonePlan,
    db: Annotated[Session, Depends(get_db)],
    _principal: Annotated[Principal, Depends(require_survey_manager_principal)],
) -> CatchmentStudyResponse:
    study = get_study(db, study_id)
    if not study:
        raise HTTPException(status_code=404, detail="Catchment study not found")
    try:
        return serialize_study(plan_zones(db, study, payload))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/survey-zones", response_model=list[SurveyZoneResponse])
def survey_zone_list(
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_authenticated_principal)],
) -> list[SurveyZoneResponse]:
    if principal.role not in {"survey-manager", "survey-executive"}:
        raise HTTPException(status_code=403, detail="Survey operations role required")
    return [serialize_zone(item) for item in list_zones(db, principal)]


@router.post(
    "/survey-zones/{zone_id}/submissions",
    response_model=LaneSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def lane_submit(
    zone_id: UUID,
    payload: LaneSubmissionCreate,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_survey_executive_principal)],
) -> LaneSubmissionResponse:
    zone = get_zone_for_principal(db, zone_id, principal)
    if not zone:
        raise HTTPException(status_code=404, detail="Survey zone not found")
    if zone.status == "completed":
        raise HTTPException(status_code=409, detail="Survey zone is already completed")
    try:
        return serialize_lane(submit_lane(db, zone, payload, principal))
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/survey-zones/{zone_id}/complete", response_model=CatchmentStudyResponse)
def survey_zone_complete(
    zone_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_survey_executive_principal)],
) -> CatchmentStudyResponse:
    zone = get_zone_for_principal(db, zone_id, principal)
    if not zone:
        raise HTTPException(status_code=404, detail="Survey zone not found")
    try:
        return serialize_study(complete_zone(db, zone))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
