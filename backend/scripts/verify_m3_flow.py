"""Exercise property catchment request -> zones -> lane surveys -> score version."""

import sys
from datetime import UTC, datetime
from uuid import uuid4

import httpx
from shapely.geometry import shape

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/api/v1"
BD_MANAGER = {"X-Demo-Role": "bd-manager", "X-Demo-User-Id": "bd-manager-1"}
SURVEY_MANAGER = {"X-Demo-Role": "survey-manager", "X-Demo-User-Id": "survey-manager-1"}
SURVEY_EXECUTIVES = {
    "survey-executive-1": {"X-Demo-Role": "survey-executive", "X-Demo-User-Id": "survey-executive-1"},
    "survey-executive-2": {"X-Demo-Role": "survey-executive", "X-Demo-User-Id": "survey-executive-2"},
}


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    client = httpx.Client(timeout=45)
    properties = client.get(f"{BASE_URL}/properties", headers=BD_MANAGER).raise_for_status().json()
    prop = next(
        (
            item for item in properties
            if item["area_name"].strip().lower() == "velachery" and item["stage"] == "survey_requested"
        ),
        None,
    )
    if not prop:
        raise RuntimeError("Run verify_m1_flow.py and verify_m2_flow.py first to create a Velachery survey request")
    first_version = prop["evaluations"][-1]["version"]

    property_study = client.post(
        f"{BASE_URL}/catchment-studies",
        headers=BD_MANAGER,
        json={"target_type": "property", "target_id": prop["id"]},
    ).raise_for_status().json()
    check(property_study["status"] in {"requested", "reused"}, "Unexpected property study state")

    if property_study["status"] == "reused":
        check(property_study["source_study_id"], "Reused study is missing its source")
        check(
            property_study["reuse_coverage"] >= 80 and not property_study["zones"],
            "Eligible cached coverage created duplicate survey work",
        )
        reused_property = client.get(
            f'{BASE_URL}/properties/{prop["id"]}', headers=BD_MANAGER,
        ).raise_for_status().json()
        check(reused_property["stage"] == "under_review", "Catchment reuse did not return the property to review")
        check(
            reused_property["evaluations"][-1]["version"] == first_version + 1,
            "Catchment reuse did not append a property evaluation",
        )
        check(
            reused_property["evaluations"][-1]["scoring_version"] == "property-fitness-v2-catchment",
            "Catchment reuse did not use the M3 scoring version",
        )
        study, target_type, target_id = find_uncovered_area_study(client)
    else:
        study = property_study
        target_type, target_id = "property", prop["id"]

    planned = client.post(
        f'{BASE_URL}/catchment-studies/{study["id"]}/zones',
        headers=SURVEY_MANAGER,
        json={
            "zone_count": 2,
            "assignee_ids": ["survey-executive-1", "survey-executive-2"],
        },
    ).raise_for_status().json()
    check(len(planned["zones"]) == 2, "The catchment was not split into two zones")
    left = shape(planned["zones"][0]["geometry"])
    right = shape(planned["zones"][1]["geometry"])
    check(left.intersection(right).area <= 1e-12, "Planned survey zones overlap")

    first_zone = planned["zones"][0]
    wrong_headers = SURVEY_EXECUTIVES["survey-executive-2"]
    if first_zone["assignee_id"] == "survey-executive-2":
        wrong_headers = SURVEY_EXECUTIVES["survey-executive-1"]
    unauthorized = client.post(
        f'{BASE_URL}/survey-zones/{first_zone["id"]}/submissions',
        headers=wrong_headers,
        json=lane_payload(first_zone),
    )
    check(unauthorized.status_code == 404, "A survey executive accessed another executive's zone")

    first_submission_id = None
    for zone in planned["zones"]:
        headers = SURVEY_EXECUTIVES[zone["assignee_id"]]
        payload = lane_payload(zone)
        submitted = client.post(
            f'{BASE_URL}/survey-zones/{zone["id"]}/submissions', headers=headers, json=payload,
        ).raise_for_status().json()
        repeated = client.post(
            f'{BASE_URL}/survey-zones/{zone["id"]}/submissions', headers=headers, json=payload,
        ).raise_for_status().json()
        check(submitted["id"] == repeated["id"], "A retry created a duplicate lane observation")
        first_submission_id = first_submission_id or submitted["id"]
        client.post(
            f'{BASE_URL}/survey-zones/{zone["id"]}/complete', headers=headers,
        ).raise_for_status()

    completed = client.get(
        f'{BASE_URL}/catchment-studies/{study["id"]}', headers=BD_MANAGER,
    ).raise_for_status().json()
    check(completed["status"] == "completed", "Study did not complete after all zones completed")
    check(completed["summary"]["new_observation_count"] == 2, "New lane observations were not aggregated")
    check(completed["summary"]["observation_count"] >= 2, "Combined catchment evidence is incomplete")
    check(completed["summary"]["coverage_percent"] >= 99, "Completed zones did not cover the target")
    check(completed["summary"]["evidence_kind"] == "demo", "Scripted observations were not labelled demo")

    updated = client.get(f'{BASE_URL}/properties/{prop["id"]}', headers=BD_MANAGER).raise_for_status().json()
    if target_type == "property":
        check(updated["stage"] == "under_review", "Completed catchment did not return the property to review")
        check(updated["evaluations"][-1]["version"] == first_version + 1, "Property evaluation was not versioned")
        check(
            updated["evaluations"][-1]["scoring_version"] == "property-fitness-v2-catchment",
            "Catchment scoring version was not recorded",
        )

    reused = client.post(
        f"{BASE_URL}/catchment-studies",
        headers=BD_MANAGER,
        json={"target_type": target_type, "target_id": target_id},
    ).raise_for_status().json()
    check(reused["status"] == "reused", "Recent completed study was not reused")
    check(reused["source_study_id"] == study["id"], "Reuse source study was not recorded")
    check(reused["reuse_coverage"] >= 80 and not reused["zones"], "Reused study created duplicate survey work")

    print({
        "property_id": prop["id"],
        "property_study_status": property_study["status"],
        "study_id": study["id"],
        "study_target_type": target_type,
        "zones": len(planned["zones"]),
        "idempotent_submission_id": first_submission_id,
        "summary": completed["summary"],
        "evaluation_versions": [item["version"] for item in updated["evaluations"]],
        "updated_score": updated["evaluations"][-1]["score"],
        "reused_study_id": reused["id"],
        "reuse_coverage": reused["reuse_coverage"],
    })


