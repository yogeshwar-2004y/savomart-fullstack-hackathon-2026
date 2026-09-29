import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any

import httpx
from redis import Redis
from redis.exceptions import RedisError
from shapely.geometry import MultiPolygon, Point, mapping

from app.core.config import Settings, get_settings
from app.m1_areas.geometry import (
    area_sq_km,
    normalize_area_geometry,
    normalize_chennai_point,
)
from app.m1_areas.schemas import AreaSearchResult

logger = logging.getLogger(__name__)


@dataclass
class SignalSnapshot:
    counts: dict[str, float]
    hotspots: list[dict[str, Any]]
    fetched_at: datetime
    source: str
    source_url: str | None
    evidence_kind: str
    limitations: str
    cache_age_seconds: int | None = None
    cache_key: str | None = None


@dataclass
class StoreSnapshot:
    nearest_store_km: float | None
    nearby_store_count: int
    fetched_at: datetime
    source: str
    evidence_kind: str
    limitations: str
    cache_age_seconds: int | None = None


VELACHERY_DEMO_SIGNALS = {
    "counts": {"residential": 132, "businesses": 89, "amenities": 44, "access": 38, "competition": 12},
    "hotspots": [
        {"name": "100 Feet Road cluster", "lat": 12.9794, "lon": 80.2182, "signals": 12},
        {"name": "Velachery Main Road cluster", "lat": 12.9872, "lon": 80.2104, "signals": 10},
        {"name": "Taramani Link Road cluster", "lat": 12.9722, "lon": 80.2214, "signals": 8},
    ],
}

DEMO_STORES = [
    {"name": "Demo Madipakkam store", "lat": 12.9647, "lon": 80.1986},
    {"name": "Demo Adambakkam store", "lat": 12.9918, "lon": 80.2041},
    {"name": "Demo Thoraipakkam store", "lat": 12.9416, "lon": 80.2362},
]

STORE_CACHE_KEY = "sitescout:stores:operational"


def _cache_client(settings: Settings) -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)


def _cache_key(prefix: str, geometry: MultiPolygon) -> str:
    digest = hashlib.sha256(geometry.wkb).hexdigest()[:24]
    return f"sitescout:{prefix}:{digest}"


def _cache_read(redis: Redis, key: str) -> SignalSnapshot | None:
    raw = redis.get(key)
    if not raw:
        return None
    payload = json.loads(raw)
    fetched_at = datetime.fromisoformat(payload["fetched_at"])
    age = max(0, int((datetime.now(UTC) - fetched_at).total_seconds()))
    return SignalSnapshot(
        counts=payload["counts"], hotspots=payload["hotspots"], fetched_at=fetched_at,
        source=payload["source"], source_url=payload.get("source_url"), evidence_kind="cached",
        limitations=payload["limitations"], cache_age_seconds=age, cache_key=key,
    )


def _cache_write(redis: Redis, key: str, snapshot: SignalSnapshot, settings: Settings) -> None:
    payload = json.dumps({
        "counts": snapshot.counts, "hotspots": snapshot.hotspots,
        "fetched_at": snapshot.fetched_at.isoformat(), "source": snapshot.source,
        "source_url": snapshot.source_url, "limitations": snapshot.limitations,
    })
    redis.setex(key, settings.external_cache_ttl_seconds, payload)
    redis.setex(f"{key}:stale", settings.stale_cache_ttl_seconds, payload)


