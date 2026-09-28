import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from math import asin, cos, radians, sin, sqrt
from typing import Any

import httpx
from redis import Redis
from shapely.geometry import MultiPolygon, Point, mapping, shape

from app.core.config import Settings, get_settings
from app.m1_areas.geometry import VELACHERY_GEOMETRY, normalize_area_geometry
from app.m1_areas.schemas import AreaSearchResult


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
        for item in response.json():
            if not item.get("geojson"):
                continue
            try:
                geometry = normalize_area_geometry(item["geojson"])
            except ValueError:
                continue
            results.append(AreaSearchResult(
                display_name=item["display_name"], selection_method=method, query=normalized,
                geometry=mapping(geometry), source="OpenStreetMap Nominatim",
                limitations="Boundary quality follows OpenStreetMap contributor coverage.",
            ))
    except (httpx.HTTPError, ValueError, json.JSONDecodeError):
        pass
    if not results and ("velachery" in normalized.lower() or normalized == "600042"):
        results.append(AreaSearchResult(
            display_name="Velachery, Chennai, Tamil Nadu", selection_method=method, query=normalized,
            geometry=mapping(normalize_area_geometry(VELACHERY_GEOMETRY)),
            source="Bundled OpenStreetMap-derived demo boundary",
            limitations="Offline fallback boundary is simplified and must not be used as an official administrative boundary.",
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
    except Exception:
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
        response = httpx.post(settings.overpass_url, content=query, timeout=35)
        response.raise_for_status()
        snapshot = _parse_overpass(response.json(), geometry)
        snapshot.cache_key = key
        if redis:
            try:
                _cache_write(redis, key, snapshot, settings)
            except Exception:
                pass
        return snapshot
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        if redis:
            try:
                stale = _cache_read(redis, f"{key}:stale")
                if stale:
                    stale.limitations += " Upstream failed; an eligible Redis snapshot was used."
                    return stale
            except Exception:
                pass
        if "velachery" in area_name.lower():
            return SignalSnapshot(
                **VELACHERY_DEMO_SIGNALS, fetched_at=datetime.now(UTC),
                source="Bundled Velachery OpenStreetMap demo snapshot", source_url="https://www.openstreetmap.org",
                evidence_kind="demo", limitations=(
                    "Demo snapshot used because live Overpass data was unavailable. Counts are mapped features, "
                    "not people, households, footfall, or complete business inventories."
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


def fetch_store_signals(geometry: MultiPolygon, settings: Settings | None = None) -> StoreSnapshot:
    settings = settings or get_settings()
    fetched_at = datetime.now(UTC)
    stores: list[dict[str, Any]] = []
    source = "Bundled Savomart demo store locations"
    kind = "demo"
    limitations = "Demo locations are illustrative and are not claims about current operational stores."
    if settings.store_service_url and settings.store_service_token:
        try:
            response = httpx.get(
                settings.store_service_url,
                headers={"X-cron-token": settings.store_service_token}, timeout=12,
            )
            response.raise_for_status()
            body = response.json()
            rows = body if isinstance(body, list) else body.get("data", body.get("stores", []))
            for row in rows:
                lat = row.get("latitude", row.get("lat"))
                lon = row.get("longitude", row.get("lng", row.get("lon")))
                if lat is not None and lon is not None:
                    stores.append({"name": row.get("name", "Savomart store"), "lat": float(lat), "lon": float(lon)})
            source = "Savomart operational store service"
            kind = "live"
            limitations = "Operational status is provider-supplied; distance is straight-line, not travel time."
        except (httpx.HTTPError, ValueError, json.JSONDecodeError):
            stores = []
    if not stores:
        stores = DEMO_STORES
    centroid = geometry.centroid
    distances = [_haversine_km(centroid.y, centroid.x, store["lat"], store["lon"]) for store in stores]
    nearby = sum(distance <= 5 for distance in distances)
    return StoreSnapshot(
        nearest_store_km=min(distances) if distances else None, nearby_store_count=nearby,
        fetched_at=fetched_at, source=source, evidence_kind=kind, limitations=limitations,
    )


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(a))