def find_uncovered_area_study(client: httpx.Client) -> tuple[dict, str, str]:
    reports = client.get(f"{BASE_URL}/area-reports", headers=BD_MANAGER).raise_for_status().json()
    velachery_first = sorted(
        reports,
        key=lambda item: (item["area_name"].strip().lower() != "velachery", item["created_at"]),
    )
    for report in velachery_first:
        study = client.post(
            f"{BASE_URL}/catchment-studies",
            headers=BD_MANAGER,
            json={"target_type": "area_report", "target_id": report["id"]},
        ).raise_for_status().json()
        if study["status"] == "requested":
            return study, "area_report", report["id"]
    raise RuntimeError("No uncovered area report is available for the zone walkthrough")


def lane_payload(zone: dict) -> dict:
    point = shape(zone["geometry"]).representative_point()
    return {
        "client_submission_id": str(uuid4()),
        "lane_name": f'{zone["label"]} verification lane',
        "latitude": point.y,
        "longitude": point.x,
        "gps_accuracy_m": 15,
        "observed_at": datetime.now(UTC).isoformat(),
        "residential_units": 72,
        "commercial_units": 16,
        "pedestrian_activity": 4,
        "vehicle_activity": 3,
        "notes": "Simulated verification observation; not a real field survey.",
        "status": "submitted",
        "evidence_kind": "demo",
    }


if __name__ == "__main__":
    main()