def search_chennai_areas(query: str, method: str, settings: Settings | None = None) -> list[AreaSearchResult]:
    settings = settings or get_settings()
    normalized = query.strip()
    if method == "pincode":
        if not normalized.isdigit() or len(normalized) != 6:
            return []
        official = _search_ogd_pincodes(normalized, settings)
        if official:
            return official
    cache_key = f"sitescout:location:{method}:{normalized.casefold()}"
    redis: Redis | None = None
    try:
        redis = _cache_client(settings)
        cached = _read_location_cache(redis, cache_key)
        if cached:
            return cached
    except (RedisError, ValueError, KeyError, TypeError) as exc:
        logger.info("Location cache unavailable: %s", exc.__class__.__name__)
        redis = None
    if method == "pincode":
        sourced = _search_public_pincode_layer(normalized, settings)
        if sourced:
            if redis:
                try:
                    _write_location_cache(redis, cache_key, sourced, settings)
                except RedisError as exc:
                    logger.info("Location cache write failed: %s", exc.__class__.__name__)
            return sourced
    params: dict[str, Any] = {
        "q": f"{normalized}, Chennai, Tamil Nadu, India",
        "format": "jsonv2", "polygon_geojson": 1, "addressdetails": 1, "limit": 5,
        "countrycodes": "in", "viewbox": "80.05,13.30,80.35,12.75", "bounded": 1,
    }
    if method == "pincode":
        params["postalcode"] = normalized
    results: list[AreaSearchResult] = []
    try:
        response = httpx.get(
            f"{settings.nominatim_url.rstrip('/')}/search", params=params,
            headers={"User-Agent": "Savo-SiteScout/0.1 (hackathon demo)"}, timeout=12,
        )
        response.raise_for_status()
        lookup_at = datetime.now(UTC)
        for item in response.json():
            raw_geometry = item.get("geojson")
            if not raw_geometry:
                continue
            geometry: dict[str, Any]
            boundary_type: str
            try:
                if raw_geometry.get("type") in {"Polygon", "MultiPolygon"}:
                    geometry = mapping(normalize_area_geometry(raw_geometry))
                    boundary_type = "osm-derived"
                elif raw_geometry.get("type") == "Point":
                    geometry = mapping(normalize_chennai_point(raw_geometry))
                    boundary_type = "point-only"
                else:
                    continue
            except ValueError:
                continue
            osm_type = item.get("osm_type", "unknown")
            osm_id = item.get("osm_id", "unknown")
            category = item.get("category", item.get("class", "place"))
            results.append(AreaSearchResult(
                display_name=item["display_name"], selection_method=method, query=normalized,
                geometry=geometry, source="OpenStreetMap via Nominatim",
                source_id=f"osm:{osm_type}:{osm_id}:{category}",
                source_url=f"https://www.openstreetmap.org/{osm_type}/{osm_id}" if osm_type in {"node", "way", "relation"} else "https://www.openstreetmap.org",
                source_license="Open Data Commons Open Database License (ODbL)",
                boundary_type=boundary_type, lookup_at=lookup_at,
                limitations=(
                    "OSM contributor boundary; completeness and administrative meaning vary."
                    if boundary_type == "osm-derived" else
                    "Geocoder returned a point, not a boundary. Choose an approximate radius or select map cells before analysis."
                ),
            ))
        if results and redis:
            _write_location_cache(redis, cache_key, results, settings)
    except (httpx.HTTPError, ValueError, json.JSONDecodeError):
        if redis:
            try:
                stale = _read_location_cache(redis, f"{cache_key}:stale")
                if stale:
                    return stale
            except (RedisError, ValueError, KeyError, TypeError) as exc:
                logger.info("Stale location cache unavailable: %s", exc.__class__.__name__)
    return results


def _read_location_cache(redis: Redis, key: str) -> list[AreaSearchResult]:
    raw = redis.get(key)
    if not raw:
        return []
    payload = json.loads(raw)
    fetched_at = datetime.fromisoformat(payload[0]["lookup_at"])
    age = max(0, int((datetime.now(UTC) - fetched_at).total_seconds()))
    return [AreaSearchResult.model_validate({**item, "cache_age_seconds": age}) for item in payload]


def _write_location_cache(redis: Redis, key: str, results: list[AreaSearchResult], settings: Settings) -> None:
    payload = json.dumps([result.model_dump(mode="json") for result in results])
    redis.setex(key, settings.location_cache_ttl_seconds, payload)
    redis.setex(f"{key}:stale", settings.stale_cache_ttl_seconds, payload)


