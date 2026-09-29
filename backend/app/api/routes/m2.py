import json
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import (
    DEMO_USERS,
    Principal,
    get_authenticated_principal,
    require_executive_principal,
    require_manager_principal,
)
from app.core.config import get_settings
from app.db.dependencies import get_db
from app.db.models import PropertyPhoto
from app.m2_properties.photos import InvalidPhoto, store_upload
from app.m2_properties.schemas import (
    AssigneeResponse,
    AssignmentCreate,
    AssignmentResponse,
    PropertyCapture,
    PropertyResponse,
    StageChange,
)
from app.m2_properties.service import (
    capture_property,
    create_assignment,
    get_assignment,
    get_property_record,
    list_assignments,
    list_properties,
    move_stage,
    photo_path,
    serialize_property,
)

router = APIRouter()


@router.get("/scout-assignments/assignees", response_model=list[AssigneeResponse])
def assignees(_principal: Annotated[Principal, Depends(require_manager_principal)]) -> list[AssigneeResponse]:
    return [AssigneeResponse(id=user.id, name=user.name) for user in DEMO_USERS.values() if user.role == "bd-executive"]


@router.post("/scout-assignments", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def assignment_create(
    payload: AssignmentCreate, db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_manager_principal)],
) -> AssignmentResponse:
    try:
        assignment = create_assignment(db, payload, principal)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return next(item for item in list_assignments(db, principal) if item.id == assignment.id)


@router.get("/scout-assignments", response_model=list[AssignmentResponse])
def assignment_list(
    db: Annotated[Session, Depends(get_db)], principal: Annotated[Principal, Depends(get_authenticated_principal)],
) -> list[AssignmentResponse]:
    if principal.role not in {"bd-manager", "bd-executive"}:
        raise HTTPException(status_code=403, detail="Property scouting role required")
    return list_assignments(db, principal)


@router.post("/scout-assignments/{assignment_id}/properties", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
def property_capture(
    assignment_id: UUID,
    payload: Annotated[str, Form()],
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_executive_principal)],
    photos: Annotated[list[UploadFile] | None, File()] = None,
) -> PropertyResponse:
    photos = photos or []
    assignment = get_assignment(db, assignment_id, principal)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment.status == "captured":
        raise HTTPException(status_code=409, detail="This assignment already has a captured property")
    try:
        capture = PropertyCapture.model_validate(json.loads(payload))
    except (json.JSONDecodeError, ValidationError) as exc:
        detail = exc.errors() if isinstance(exc, ValidationError) else "Property payload must be valid JSON"
        raise HTTPException(status_code=422, detail=detail) from exc
    if len(photos) > 8:
        raise HTTPException(status_code=422, detail="Upload at most 8 property photos")
    settings = get_settings()
    stored = []
    completed = False
    try:
        for item in photos:
            stored.append(
                store_upload(
                    item,
                    settings.property_photo_storage_path,
                    settings.property_photo_max_bytes,
                )
            )
        prop = capture_property(db, assignment, capture, principal, stored, settings)
        completed = True
    except InvalidPhoto as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        if not completed:
            for item in stored:
                (Path(settings.property_photo_storage_path) / item.storage_key).unlink(missing_ok=True)
    return serialize_property(prop)


@router.get("/properties", response_model=list[PropertyResponse])
def property_list(
    db: Annotated[Session, Depends(get_db)], principal: Annotated[Principal, Depends(get_authenticated_principal)],
) -> list[PropertyResponse]:
    if principal.role not in {"bd-manager", "bd-executive"}:
        raise HTTPException(status_code=403, detail="Property scouting role required")
    return list_properties(db, principal)


def _authorized_property(db: Session, property_id: UUID, principal: Principal):
    prop = get_property_record(db, property_id)
    if not prop or (principal.role == "bd-executive" and prop.assignment.assignee_id != principal.id):
        raise HTTPException(status_code=404, detail="Property not found")
    if principal.role not in {"bd-manager", "bd-executive"}:
        raise HTTPException(status_code=403, detail="Property scouting role required")
    return prop


@router.get("/properties/{property_id}", response_model=PropertyResponse)
def property_detail(
    property_id: UUID, db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_authenticated_principal)],
) -> PropertyResponse:
    return serialize_property(_authorized_property(db, property_id, principal))


@router.post("/properties/{property_id}/stage", response_model=PropertyResponse)
def property_stage(
    property_id: UUID, payload: StageChange, db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(require_manager_principal)],
) -> PropertyResponse:
    prop = get_property_record(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    try:
        return serialize_property(move_stage(db, prop, payload.stage, payload.reason, principal))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/properties/{property_id}/photos/{photo_id}")
def property_photo(
    property_id: UUID, photo_id: UUID, db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_authenticated_principal)],
) -> FileResponse:
    _authorized_property(db, property_id, principal)
    photo = db.scalar(select(PropertyPhoto).where(PropertyPhoto.id == photo_id, PropertyPhoto.property_id == property_id))
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    path = photo_path(photo)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Photo file is unavailable")
    return FileResponse(path, media_type=photo.content_type, filename=photo.original_filename)
