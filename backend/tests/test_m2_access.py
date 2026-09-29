from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.dependencies import get_db
from app.main import app
import app.api.routes.m2 as m2_route


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