def _search_ogd_pincodes(pincode: str, settings: Settings) -> list[AreaSearchResult]:
    if not settings.ogd_pincode_boundaries_path:
        return []
    path = Path(settings.ogd_pincode_boundaries_path)
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return []
    try:
        document = json.loads(text)
        features = document.get("features", []) if document.get("type") == "FeatureCollection" else [document]
    except json.JSONDecodeError:
        features = []
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                features.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    matches: list[AreaSearchResult] = []
    for feature in features:
        properties = feature.get("properties", {})
        value = next((properties.get(key) for key in ("pincode", "pin_code", "PINCODE", "Pincode", "PIN Code") if properties.get(key) is not None), None)
        if str(value) != pincode:
            continue
        try:
            geometry = normalize_area_geometry(feature["geometry"])
        except (KeyError, ValueError):
            continue
        matches.append(AreaSearchResult(
            display_name=f"PIN {pincode}, Chennai, Tamil Nadu", selection_method="pincode", query=pincode,
            geometry=mapping(geometry), source="OGD India / Department of Posts",
            source_id=f"ogd-india:department-of-posts:pincode:{pincode}",
            source_url="https://www.data.gov.in/catalog/all-india-pincode-boundary-geo-json",
            source_license="Government Open Data License - India",
            boundary_type="official", lookup_at=datetime.now(UTC), is_official=True,
            limitations=(
                "Postal delivery boundary from the configured OGD India dataset; refresh cadence follows the local "
                f"dataset file (modified {datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()})."
            ),
        ))
    return matches


def _search_public_pincode_layer(pincode: str, settings: Settings) -> list[AreaSearchResult]:
    if not settings.chennai_pincode_feature_url:
        return []
    try:
        response = httpx.get(
            f"{settings.chennai_pincode_feature_url.rstrip('/')}/query",
            params={
                "where": f"pincode = '{pincode}'", "outFields": "OBJECTID,pincode,office_name",
                "returnGeometry": "true", "f": "geojson", "outSR": "4326",
            }, timeout=15,
        )
        response.raise_for_status()
        features = response.json().get("features", [])
    except (httpx.HTTPError, ValueError, json.JSONDecodeError):
        return []
    results: list[AreaSearchResult] = []
    for feature in features:
        try:
            geometry = normalize_area_geometry(feature["geometry"])
        except (KeyError, ValueError):
            continue
        properties = feature.get("properties", {})
        object_id = properties.get("OBJECTID", feature.get("id", "unknown"))
        results.append(AreaSearchResult(
            display_name=f"PIN {pincode}, Chennai, Tamil Nadu", selection_method="pincode", query=pincode,
            geometry=mapping(geometry), source="Public Chennai pincode feature layer",
            source_id=f"arcgis:9f024e2233044c6d949068b3513bffa7:layer:11:object:{object_id}",
            source_url=settings.chennai_pincode_feature_url, source_license=None,
            boundary_type="third-party", lookup_at=datetime.now(UTC), is_official=False,
            limitations=(
                "Public polygon with useful Chennai coverage, but publisher metadata does not establish it as an "
                "official Department of Posts boundary. Configure the OGD file to prefer a verified official polygon."
            ),
        ))
    return results


