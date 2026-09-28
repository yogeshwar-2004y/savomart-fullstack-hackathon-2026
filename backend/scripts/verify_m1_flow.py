"""Run the live M1 smoke flow against the local Docker Compose stack."""

import time
from typing import Any

import httpx

API = "http://localhost:8000/api/v1"
HEADERS = {"X-Demo-Role": "bd-manager"}


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
    search = request("GET", "/areas/search?q=Velachery&method=locality")[0]
    velachery, velachery_states = run_analysis({
        "name": "Velachery", "query": "Velachery", "selection_method": "locality",
        "geometry": search["geometry"],
    })
    cell, cell_states = run_analysis({
        "name": "Velachery verification cell", "selection_method": "cells",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[80.20, 12.97], [80.21, 12.97], [80.21, 12.98], [80.20, 12.98], [80.20, 12.97]]],
        },
    })
    comparison = request(
        "GET", f"/area-reports/compare?left_id={velachery['id']}&right_id={cell['id']}"
    )
    reports = request("GET", "/area-reports")
    required_metric_fields = {
        "raw_value", "normalized_value", "weight", "contribution", "source_name",
        "fetched_at", "geography", "limitations",
    }
    assert all(required_metric_fields <= metric.keys() for metric in velachery["metrics"])
    assert any(metric["category"] == "people" and metric["raw_value"] is None for metric in velachery["metrics"])
    assert len(velachery["suggestions"]) > 0
    assert len(reports) >= 2
    print({
        "health": health["status"],
        "velachery": {"score": velachery["score"], "states": velachery_states, "report_id": velachery["id"]},
        "cell": {"score": cell["score"], "states": cell_states, "report_id": cell["id"]},
        "comparison_delta": comparison["score_delta"],
        "saved_report_count": len(reports),
    })


if __name__ == "__main__":
    main()
