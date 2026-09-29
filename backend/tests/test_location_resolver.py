import json
from datetime import UTC, datetime

import httpx
from redis.exceptions import RedisError

from app.core.config import Settings
from app.m1_areas import adapters
from app.m1_areas.geometry import normalize_area_geometry

POLYGON = {
    "type": "Polygon",
    "coordinates": [[[80.20, 12.97], [80.22, 12.97], [80.22, 12.99], [80.20, 12.99], [80.20, 12.97]]],
}


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class StaleRedis:
    def __init__(self, payload: str):
        self.payload = payload

    def get(self, key: str):
        return self.payload if key.endswith(":stale") else None


def test_locality_polygon_gets_stable_osm_provenance(monkeypatch) -> None:
    monkeypatch.setattr(adapters, "_cache_client", lambda _settings: (_ for _ in ()).throw(RedisError()))
    monkeypatch.setattr(adapters.httpx, "get", lambda *args, **kwargs: Response([{
        "display_name": "Velachery, Chennai", "osm_type": "relation", "osm_id": 987,
        "category": "place", "geojson": POLYGON,
    }]))

    result = adapters.search_chennai_areas("Velachery", "locality", Settings())[0]

    assert result.boundary_type == "osm-derived"
    assert result.source_id == "osm:relation:987:place"
    assert result.geometry["type"] == "MultiPolygon"


def test_point_result_is_not_presented_as_boundary(monkeypatch) -> None:
    monkeypatch.setattr(adapters, "_cache_client", lambda _settings: (_ for _ in ()).throw(RedisError()))
    monkeypatch.setattr(adapters.httpx, "get", lambda *args, **kwargs: Response([{
        "display_name": "Other Chennai locality", "osm_type": "node", "osm_id": 12,
        "category": "place", "geojson": {"type": "Point", "coordinates": [80.21, 12.98]},
    }]))

    result = adapters.search_chennai_areas("Other", "locality", Settings())[0]

    assert result.boundary_type == "point-only"
    assert result.geometry["type"] == "Point"
    assert "not a boundary" in result.limitations


def test_official_pincode_file_and_missing_boundary(tmp_path) -> None:
    path = tmp_path / "pincodes.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": [{
        "type": "Feature", "properties": {"pincode": "600042"}, "geometry": POLYGON,
    }]}))
    settings = Settings(ogd_pincode_boundaries_path=str(path))

    result = adapters.search_chennai_areas("600042", "pincode", settings)[0]

    assert result.boundary_type == "official"
    assert result.is_official is True
    assert result.source_id.endswith(":600042")
    assert adapters._search_ogd_pincodes("600001", settings) == []


def test_upstream_failure_uses_stale_cached_geography(monkeypatch) -> None:
    lookup = datetime.now(UTC).isoformat()
    payload = json.dumps([{
        "display_name": "Anna Nagar, Chennai", "selection_method": "locality", "query": "Anna Nagar",
        "geometry": POLYGON, "source": "OpenStreetMap via Nominatim",
        "source_id": "osm:relation:55:place", "source_url": "https://www.openstreetmap.org/relation/55",
        "source_license": "ODbL", "boundary_type": "osm-derived", "lookup_at": lookup,
        "is_official": False, "is_approximate": False, "limitations": "OSM boundary",
    }])
    monkeypatch.setattr(adapters, "_cache_client", lambda _settings: StaleRedis(payload))
    monkeypatch.setattr(adapters.httpx, "get", lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("down")))

    result = adapters.search_chennai_areas("Anna Nagar", "locality", Settings())[0]

    assert result.source_id == "osm:relation:55:place"
    assert result.cache_age_seconds is not None


def test_grid_signal_query_uses_encoded_overpass_query(monkeypatch) -> None:
    captured = {}

    def get(url, **kwargs):
        captured.update(url=url, **kwargs)
        return Response({"elements": []})

    monkeypatch.setattr(adapters, "_cache_client", lambda _settings: (_ for _ in ()).throw(RedisError()))
    monkeypatch.setattr(adapters.httpx, "get", get)

    snapshot = adapters.fetch_osm_signals(normalize_area_geometry(POLYGON), "Selected Chennai cells (1)", Settings())

    assert captured["params"]["data"].startswith("[out:json]")
    assert captured["headers"]["User-Agent"].startswith("Savo-SiteScout/")
    assert snapshot.evidence_kind == "live"


def test_grid_signal_query_uses_labelled_demo_fallback_after_upstream_failure(monkeypatch) -> None:
    monkeypatch.setattr(adapters, "_cache_client", lambda _settings: (_ for _ in ()).throw(RedisError()))
    monkeypatch.setattr(
        adapters.httpx, "get", lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("down")),
    )

    snapshot = adapters.fetch_osm_signals(
        normalize_area_geometry(POLYGON), "Selected Chennai cells (1)", Settings(),
    )

    assert snapshot.evidence_kind == "demo"
    assert snapshot.source == "Simulated M1 fallback baseline"
    assert "not observations" in snapshot.limitations


def test_operational_store_parser_supports_nested_coordinates() -> None:
    stores = adapters._parse_operational_stores({"data": [
        {"store_code": "CHN-1", "name": "Valid", "zone": "CHN", "is_operational": True,
         "geocoordinates": {"latitude": 12.97, "longitude": 80.25}},
        {"store_code": "CHN-2", "name": "Closed", "is_operational": False,
         "geocoordinates": {"latitude": 13.01, "longitude": 80.20}},
        {"store_code": "BAD", "name": "Invalid", "is_operational": True,
         "geocoordinates": {"latitude": 200, "longitude": 80.20}},
    ]})

    assert stores == [{
        "code": "CHN-1", "name": "Valid", "lat": 12.97, "lon": 80.25,
        "zone": "CHN", "address": None,
    }]
