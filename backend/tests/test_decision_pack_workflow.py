from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.api.routes.m2 as m2_route
from app.db.dependencies import get_db
from app.main import app

MANAGER = {"X-Demo-Role": "bd-manager", "X-Demo-User-Id": "bd-manager-1"}
EXECUTIVE = {"X-Demo-Role": "bd-executive", "X-Demo-User-Id": "bd-executive-1"}


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: object()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_stage_transition_requires_reason(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """
    Verify transition requests require a non-empty audit reason.
    """
    monkeypatch.setattr(m2_route, "get_property_record", lambda *_args: SimpleNamespace(stage="scouted"))

    response = client.post(
        f"/api/v1/properties/{uuid4()}/stage",
        headers=MANAGER,
        json={"stage": "shortlisted", "reason": "   "},
    )
    assert response.status_code == 422


def test_illegal_state_transition_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """
    Verify state machine rejects invalid jumps (e.g. scouted -> approved).
    """
    monkeypatch.setattr(m2_route, "get_property_record", lambda *_args: SimpleNamespace(stage="scouted"))
    monkeypatch.setattr(
        m2_route,
        "move_stage",
        lambda *_args: (_ for _ in ()).throw(ValueError("Cannot move property from scouted to approved")),
    )

    response = client.post(
        f"/api/v1/properties/{uuid4()}/stage",
        headers=MANAGER,
        json={"stage": "approved", "reason": "Attempting jump without catchment"},
    )
    assert response.status_code == 409
    assert "Cannot move" in response.json()["detail"]


def test_rbac_prevents_executive_stage_transitions(client: TestClient):
    """
    Verify BD Executive role cannot perform manager stage transitions.
    """
    response = client.post(
        f"/api/v1/properties/{uuid4()}/stage",
        headers=EXECUTIVE,
        json={"stage": "approved", "reason": "Unauthorized attempt"},
    )
    assert response.status_code == 403
