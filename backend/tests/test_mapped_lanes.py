from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import box, shape

import app.m3_surveys.service as survey_service
from app.m3_surveys.roads import parse_road_suggestions
from app.m3_surveys.schemas import ZonePlan


def test_road_suggestions_clip_and_group_fragmented_ways() -> None:
    remaining = box(80.20, 12.98, 80.22, 13.00)
    payload = {"elements": [
        {"type": "way", "id": 101, "tags": {"highway": "residential", "name": "Main Road"}, "geometry": [{"lat": 12.99, "lon": 80.19}, {"lat": 12.99, "lon": 80.21}]},
        {"type": "way", "id": 102, "tags": {"highway": "residential", "name": "Main Road"}, "geometry": [{"lat": 12.99, "lon": 80.21}, {"lat": 12.99, "lon": 80.23}]},
        {"type": "way", "id": 103, "tags": {"highway": "residential", "name": "Outside"}, "geometry": [{"lat": 13.01, "lon": 80.20}, {"lat": 13.01, "lon": 80.22}]},
    ]}
    suggestions = parse_road_suggestions(payload, remaining, datetime.now(UTC))
    assert len(suggestions) == 1
    assert suggestions[0]["osm_way_ids"] == [101, 102]
    assert suggestions[0]["label"] == "Main Road"
    assert shape(suggestions[0]["geometry"]).within(remaining)


def test_missing_road_source_preserves_manual_zone_planning(monkeypatch) -> None:
    study = SimpleNamespace(
        id=uuid4(), status="requested", zones=[], lane_suggestions=None,
        lane_suggestions_fetched_at=None, lane_suggestions_error=None,
        survey_geometry="unused",
    )
    db = SimpleNamespace(commit=lambda: None)
    monkeypatch.setattr(survey_service, "to_shape", lambda _geometry: box(80.20, 12.98, 80.22, 13.00))
    monkeypatch.setattr(survey_service, "fetch_road_suggestions", lambda *_args: (_ for _ in ()).throw(httpx.ReadTimeout("unavailable")))
    monkeypatch.setattr(survey_service, "get_study", lambda *_args: study)
    result = survey_service.refresh_lane_suggestions(db, study)
    assert result.lane_suggestions == []
    assert "Plan zones manually" in result.lane_suggestions_error

    fetched_at = datetime.now(UTC)
    monkeypatch.setattr(survey_service, "fetch_road_suggestions", lambda *_args: ([{"id": "osm-road:test"}], fetched_at))
    retried = survey_service.refresh_lane_suggestions(db, study, force=True)
    assert retried.lane_suggestions == [{"id": "osm-road:test"}]
    assert retried.lane_suggestions_error is None
    assert retried.lane_suggestions_fetched_at == fetched_at


def test_reviewed_lane_is_assigned_to_only_one_zone(monkeypatch) -> None:
    geometry = box(80.20, 12.98, 80.22, 13.00)
    study = SimpleNamespace(
        id=uuid4(), status="requested", zones=[], survey_geometry=from_shape(geometry, srid=4326),
        lane_suggestions=[{
            "id": "osm-road:crossing", "geometry": {
                "type": "LineString", "coordinates": [[80.202, 12.99], [80.218, 12.99]],
            },
        }],
    )
    zones = []
    db = SimpleNamespace(add_all=lambda items: zones.extend(items), commit=lambda: None)
    monkeypatch.setattr(survey_service, "get_study", lambda *_args: study)
    survey_service.plan_zones(db, study, ZonePlan(
        zone_count=2, assignee_ids=["survey-executive-1", "survey-executive-2"],
        included_lane_ids=["osm-road:crossing"],
    ))
    assert len(zones) == 2
    assert sum("osm-road:crossing" in zone.suggested_lane_ids for zone in zones) == 1
