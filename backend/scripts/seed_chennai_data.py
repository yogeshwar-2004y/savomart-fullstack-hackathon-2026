#!/usr/bin/env python3
"""Seed verified Chennai source snapshots into PostgreSQL/PostGIS."""

import argparse
import csv
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from geoalchemy2.shape import from_shape
from shapely.geometry import shape

from app.db.models import OperationalStore, WardCensus
from app.db.session import SessionLocal
from app.m1_areas.geometry import normalize_area_geometry

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
STORE_SOURCE_URL = "https://internal-service.savomart.in/bridge/api/store/list?is_operational=True"
WARD_SOURCE_URL = (
    "https://gisgcc.chennaicorporation.gov.in/server/rest/services/GCCPublic/"
    "GCC_AdminBoundary/MapServer/4"
)
CENSUS_SOURCE_URL = (
    "https://www.chennaicorporation.gov.in/delimitation_draft/pdf/"
    "DELIMITATION_OF_WARDS_DRAFT_PROPOSAL_ENGLISH.pdf"
)


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "stores", "results", "items"):
            if isinstance(payload.get(key), list):
                return payload[key]
    raise ValueError("Store snapshot does not contain a recognized record list")


def _store_point(row: dict[str, Any]) -> tuple[float, float]:
    coordinates = row.get("geocoordinates") or row.get("coordinates") or {}
    latitude = coordinates.get("latitude", coordinates.get("lat", row.get("latitude", row.get("lat"))))
    longitude = coordinates.get(
        "longitude", coordinates.get("lng", coordinates.get("lon", row.get("longitude", row.get("lng", row.get("lon")))))
    )
    latitude, longitude = float(latitude), float(longitude)
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError(f"Invalid store coordinate for {row.get('store_code', 'unknown')}")
    return latitude, longitude


def seed(
    stores_path: Path, census_path: Path, wards_path: Path,
    store_payload: Any | None = None, store_status: str = "provided-snapshot",
) -> tuple[int, int]:
    store_snapshot_at = datetime.fromtimestamp(stores_path.stat().st_mtime, UTC)
    ward_snapshot_at = datetime.fromtimestamp(wards_path.stat().st_mtime, UTC)
    stores = [
        row for row in _rows(
            store_payload if store_payload is not None else json.loads(stores_path.read_text(encoding="utf-8"))
        ) if row.get("is_operational", row.get("isOperational", True)) is not False
    ]
    if store_payload is not None:
        store_snapshot_at = datetime.now(UTC)
    census = {}
    with census_path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            census[str(row["ward_id"]).zfill(3)] = row
    wards = json.loads(wards_path.read_text(encoding="utf-8"))
    features = wards.get("features", []) if wards.get("type") == "FeatureCollection" else []
    if not stores or (store_payload is None and len(stores) != 74) or len(census) != 200 or len(features) != 200:
        raise ValueError("Expected operational stores plus 200 census rows and 200 GCC ward polygons")

    db = SessionLocal()
    try:
        for row in stores:
            latitude, longitude = _store_point(row)
            code = str(row.get("store_code") or "").strip()
            if not code:
                raise ValueError("Store record is missing store_code")
            db.merge(OperationalStore(
                store_code=code, name=str(row.get("name") or code), address=row.get("address"),
                zone=row.get("zone"), is_operational=bool(row.get("is_operational", True)),
                location=from_shape(shape({"type": "Point", "coordinates": [longitude, latitude]}), srid=4326),
                source_name=("Savomart operational store service" if store_status == "live" else "Savomart operational store snapshot"),
                source_url=STORE_SOURCE_URL,
                source_status=store_status, retrieved_at=store_snapshot_at,
            ))
        seen = set()
        for feature in features:
            ward_id = str((feature.get("properties") or {}).get("ward") or "").zfill(3)
            row = census.get(ward_id)
            if not row or ward_id in seen:
                raise ValueError(f"GCC ward {ward_id or 'unknown'} has no unique census row")
            geometry = normalize_area_geometry(feature["geometry"])
            db.merge(WardCensus(
                ward_id=ward_id, zone=int(row["zone"]),
                residential_buildings=int(row["residential_buildings"]),
                households_2011=int(row["households_2011"]), population_2011=int(row["population_2011"]),
                geometry=from_shape(geometry, srid=4326), boundary_source_url=WARD_SOURCE_URL,
                census_source_url=CENSUS_SOURCE_URL, retrieved_at=ward_snapshot_at,
            ))
            seen.add(ward_id)
        db.commit()
        return len(stores), len(seen)
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stores", type=Path, default=DATA_DIR / "savomart_operational_stores.json")
    parser.add_argument("--census", type=Path, default=DATA_DIR / "gcc_ward_population_census_2011.csv")
    parser.add_argument("--wards", type=Path, default=DATA_DIR / "gcc_ward_boundaries.geojson")
    args = parser.parse_args()
    live_payload = None
    store_status = "provided-snapshot"
    service_url, token = os.getenv("STORE_SERVICE_URL"), os.getenv("STORE_SERVICE_TOKEN")
    if service_url and token:
        try:
            response = httpx.get(
                service_url, headers={"X-cron-token": token}, timeout=15, follow_redirects=True,
            )
            response.raise_for_status()
            live_payload = response.json()
            store_status = "live"
        except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
            print(f"Store refresh unavailable ({type(exc).__name__}); using provided snapshot")
    stores, wards = seed(args.stores, args.census, args.wards, live_payload, store_status)
    print(f"Seeded {stores} operational stores ({store_status}) and {wards} GCC ward census geometries")


if __name__ == "__main__":
    main()
