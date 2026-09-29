"""Run a fresh persisted M1 -> M2 -> M3 journey through the local API."""

import io
import json
import sys
from datetime import UTC, datetime
from uuid import uuid4

import httpx
from PIL import Image
from shapely.geometry import box, shape

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/api/v1"
MANAGER = {"X-Demo-Role": "bd-manager", "X-Demo-User-Id": "bd-manager-1"}
EXECUTIVE = {"X-Demo-Role": "bd-executive", "X-Demo-User-Id": "bd-executive-1"}
OTHER_EXECUTIVE = {"X-Demo-Role": "bd-executive", "X-Demo-User-Id": "bd-executive-2"}
SURVEY_MANAGER = {"X-Demo-Role": "survey-manager", "X-Demo-User-Id": "survey-manager-1"}
SURVEY_EXECUTIVE = {"X-Demo-Role": "survey-executive", "X-Demo-User-Id": "survey-executive-1"}
OTHER_SURVEY_EXECUTIVE = {"X-Demo-Role": "survey-executive", "X-Demo-User-Id": "survey-executive-2"}


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def choose_uncovered_cell(client: httpx.Client) -> tuple[float, float]:
    studies = client.get(f"{BASE_URL}/catchment-studies", headers=MANAGER).raise_for_status().json()
    completed = [shape(item["target_geometry"]) for item in studies if item["status"] == "completed"]
    candidates = (
        (80.06, 12.76), (80.10, 12.76), (80.14, 12.76), (80.28, 12.76),
        (80.32, 12.76), (80.06, 13.10), (80.32, 13.10), (80.06, 13.24),
        (80.12, 13.24), (80.28, 13.24), (80.32, 13.24),
    )
    for west, south in candidates:
        candidate = box(west, south, west + 0.01, south + 0.01)
        if all(candidate.distance(geometry) > 0.025 for geometry in completed):
            return west, south
    raise RuntimeError("No isolated Chennai verification cell remains; reset demo volumes or add a candidate")


