"""Targeted, cached OpenStreetMap road suggestions for a single catchment."""

import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime

import httpx
from pyproj import Transformer
from redis import Redis
from redis.exceptions import RedisError
from shapely.geometry import LineString, MultiLineString, mapping
from shapely.ops import transform, unary_union

from app.core.config import Settings

_TO_METRES = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True)


def _to_metric(geometry):
    return transform(_TO_METRES.transform, geometry)

ROAD_SOURCE = "OpenStreetMap ways via Overpass"
ROAD_LICENSE = "Open Data Commons Open Database License (ODbL)"
SURVEYABLE_HIGHWAYS = "residential|living_street|service|unclassified|tertiary|secondary|primary|pedestrian|footway|path"


def parse_road_suggestions(payload: dict, remaining, fetched_at: datetime) -> list[dict]:
    grouped: dict[str, list[tuple[int, object]]] = defaultdict(list)
    for item in payload.get("elements", []):
        if item.get("type") != "way" or not item.get("geometry") or not item.get("tags", {}).get("highway"):
            continue
        points = [(point.get("lon"), point.get("lat")) for point in item["geometry"]]
        if len(points) < 2 or any(None in point for point in points):
            continue
        raw = LineString(points)
        clipped = raw.intersection(remaining)
        if clipped.is_empty or _to_metric(clipped).length < 25:
            continue
        name = str(item["tags"].get("name") or "").strip()
        key = f"{name.casefold()}:{item['tags']['highway']}" if name else f"way:{item['id']}"
        grouped[key].append((int(item["id"]), clipped))

    suggestions = []
    for key, parts in grouped.items():
        merged = unary_union([part for _, part in parts])
        lines = [merged] if isinstance(merged, LineString) else [part for part in getattr(merged, "geoms", []) if isinstance(part, LineString)]
        if not lines:
            continue
        geometry = MultiLineString(lines)
        way_ids = sorted({way_id for way_id, _ in parts})
        label = key.split(":", 1)[0].title() if not key.startswith("way:") else f"Unnamed mapped way {way_ids[0]}"
        identifier = hashlib.sha256((key + ":" + ",".join(map(str, way_ids))).encode()).hexdigest()[:16]
        suggestions.append({
            "id": f"osm-road:{identifier}", "label": label, "geometry": mapping(geometry),
            "length_m": round(_to_metric(geometry).length), "osm_way_ids": way_ids,
            "source": ROAD_SOURCE, "fetched_at": fetched_at.isoformat(),
        })
    return sorted(suggestions, key=lambda row: (-row["length_m"], row["label"]))[:100]


def fetch_road_suggestions(remaining, settings: Settings) -> tuple[list[dict], datetime]:
    digest = hashlib.sha256(remaining.wkb).hexdigest()[:24]
    cache_key = f"sitescout:roads:{digest}"
    redis = None
    try:
        redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
        raw = redis.get(cache_key)
        if raw:
            snapshot = json.loads(raw)
            return snapshot["suggestions"], datetime.fromisoformat(snapshot["fetched_at"])
    except (RedisError, ValueError, KeyError, TypeError):
        redis = None

    west, south, east, north = remaining.bounds
    query = f'[out:json][timeout:18];way["highway"~"^({SURVEYABLE_HIGHWAYS})$"]({south},{west},{north},{east});out geom;'
    response = httpx.post(settings.overpass_url, data={"data": query}, timeout=24)
    response.raise_for_status()
    fetched_at = datetime.now(UTC)
    suggestions = parse_road_suggestions(response.json(), remaining, fetched_at)
    if redis is not None:
        try:
            redis.setex(cache_key, 86400, json.dumps({"suggestions": suggestions, "fetched_at": fetched_at.isoformat()}))
        except RedisError:
            pass
    return suggestions, fetched_at
