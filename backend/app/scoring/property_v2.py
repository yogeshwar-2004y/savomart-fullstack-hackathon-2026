from copy import deepcopy
from datetime import datetime
from typing import Any

SCORING_VERSION = "property-fitness-v2-catchment"


def score_with_catchment(
    previous_metrics: list[dict[str, Any]],
    summary: dict[str, Any],
    fetched_at: datetime,
) -> dict[str, Any]:
    observations = max(int(summary.get("observation_count", 0)), 1)
    residential_per_observation = float(summary.get("residential_units", 0)) / observations
    commercial_per_observation = float(summary.get("commercial_units", 0)) / observations
    pedestrian = float(summary.get("average_pedestrian_activity", 0))
    vehicle = float(summary.get("average_vehicle_activity", 0))
    normalized = min(
        1.0,
        0.40 * min(residential_per_observation / 80, 1)
        + 0.25 * min(commercial_per_observation / 20, 1)
        + 0.20 * min(pedestrian / 5, 1)
        + 0.15 * min(vehicle / 5, 1),
    )

    metrics = deepcopy(previous_metrics)
    for metric in metrics:
        metric["weight"] = round(float(metric["weight"]) * 0.9, 4)
        metric["contribution"] = round(float(metric["contribution"]) * 0.9, 2)
    catchment_contribution = round(normalized * 10, 2)
    metrics.append(
        {
            "key": "catchment_observations",
            "label": "Field-observed catchment demand",
            "raw_value": summary.get("observation_count", 0),
            "raw_unit": "submitted lane observations",
            "normalized_value": round(normalized, 4),
            "weight": 0.10,
            "contribution": catchment_contribution,
            "source": "Savo SiteScout lane survey",
            "fetched_at": fetched_at.isoformat(),
            "evidence_kind": str(summary.get("evidence_kind", "field-survey")),
            "transformation": (
                "40% residential units per observation, 25% commercial units per observation, "
                "20% pedestrian activity, and 15% vehicle activity; capped at 1"
            ),
            "limitations": (
                "Counts and activity ratings are executive observations, not a census or continuous footfall study."
            ),
        }
    )
    score = round(sum(float(metric["contribution"]) for metric in metrics), 1)
    rating = (
        "Strong candidate"
        if score >= 70
        else "Promising"
        if score >= 55
        else "Needs review"
        if score >= 40
        else "Weak candidate"
    )
    return {
        "score": score,
        "rating": rating,
        "recommendation": (
            "Review the property with completed catchment evidence."
            if score >= 55
            else "Hold for manager review; observed catchment evidence remains weak or incomplete."
        ),
        "metrics": metrics,
        "insights": [
            f"Catchment fieldwork contributed {catchment_contribution:.1f} points from {summary.get('observation_count', 0)} lane observations.",
            f"Survey coverage is {float(summary.get('coverage_percent', 0)):.1f}% across completed work zones.",
        ],
        "risks": [
            "One or more observations were outside their assigned zone and require review."
        ]
        if summary.get("location_mismatch_count", 0)
        else [],
        "limitations": [
            "Catchment observations are timestamped field samples and do not represent a census.",
            str(summary.get("limitations", "Coverage is limited to completed assigned zones.")),
        ],
        "source_snapshot_at": fetched_at,
    }