def main() -> None:
    client = httpx.Client(timeout=45)
    marker = uuid4().hex[:10]
    west, south = choose_uncovered_cell(client)
    ring = [
        [west, south], [west + 0.01, south], [west + 0.01, south + 0.01],
        [west, south + 0.01], [west, south],
    ]
    accepted = client.post(
        f"{BASE_URL}/areas/analyses",
        headers=MANAGER,
        json={"area": {
            "name": f"E2E Chennai {marker}",
            "query": "E2E verification cell",
            "selection_method": "cells",
            "geometry": {"type": "MultiPolygon", "coordinates": [[ring]]},
            "source": "User-selected Chennai map cell",
            "source_id": f"verification:{marker}",
            "boundary_type": "user-selected",
            "lookup_at": datetime.now(UTC).isoformat(),
            "is_official": False,
            "is_approximate": False,
        }},
    ).raise_for_status().json()

    report = None
    for _ in range(10_000):
        job = client.get(f'{BASE_URL}/jobs/{accepted["job_id"]}').raise_for_status().json()
        if job["status"] == "completed" and job["report_id"]:
            report = client.get(f'{BASE_URL}/area-reports/{job["report_id"]}', headers=MANAGER).raise_for_status().json()
            break
        if job["status"] == "failed":
            raise RuntimeError(f'M1 job failed: {job["status_detail"]}')
    check(report is not None and bool(report["suggestions"]), "M1 did not produce a saved report and hotspot")

    suggestion = report["suggestions"][0]
    assignment = client.post(
        f"{BASE_URL}/scout-assignments",
        headers=MANAGER,
        json={
            "area_report_id": report["id"], "suggestion_id": suggestion["id"],
            "assignee_id": "bd-executive-1", "instructions": f"E2E walkthrough {marker}",
        },
    ).raise_for_status().json()
    owned = client.get(f"{BASE_URL}/scout-assignments", headers=EXECUTIVE).raise_for_status().json()
    hidden = client.get(f"{BASE_URL}/scout-assignments", headers=OTHER_EXECUTIVE).raise_for_status().json()
    check(any(item["id"] == assignment["id"] for item in owned), "Assignment is not visible to its owner")
    check(not any(item["id"] == assignment["id"] for item in hidden), "Assignment leaked to another executive")

    capture = {
        "latitude": suggestion["latitude"], "longitude": suggestion["longitude"],
        "address": f"E2E SiteScout {marker}, Chennai", "rent_monthly": 125000,
        "size_sq_ft": 2100, "frontage_ft": 30, "road_width_ft": 36,
        "property_type": "street_shop", "floor_level": "ground", "visibility_rating": 4,
        "condition_rating": 4, "parking_available": True, "power_backup": True,
        "water_available": True, "notes": "Automated end-to-end verification record.",
    }
    unauthorized = client.post(
        f'{BASE_URL}/scout-assignments/{assignment["id"]}/properties',
        headers=OTHER_EXECUTIVE, data={"payload": json.dumps(capture)},
    )
    check(unauthorized.status_code == 404, "Another executive could submit a property")
    image = io.BytesIO()
    Image.new("RGB", (32, 24), "#FFF200").save(image, "JPEG")
    prop = client.post(
        f'{BASE_URL}/scout-assignments/{assignment["id"]}/properties',
        headers=EXECUTIVE, data={"payload": json.dumps(capture)},
        files=[("photos", ("e2e-property.jpg", image.getvalue(), "image/jpeg"))],
    ).raise_for_status().json()
    check([item["version"] for item in prop["evaluations"]] == [1], "M2 did not persist evaluation v1")
    check(prop["evaluations"][0]["scoring_version"] == "property-fitness-v1", "M2 score version mismatch")
    check(len(prop["photos"]) == 1, "M2 did not persist the validated property photo")

    for stage, reason in (
        ("shortlisted", "E2E verification shortlist"),
        ("survey_requested", "E2E verification requests catchment evidence"),
    ):
        prop = client.post(
            f'{BASE_URL}/properties/{prop["id"]}/stage', headers=MANAGER,
            json={"stage": stage, "reason": reason},
        ).raise_for_status().json()

    study = client.post(
        f"{BASE_URL}/catchment-studies", headers=MANAGER,
        json={"target_type": "property", "target_id": prop["id"]},
    ).raise_for_status().json()
    check(study["status"] == "requested", "Fresh E2E property unexpectedly matched existing catchment coverage")
    planned = client.post(
        f'{BASE_URL}/catchment-studies/{study["id"]}/zones', headers=SURVEY_MANAGER,
        json={"zone_count": 2, "assignee_ids": ["survey-executive-1"]},
    ).raise_for_status().json()
    check(len(planned["zones"]) == 2, "Survey Manager did not create two zones")

    zones = client.get(f"{BASE_URL}/survey-zones", headers=SURVEY_EXECUTIVE).raise_for_status().json()
    owned_zone_ids = {zone["id"] for zone in zones}
    check(all(zone["id"] in owned_zone_ids for zone in planned["zones"]), "Survey assignment is missing for its executive")
    wrong_owner = client.post(
        f'{BASE_URL}/survey-zones/{planned["zones"][0]["id"]}/submissions',
        headers=OTHER_SURVEY_EXECUTIVE,
        json={
            "client_submission_id": str(uuid4()), "lane_name": "Unauthorized E2E lane",
            "latitude": suggestion["latitude"], "longitude": suggestion["longitude"],
            "gps_accuracy_m": 15, "observed_at": datetime.now(UTC).isoformat(),
            "residential_units": 60, "commercial_units": 15,
            "pedestrian_activity": 4, "vehicle_activity": 3,
        },
    )
    check(wrong_owner.status_code == 404, "Another survey executive accessed the assigned zone")

    for zone in planned["zones"]:
        point = shape(zone["geometry"]).representative_point()
        payload = {
            "client_submission_id": str(uuid4()), "lane_name": f'{zone["label"]} E2E lane {marker}',
            "latitude": point.y, "longitude": point.x, "gps_accuracy_m": 15,
            "observed_at": datetime.now(UTC).isoformat(), "residential_units": 60,
            "commercial_units": 15, "pedestrian_activity": 4, "vehicle_activity": 3,
            "notes": "Automated workflow sample, not a real field observation.", "evidence_kind": "demo",
        }
        saved = client.post(
            f'{BASE_URL}/survey-zones/{zone["id"]}/submissions', headers=SURVEY_EXECUTIVE, json=payload,
        ).raise_for_status().json()
        repeated = client.post(
            f'{BASE_URL}/survey-zones/{zone["id"]}/submissions', headers=SURVEY_EXECUTIVE, json=payload,
        ).raise_for_status().json()
        check(saved["id"] == repeated["id"], "Lane submission retry created a duplicate")
        client.post(
            f'{BASE_URL}/survey-zones/{zone["id"]}/complete', headers=SURVEY_EXECUTIVE,
        ).raise_for_status()

    final = client.get(f'{BASE_URL}/properties/{prop["id"]}', headers=MANAGER).raise_for_status().json()
    completed_study = client.get(
        f'{BASE_URL}/catchment-studies/{study["id"]}', headers=MANAGER,
    ).raise_for_status().json()
    versions = [item["version"] for item in final["evaluations"]]
    check(versions == [1, 2], f"Expected append-only evaluation versions [1, 2], got {versions}")
    check(final["evaluations"][0]["scoring_version"] == "property-fitness-v1", "Original evaluation was changed")
    check(final["evaluations"][1]["scoring_version"] == "property-fitness-v2-catchment", "Catchment evaluation missing")
    check(final["stage"] == "under_review", "Completed catchment did not return property to manager review")
    check(any("Score changed from" in item for item in final["evaluations"][1]["insights"]), "Score-change explanation missing")
    check(completed_study["status"] == "completed", "Catchment study did not complete")
    check(completed_study["summary"]["evidence_kind"] == "demo", "Walkthrough observations are not labelled demo")

    print({
        "area_report_id": report["id"],
        "assignment_id": assignment["id"],
        "property_id": prop["id"],
        "study_id": study["id"],
        "zone_count": len(planned["zones"]),
        "evaluation_versions": versions,
        "property_photo_count": len(final["photos"]),
        "scores": [item["score"] for item in final["evaluations"]],
        "final_stage": final["stage"],
        "evidence_kind": completed_study["summary"]["evidence_kind"],
        "role_ownership_checks": "passed",
    })


if __name__ == "__main__":
    main()