def fetch_osm_signals(geometry: MultiPolygon, area_name: str, settings: Settings | None = None) -> SignalSnapshot:
    settings = settings or get_settings()
    key = _cache_key("osm-signals", geometry)
    redis: Redis | None = None
    try:
        redis = _cache_client(settings)
        cached = _cache_read(redis, key)
        if cached:
            return cached
    except (RedisError, ValueError, KeyError, TypeError) as exc:
        logger.info("Signal cache unavailable: %s", exc.__class__.__name__)
        redis = None

    min_lon, min_lat, max_lon, max_lat = geometry.bounds
    bbox = f"{min_lat},{min_lon},{max_lat},{max_lon}"
    query = f"""[out:json][timeout:25];(
      nwr[building~\"^(apartments|residential|house|yes)$\"]({bbox});
      nwr[shop]({bbox}); nwr[office]({bbox}); nwr[amenity]({bbox});
      nwr[public_transport]({bbox}); nwr[railway=station]({bbox}); nwr[highway=bus_stop]({bbox});
      nwr[highway~\"^(primary|secondary|tertiary)$\"]({bbox});
    );out center tags;"""
    try:
        response = httpx.get(
            settings.overpass_url,
            params={"data": query},
            headers={"User-Agent": "Savo-SiteScout/0.1 (Chennai area intelligence)"},
            timeout=35,
        )
        response.raise_for_status()
        snapshot = _parse_overpass(response.json(), geometry)
        snapshot.cache_key = key
        if redis:
            try:
                _cache_write(redis, key, snapshot, settings)
            except RedisError as exc:
                logger.info("Signal cache write failed: %s", exc.__class__.__name__)
        return snapshot
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        if redis:
            try:
                stale = _cache_read(redis, f"{key}:stale")
                if stale:
                    stale.limitations += " Upstream failed; an eligible Redis snapshot was used."
                    return stale
            except (RedisError, ValueError, KeyError, TypeError) as exc:
                logger.info("Stale signal cache unavailable: %s", exc.__class__.__name__)
        if "velachery" in area_name.lower():
            return SignalSnapshot(
                **VELACHERY_DEMO_SIGNALS, fetched_at=datetime.now(UTC),
                source="Bundled Velachery OpenStreetMap demo snapshot", source_url="https://www.openstreetmap.org",
                evidence_kind="demo", limitations=(
                    "Demo snapshot used because live Overpass data was unavailable. Counts are mapped features, "
                    "not people, households, footfall, or complete business inventories."
                ), cache_key=key,
            )
        if settings.allow_simulated_signal_fallback:
            size = area_sq_km(geometry)
            centroid = geometry.centroid
            return SignalSnapshot(
                counts={
                    "residential": round(24 * size, 2), "businesses": round(16 * size, 2),
                    "amenities": round(8 * size, 2), "access": round(7 * size, 2),
                    "competition": round(2 * size, 2),
                },
                hotspots=[{
                    "name": "Area centre demo validation point", "lat": centroid.y,
                    "lon": centroid.x, "signals": 0,
                }],
                fetched_at=datetime.now(UTC), source="Simulated M1 fallback baseline", source_url=None,
                evidence_kind="demo", limitations=(
                    "Live Overpass data and an eligible cache snapshot were unavailable. Values are a fixed "
                    "simulation for workflow testing, not observations about this area and not suitable for a "
                    "site decision. Retry later for sourced OpenStreetMap evidence."
                ), cache_key=key,
            )
        raise RuntimeError(f"OpenStreetMap enrichment failed: {exc.__class__.__name__}") from exc


def _parse_overpass(payload: dict[str, Any], geometry: MultiPolygon) -> SignalSnapshot:
    counts = {"residential": 0.0, "businesses": 0.0, "amenities": 0.0, "access": 0.0, "competition": 0.0}
    candidates: list[dict[str, Any]] = []
    for element in payload.get("elements", []):
        lat = element.get("lat", element.get("center", {}).get("lat"))
        lon = element.get("lon", element.get("center", {}).get("lon"))
        if lat is None or lon is None or not geometry.covers(Point(lon, lat)):
            continue
        tags = element.get("tags", {})
        score = 0
        if tags.get("building") in {"apartments", "residential", "house", "yes"}:
            counts["residential"] += 1
            score += 1
        if "shop" in tags or "office" in tags:
            counts["businesses"] += 1
            score += 2
        if tags.get("amenity") in {"school", "college", "hospital", "clinic", "pharmacy", "marketplace", "bank", "atm"}:
            counts["amenities"] += 1
            score += 2
        if "public_transport" in tags or tags.get("railway") == "station" or tags.get("highway") in {"bus_stop", "primary", "secondary", "tertiary"}:
            counts["access"] += 1
            score += 2
        if tags.get("shop") in {"supermarket", "convenience", "department_store"}:
            counts["competition"] += 1
        if score >= 2:
            candidates.append({
                "name": tags.get("name") or "Mapped activity cluster", "lat": lat, "lon": lon, "signals": score,
            })
    candidates.sort(key=lambda item: item["signals"], reverse=True)
    return SignalSnapshot(
        counts=counts, hotspots=candidates[:12], fetched_at=datetime.now(UTC),
        source="OpenStreetMap via Overpass API", source_url="https://www.openstreetmap.org",
        evidence_kind="live", limitations=(
            "OpenStreetMap coverage varies. Feature counts indicate mapped urban activity only and must not be "
            "interpreted as population, households, footfall, or a complete business census."
        ),
    )


