from datetime import datetime
from typing import Any

SCORING_VERSION = "property-fitness-v1"


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _metric(
    key: str, label: str, raw_value: float | None, raw_unit: str, normalized: float,
    weight: float, source: str, fetched_at: datetime, evidence_kind: str,
    transformation: str, limitations: str,
) -> dict[str, Any]:
    normalized = _clamp(normalized)
    return {
        "key": key, "label": label, "raw_value": raw_value, "raw_unit": raw_unit,
        "normalized_value": round(normalized, 4), "weight": weight,
        "contribution": round(normalized * weight * 100, 2), "source": source,
        "fetched_at": fetched_at.isoformat(), "evidence_kind": evidence_kind,
        "transformation": transformation, "limitations": limitations,
    }


def score_property(
    *, rent_monthly: float, size_sq_ft: float, frontage_ft: float | None,
    road_width_ft: float | None, visibility_rating: int, condition_rating: int,
    parking_available: bool, power_backup: bool, water_available: bool,
    osm_counts: dict[str, float], osm_source: str, osm_kind: str, osm_limitations: str,
    nearest_store_km: float | None, store_source: str, store_kind: str,
    store_limitations: str, fetched_at: datetime,
) -> dict[str, Any]:
    rent_per_sq_ft = rent_monthly / size_sq_ft
    utilities = sum((parking_available, power_backup, water_available)) / 3
    activity_count = osm_counts.get("businesses", 0) + osm_counts.get("amenities", 0) + osm_counts.get("access", 0)
    competition = osm_counts.get("competition", 0)
    metrics = [
        _metric("rent_efficiency", "Rent efficiency", rent_per_sq_ft, "INR/sq ft/month", 1 - rent_per_sq_ft / 150, .20, "Field capture", fetched_at, "captured", "1 - min(rent per sq ft / 150, 1)", "Commercial viability still requires negotiation and finance review."),
        _metric("size_fit", "Store size fit", size_sq_ft, "sq ft", 1 if 1200 <= size_sq_ft <= 3000 else 0.6 if 800 <= size_sq_ft <= 4000 else 0.2, .15, "Field capture", fetched_at, "captured", "1.0 for 1,200-3,000; 0.6 for 800-4,000; otherwise 0.2", "Thresholds are initial Savomart scouting rules, not a lease approval."),
        _metric("frontage", "Frontage", frontage_ft, "ft", (frontage_ft or 0) / 30, .10, "Field capture", fetched_at, "captured" if frontage_ft is not None else "missing", "min(frontage / 30, 1); missing is 0", "Measurement is executive-reported and should be verified."),
        _metric("road_access", "Road access", road_width_ft, "ft", (road_width_ft or 0) / 40, .10, "Field capture", fetched_at, "captured" if road_width_ft is not None else "missing", "min(road width / 40, 1); missing is 0", "Road width is executive-reported; routing and turning access are not modeled."),
        _metric("visibility", "Street visibility", float(visibility_rating), "rating / 5", visibility_rating / 5, .10, "Field capture", fetched_at, "captured", "rating / 5", "Subjective field rating."),
        _metric("condition", "Property condition", float(condition_rating), "rating / 5", condition_rating / 5, .07, "Field capture", fetched_at, "captured", "rating / 5", "Subjective field rating; no engineering inspection."),
        _metric("utilities", "Access and utilities", float(sum((parking_available, power_backup, water_available))), "available / 3", utilities, .08, "Field capture", fetched_at, "captured", "available items / 3", "Availability is unverified at scouting stage."),
        _metric("mapped_activity", "Nearby mapped activity", activity_count, "OSM features within 750 m", activity_count / 60, .10, osm_source, fetched_at, osm_kind, "min((shops + amenities + access) / 60, 1)", osm_limitations),
        _metric("competition_headroom", "Competition headroom", competition, "mapped competitors within 750 m", 1 - competition / 10, .05, osm_source, fetched_at, osm_kind, "1 - min(mapped competitors / 10, 1)", osm_limitations),
        _metric("savomart_gap", "Savomart coverage gap", nearest_store_km, "straight-line km", .5 if nearest_store_km is None else nearest_store_km / 5, .05, store_source, fetched_at, store_kind, "min(nearest store km / 5, 1); unavailable uses neutral 0.5", store_limitations),
    ]
    score = round(sum(item["contribution"] for item in metrics), 1)
    rating = "Strong candidate" if score >= 70 else "Promising" if score >= 55 else "Needs review" if score >= 40 else "Weak candidate"
    top = sorted(metrics, key=lambda item: item["contribution"], reverse=True)[:3]
    insights = [f'{item["label"]} contributes {item["contribution"]:.1f} points.' for item in top]
    risks = []
    if rent_per_sq_ft > 120: risks.append("High asking rent per square foot.")
    if frontage_ft is None or frontage_ft < 15: risks.append("Frontage is missing or below 15 ft.")
    if road_width_ft is None or road_width_ft < 20: risks.append("Road access is missing or below 20 ft.")
    if osm_kind == "demo": risks.append("Nearby public-feature evidence is simulated and must be refreshed.")
    limitations = [osm_limitations, store_limitations, "Field inputs are self-reported and require manager validation."]
    recommendation = "Shortlist for manager review." if score >= 55 else "Hold for validation before advancing."
    return {"score": score, "rating": rating, "recommendation": recommendation, "metrics": metrics, "insights": insights, "risks": risks, "limitations": limitations}


ALLOWED_TRANSITIONS = {
    "scouted": {"shortlisted", "rejected"},
    "shortlisted": {"survey_requested", "under_review", "rejected"},
    "survey_requested": {"under_review", "rejected"},
    "under_review": {"approved", "rejected", "shortlisted"},
    "approved": set(),
    "rejected": {"shortlisted"},
}


def validate_transition(current: str, target: str) -> None:
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"Cannot move property from {current} to {target}")
