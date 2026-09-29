"""Run the live M1 smoke flow against the local Docker Compose stack."""

import time
from typing import Any

import httpx

API = "http://localhost:8000/api/v1"
HEADERS = {"X-Demo-Role": "bd-manager"}


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def request(method: str, path: str, **kwargs: Any) -> Any:
    response = httpx.request(method, f"{API}{path}", headers=HEADERS, timeout=30, **kwargs)
    response.raise_for_status()
    return response.json()


def run_analysis(area: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    accepted = request("POST", "/areas/analyses", json={"area": area})
    seen: list[str] = []
    for _ in range(120):
        job = request("GET", f"/jobs/{accepted['job_id']}")
        if not seen or seen[-1] != job["status"]:
            seen.append(job["status"])
        if job["status"] == "completed":
            return request("GET", f"/area-reports/{job['report_id']}"), seen
        if job["status"] == "failed":
            raise RuntimeError(f"Analysis failed: {job['status_detail']} ({job['error_code']})")
        time.sleep(1)
    raise TimeoutError("Analysis did not complete within 120 seconds")


def main() -> None:
    health = request("GET", "/health")
    stores = request("GET", "/areas/stores")
    search = request("GET", "/areas/search?q=Velachery&method=locality")[0]
    anna_nagar = request("GET", "/areas/search?q=Anna%20Nagar&method=locality")[0]
    pincode = request("GET", "/areas/search?q=600042&method=pincode")[0]
    check(search["boundary_type"] == "osm-derived", "Velachery did not resolve to an OSM boundary")
    check(anna_nagar["geometry"]["type"] == "MultiPolygon", "Anna Nagar did not resolve to a polygon")
    check(pincode["boundary_type"] in {"official", "third-party"}, "Pincode boundary source is unsupported")
    velachery, velachery_states = run_analysis({
        "name": "Velachery", "query": "Velachery", "selection_method": "locality",
        "geometry": search["geometry"], "source": search["source"], "source_id": search["source_id"],
        "source_url": search["source_url"], "source_license": search["source_license"],
        "boundary_type": search["boundary_type"], "lookup_at": search["lookup_at"],
        "is_official": search["is_official"], "is_approximate": search["is_approximate"],
        "resolver_cache_age_seconds": search["cache_age_seconds"],
    })
    cell, cell_states = run_analysis({
        "name": "Velachery verification cell", "selection_method": "cells",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[80.20, 12.97], [80.21, 12.97], [80.21, 12.98], [80.20, 12.98], [80.20, 12.97]]],
        },
        "source": "User-selected map cells", "source_id": "user-cells:pending-server-hash",
        "boundary_type": "user-selected", "lookup_at": "2026-09-28T12:00:00Z",
        "is_official": False, "is_approximate": False,
    })
    comparison = request(
        "GET", f"/area-reports/compare?left_id={velachery['id']}&right_id={cell['id']}"
    )
    reports = request("GET", "/area-reports")
    required_metric_fields = {
        "raw_value", "normalized_value", "weight", "contribution", "source_name",
        "fetched_at", "geography", "limitations",
    }
    check(all(required_metric_fields <= metric.keys() for metric in velachery["metrics"]), "Metric provenance is incomplete")
    people = [metric for metric in velachery["metrics"] if metric["category"] == "people"]
    store_metrics = [metric for metric in velachery["metrics"] if metric["category"] == "savomart"]
    check(people and all(metric["weight"] == 0 for metric in people), "People evidence must remain zero-weight")
    check(all(metric["evidence_kind"] == "proxy" and metric["raw_value"] is not None for metric in people), "Seeded people proxy is missing or mislabelled")
    check(store_metrics and all(metric["evidence_kind"] != "demo" for metric in store_metrics), "Operational store snapshot was replaced by demo evidence")
    check(len(stores) == 11 and all(store["source_status"] == "provided-snapshot" for store in stores), "Chennai store snapshot is incomplete")
    check(bool(velachery["suggestions"]), "Velachery has no scouting suggestions")
    check(velachery["geometry"] == search["geometry"], "Saved geometry differs from resolved geometry")
    check(velachery["source_id"] == search["source_id"], "Saved source ID differs from resolved source ID")
    check(cell["source_id"].startswith("user-cells:sha256:"), "Map-cell source ID is not stable")
    check(len(reports) >= 2, "Saved report retrieval did not return both analyses")
    print({
        "health": health["status"],
        "resolved_examples": {
            "velachery": search["source_id"], "anna_nagar": anna_nagar["source_id"],
            "600042": pincode["source_id"],
        },
        "velachery": {"score": velachery["score"], "states": velachery_states, "report_id": velachery["id"]},
        "cell": {"score": cell["score"], "states": cell_states, "report_id": cell["id"]},
        "comparison_delta": comparison["score_delta"],
        "chennai_store_pins": len(stores),
        "saved_report_count": len(reports),
    })


if __name__ == "__main__":
    main()