def _store_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "stores", "results", "items"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def _parse_operational_stores(payload: Any) -> list[dict[str, Any]]:
    stores = []
    for row in _store_rows(payload):
        if row.get("is_operational", row.get("isOperational", True)) is False:
            continue
        coordinates = row.get("geocoordinates") or row.get("coordinates") or {}
        lat = coordinates.get("latitude", coordinates.get("lat", row.get("latitude", row.get("lat"))))
        lon = coordinates.get(
            "longitude", coordinates.get("lng", coordinates.get("lon", row.get("longitude", row.get("lng", row.get("lon")))))
        )
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue
        stores.append({
            "code": str(row.get("store_code", row.get("storeCode", row.get("id", "")))),
            "name": row.get("name", "Savomart store"), "lat": lat, "lon": lon,
            "zone": row.get("zone"), "address": row.get("address"),
        })
    return stores


def _snapshot_stores(settings: Settings) -> tuple[list[dict[str, Any]], datetime | None]:
    if not settings.store_snapshot_path:
        return [], None
    path = Path(settings.store_snapshot_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    try:
        stores = _parse_operational_stores(json.loads(path.read_text(encoding="utf-8")))
        return stores, datetime.fromtimestamp(path.stat().st_mtime, UTC)
    except (OSError, json.JSONDecodeError):
        return [], None


def _live_stores(settings: Settings) -> tuple[list[dict[str, Any]], str, int | None]:
    if not settings.store_service_url or not settings.store_service_token:
        return [], "missing", None
    redis: Redis | None = None
    try:
        redis = _cache_client(settings)
        cached = redis.get(STORE_CACHE_KEY)
        if cached:
            payload = json.loads(cached)
            age = max(0, int((datetime.now(UTC) - datetime.fromisoformat(payload["fetched_at"])).total_seconds()))
            return payload["stores"], "cached", age
    except (RedisError, json.JSONDecodeError, KeyError, ValueError):
        redis = None
    try:
        response = httpx.get(
            settings.store_service_url,
            headers={"X-cron-token": settings.store_service_token}, timeout=12,
            follow_redirects=True,
        )
        response.raise_for_status()
        stores = _parse_operational_stores(response.json())
        if stores and redis:
            payload = json.dumps({"stores": stores, "fetched_at": datetime.now(UTC).isoformat()})
            redis.setex(STORE_CACHE_KEY, settings.external_cache_ttl_seconds, payload)
            redis.setex(f"{STORE_CACHE_KEY}:stale", settings.stale_cache_ttl_seconds, payload)
        return stores, "live", None
    except (httpx.HTTPError, ValueError, json.JSONDecodeError):
        if redis:
            try:
                cached = redis.get(f"{STORE_CACHE_KEY}:stale")
                if cached:
                    payload = json.loads(cached)
                    age = max(0, int((datetime.now(UTC) - datetime.fromisoformat(payload["fetched_at"])).total_seconds()))
                    return payload["stores"], "cached", age
            except (RedisError, json.JSONDecodeError, KeyError, ValueError):
                pass
        return [], "unavailable", None


def fetch_store_signals(geometry: MultiPolygon, settings: Settings | None = None) -> StoreSnapshot:
    settings = settings or get_settings()
    fetched_at = datetime.now(UTC)
    stores, kind, cache_age = _live_stores(settings)
    source = "Savomart operational store service"
    limitations = "Operational status is provider-supplied; distance is straight-line, not travel time."
    if not stores:
        stores, snapshot_at = _snapshot_stores(settings)
        source = "Provided Savomart operational store snapshot"
        kind = "snapshot"
        limitations = "Provided operational snapshot; status may have changed since retrieval. Distance is straight-line."
        if snapshot_at:
            fetched_at = snapshot_at
    if not stores:
        stores = DEMO_STORES
        source = "Bundled Savomart demo store locations"
        kind = "demo"
        limitations = "Demo locations are illustrative and are not claims about current operational stores."
    centroid = geometry.centroid
    distances = [_haversine_km(centroid.y, centroid.x, store["lat"], store["lon"]) for store in stores]
    nearby = sum(distance <= 5 for distance in distances)
    return StoreSnapshot(
        nearest_store_km=min(distances) if distances else None, nearby_store_count=nearby,
        fetched_at=fetched_at, source=source, evidence_kind=kind, limitations=limitations,
        cache_age_seconds=cache_age,
    )


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(a))
