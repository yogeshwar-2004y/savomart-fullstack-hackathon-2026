from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.routes import reports as reports_route
from app.db.dependencies import get_db
from app.main import app
from app.m1_areas.schemas import AreaReportResponse


def test_saved_report_endpoint_returns_evidence_and_geometry(monkeypatch) -> None:
    report_id, area_id, analysis_id = uuid4(), uuid4(), uuid4()
    now = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
    saved = AreaReportResponse(
        id=report_id, area_id=area_id, analysis_id=analysis_id, area_name="Velachery",
        title="Velachery Area Fitness Report", score=64.2, rating="Promising",
        summary="Deterministic summary", scoring_version="area-fitness-v1", created_at=now,
        source_snapshot_at=now, used_cached_evidence=False, cache_age_seconds=None,
        selection_method="locality", area_sq_km=4.2,
        geometry={"type": "MultiPolygon", "coordinates": [[[[80.2, 12.97], [80.21, 12.97], [80.21, 12.98], [80.2, 12.97]]]]},
        metrics=[{
            "key": "amenity_density", "category": "amenities", "label": "Mapped amenities",
            "raw_value": 4, "raw_unit": "features per sq km", "normalized_value": 0.2,
            "weight": 0.2, "contribution": 4, "source_name": "OpenStreetMap", "source_url": None,
            "fetched_at": now, "geography": "Velachery polygon", "transformation": "documented",
            "limitations": "Not population", "evidence_kind": "live", "cache_age_seconds": None,
        }],
        suggestions=[{
            "rank": 1, "label": "Main road cluster", "latitude": 12.98, "longitude": 80.21,
            "rationale": "Validate on site", "evidence": {"source": "OpenStreetMap"},
        }],
    )
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(reports_route, "get_report", lambda _db, _id: saved)
    try:
        response = TestClient(app).get(f"/api/v1/area-reports/{report_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["area_name"] == "Velachery"
    assert body["geometry"]["type"] == "MultiPolygon"
    assert body["metrics"][0]["limitations"] == "Not population"
    assert body["suggestions"][0]["rank"] == 1
