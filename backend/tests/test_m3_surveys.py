from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import MultiPolygon, box

import app.api.routes.m3 as m3_route
from app.db.dependencies import get_db
from app.m3_surveys.schemas import LaneSubmissionCreate, LaneSubmissionResponse
from app.m3_surveys.service import geometry_overlap_ratio, zones_overlap
from app.main import app
from app.scoring.property_v2 import SCORING_VERSION, score_with_catchment

SURVEY_EXECUTIVE = {
    "X-Demo-Role": "survey-executive",
    "X-Demo-User-Id": "survey-executive-1",
}


def multi(min_x: float, min_y: float, max_x: float, max_y: float) -> MultiPolygon:
    return MultiPolygon([box(min_x, min_y, max_x, max_y)])


def test_overlap_ratio_supports_reuse_threshold() -> None:
    target = multi(80.20, 12.90, 80.30, 13.00)
    eighty_percent = multi(80.20, 12.90, 80.28, 13.00)
    assert geometry_overlap_ratio(target, eighty_percent) == pytest.approx(0.8, abs=0.00002)
    assert geometry_overlap_ratio(target, multi(80.31, 12.90, 80.32, 13.00)) == 0


def test_union_of_recent_study_coverage_can_meet_reuse_threshold() -> None:
    target = multi(80.20, 12.90, 80.30, 13.00)
    west = multi(80.20, 12.90, 80.24, 13.00)
    east = multi(80.24, 12.90, 80.28, 13.00)
    combined = MultiPolygon([*west.geoms, *east.geoms])

    assert geometry_overlap_ratio(target, west) == pytest.approx(0.4, abs=0.002)
    assert geometry_overlap_ratio(target, east) == pytest.approx(0.4, abs=0.002)
    assert geometry_overlap_ratio(target, combined) == pytest.approx(0.8, abs=0.002)
    assert geometry_overlap_ratio(target, multi(80.31, 12.90, 80.32, 13.00)) == 0


def test_zone_overlap_rejects_area_but_allows_shared_edge() -> None:
    left = multi(80.20, 12.90, 80.25, 13.00)
    touching = multi(80.25, 12.90, 80.30, 13.00)
    overlapping = multi(80.24, 12.90, 80.30, 13.00)
    assert zones_overlap(left, touching) is False
    assert zones_overlap(left, overlapping) is True


def test_lane_submission_validates_chennai_coordinates_and_counts() -> None:
    common = {
        "client_submission_id": uuid4(),
        "lane_name": "Velachery Main Road",
        "latitude": 12.98,
        "longitude": 80.22,
        "gps_accuracy_m": 20,
        "observed_at": datetime.now(UTC),
        "residential_units": 50,
        "commercial_units": 12,
        "pedestrian_activity": 4,
        "vehicle_activity": 3,
    }
    LaneSubmissionCreate.model_validate(common)
    with pytest.raises(ValueError):
        LaneSubmissionCreate.model_validate({**common, "latitude": 0})
    with pytest.raises(ValueError):
        LaneSubmissionCreate.model_validate({**common, "residential_units": -1})


def test_survey_executive_cannot_submit_another_executives_zone(monkeypatch) -> None:
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(m3_route, "get_zone_for_principal", lambda *_args: None)
    try:
        response = TestClient(app).post(
            f"/api/v1/survey-zones/{uuid4()}/submissions",
            headers=SURVEY_EXECUTIVE,
            json={
                "client_submission_id": str(uuid4()),
                "lane_name": "Velachery Main Road",
                "latitude": 12.98,
                "longitude": 80.22,
                "gps_accuracy_m": 20,
                "observed_at": datetime.now(UTC).isoformat(),
                "residential_units": 50,
                "commercial_units": 12,
                "pedestrian_activity": 4,
                "vehicle_activity": 3,
            },
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 404


def test_duplicate_submission_returns_existing_capture(monkeypatch) -> None:
    submission_id = uuid4()
    zone = SimpleNamespace(id=uuid4(), status="assigned")
    existing = SimpleNamespace(client_submission_id=submission_id)
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(m3_route, "get_zone_for_principal", lambda *_args: zone)
    monkeypatch.setattr(m3_route, "submit_lane", lambda *_args: existing)
    monkeypatch.setattr(
        m3_route,
        "serialize_lane",
        lambda item: LaneSubmissionResponse(
            id=uuid4(), client_submission_id=item.client_submission_id, zone_id=zone.id,
            lane_name="Velachery Main Road", latitude=12.98, longitude=80.22,
            gps_accuracy_m=20, observed_at=datetime.now(UTC), residential_units=50,
            commercial_units=12, pedestrian_activity=4, vehicle_activity=3,
            notes=None, status="submitted", evidence_kind="field-survey", location_mismatch=False,
            mismatch_distance_m=0, created_at=datetime.now(UTC),
        ),
    )
    payload = {
        "client_submission_id": str(submission_id),
        "lane_name": "Velachery Main Road",
        "latitude": 12.98,
        "longitude": 80.22,
        "gps_accuracy_m": 20,
        "observed_at": datetime.now(UTC).isoformat(),
        "residential_units": 50,
        "commercial_units": 12,
        "pedestrian_activity": 4,
        "vehicle_activity": 3,
    }
    try:
        first = TestClient(app).post(
            f"/api/v1/survey-zones/{zone.id}/submissions", headers=SURVEY_EXECUTIVE, json=payload
        )
        second = TestClient(app).post(
            f"/api/v1/survey-zones/{zone.id}/submissions", headers=SURVEY_EXECUTIVE, json=payload
        )
    finally:
        app.dependency_overrides.clear()
    assert first.status_code == second.status_code == 201
    assert first.json()["client_submission_id"] == second.json()["client_submission_id"] == str(submission_id)


def test_catchment_score_is_versioned_and_reconciles() -> None:
    previous = [{
        "key": "base", "label": "Base", "raw_value": 1, "raw_unit": "value",
        "normalized_value": 0.8, "weight": 1.0, "contribution": 80.0,
        "source": "M2", "fetched_at": datetime.now(UTC).isoformat(),
        "evidence_kind": "captured", "transformation": "base", "limitations": "none",
    }]
    summary = {
        "observation_count": 2,
        "residential_units": 160,
        "commercial_units": 40,
        "average_pedestrian_activity": 5,
        "average_vehicle_activity": 5,
        "coverage_percent": 100,
        "location_mismatch_count": 0,
        "evidence_kind": "demo",
    }
    result = score_with_catchment(previous, summary, datetime.now(UTC))
    assert SCORING_VERSION == "property-fitness-v2-catchment"
    assert result["score"] == 82.0
    assert sum(metric["weight"] for metric in result["metrics"]) == pytest.approx(1)
    assert result["score"] == round(sum(metric["contribution"] for metric in result["metrics"]), 1)
    assert result["metrics"][-1]["evidence_kind"] == "demo"
