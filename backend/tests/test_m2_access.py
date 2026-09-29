import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.api.routes.m2 as m2_route
from app.db.dependencies import get_db
from app.main import app

EXECUTIVE = {"X-Demo-Role": "bd-executive", "X-Demo-User-Id": "bd-executive-1"}
MANAGER = {"X-Demo-Role": "bd-manager", "X-Demo-User-Id": "bd-manager-1"}


def property_payload(**overrides):
    payload = {
        "latitude": 12.98,
        "longitude": 80.22,
        "address": "Test property, Velachery",
        "rent_monthly": 120_000,
        "size_sq_ft": 2_000,
        "property_type": "street_shop",
        "floor_level": "ground",
        "visibility_rating": 4,
        "condition_rating": 4,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: object()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_executive_cannot_read_another_executives_property(monkeypatch) -> None:
    property_id = uuid4()
    record = SimpleNamespace(assignment=SimpleNamespace(assignee_id="bd-executive-2"))
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(m2_route, "get_property_record", lambda _db, _id: record)
    try:
        response = TestClient(app).get(
            f"/api/v1/properties/{property_id}",
            headers={"X-Demo-Role": "bd-executive", "X-Demo-User-Id": "bd-executive-1"},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 404


def test_m2_requires_explicit_identity_headers() -> None:
    response = TestClient(app).get("/api/v1/properties")
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("overrides", "expected_field"),
    [
        ({"rent_monthly": 0}, "rent_monthly"),
        ({"latitude": 0}, "latitude"),
        ({"longitude": 0}, "longitude"),
    ],
)
def test_property_capture_rejects_invalid_rent_and_coordinates(
    monkeypatch, client, overrides, expected_field,
) -> None:
    monkeypatch.setattr(m2_route, "get_assignment", lambda *_args: SimpleNamespace(status="assigned"))

    response = client.post(
        f"/api/v1/scout-assignments/{uuid4()}/properties",
        headers=EXECUTIVE,
        data={"payload": json.dumps(property_payload(**overrides))},
    )

    assert response.status_code == 422
    assert expected_field in str(response.json()["detail"])


def test_executive_cannot_submit_to_another_executives_assignment(monkeypatch, client) -> None:
    monkeypatch.setattr(m2_route, "get_assignment", lambda *_args: None)

    response = client.post(
        f"/api/v1/scout-assignments/{uuid4()}/properties",
        headers=EXECUTIVE,
        data={"payload": json.dumps(property_payload())},
    )

    assert response.status_code == 404


def test_assignment_rejects_duplicate_property_submission(monkeypatch, client) -> None:
    monkeypatch.setattr(m2_route, "get_assignment", lambda *_args: SimpleNamespace(status="captured"))

    response = client.post(
        f"/api/v1/scout-assignments/{uuid4()}/properties",
        headers=EXECUTIVE,
        data={"payload": json.dumps(property_payload())},
    )

    assert response.status_code == 409


def test_property_capture_rejects_invalid_upload(monkeypatch, client) -> None:
    monkeypatch.setattr(m2_route, "get_assignment", lambda *_args: SimpleNamespace(status="assigned"))

    response = client.post(
        f"/api/v1/scout-assignments/{uuid4()}/properties",
        headers=EXECUTIVE,
        data={"payload": json.dumps(property_payload())},
        files={"photos": ("fake.jpg", b"not an image", "image/jpeg")},
    )

    assert response.status_code == 422
    assert "valid JPEG" in response.json()["detail"]


def test_property_stage_endpoint_rejects_illegal_transition(monkeypatch, client) -> None:
    monkeypatch.setattr(m2_route, "get_property_record", lambda *_args: SimpleNamespace(stage="scouted"))
    monkeypatch.setattr(
        m2_route,
        "move_stage",
        lambda *_args: (_ for _ in ()).throw(ValueError("Cannot move property from scouted to approved")),
    )

    response = client.post(
        f"/api/v1/properties/{uuid4()}/stage",
        headers=MANAGER,
        json={"stage": "approved", "reason": "Skip directly to approval"},
    )

    assert response.status_code == 409
    assert "Cannot move" in response.json()["detail"]
