from dataclasses import dataclass
from datetime import datetime
from typing import Any

SCORING_VERSION = "area-fitness-v2"


@dataclass(frozen=True)
class MetricRule:
    key: str
    category: str
    label: str
    weight: float
    cap_per_sq_km: float | None = None
    inverse: bool = False


RULES = (
    MetricRule("residential_density", "homes", "Mapped residential buildings", 0.25, 60),
    MetricRule("business_density", "businesses", "Mapped shops and offices", 0.20, 40),
    MetricRule("amenity_density", "amenities", "Mapped daily-life amenities", 0.20, 20),
    MetricRule("access_density", "mobility", "Mapped transit and major-road access", 0.15, 25),
    MetricRule("competition_headroom", "competition", "Competition headroom", 0.10, 8, True),
    MetricRule("savomart_coverage_gap", "savomart", "Distance to nearest Savomart", 0.10),
)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_area(
    *, area_sq_km: float, counts: dict[str, float], nearest_store_km: float | None,
    provenance: dict[str, Any], fetched_at: datetime, nearby_store_count: int | None = None,
) -> tuple[float, str, list[dict[str, Any]]]:
    values = {
        "residential_density": counts.get("residential", 0) / area_sq_km,
        "business_density": counts.get("businesses", 0) / area_sq_km,
        "amenity_density": counts.get("amenities", 0) / area_sq_km,
        "access_density": counts.get("access", 0) / area_sq_km,
        "competition_headroom": counts.get("competition", 0) / area_sq_km,
        "savomart_coverage_gap": nearest_store_km,
    }
    metrics: list[dict[str, Any]] = []
    for rule in RULES:
        raw = values[rule.key]
        if rule.key == "savomart_coverage_gap":
            normalized = 0.5 if raw is None else _clamp(float(raw) / 3.0)
            transformation = "min(nearest_store_km / 3, 1); neutral 0.5 when store data is unavailable"
            raw_unit = "km"
            limitation = provenance.get("store_limitations", "Straight-line distance, not travel time.")
            source_name = provenance.get("store_source", "Savomart store service")
            source_url = None
            kind = provenance.get("store_kind", "live")
        else:
            density = float(raw)
            normalized = _clamp(density / float(rule.cap_per_sq_km))
            if rule.inverse:
                normalized = 1 - normalized
            transformation = (
                f"1 - min(count / area_sq_km / {rule.cap_per_sq_km}, 1)" if rule.inverse
                else f"min(count / area_sq_km / {rule.cap_per_sq_km}, 1)"
            )
            raw_unit = "features per sq km"
            limitation = provenance["osm_limitations"]
            source_name = provenance["osm_source"]
            source_url = provenance.get("osm_url")
            kind = provenance["osm_kind"]
        contribution = round(normalized * rule.weight * 100, 2)
        metrics.append({
            "key": rule.key, "category": rule.category, "label": rule.label,
            "raw_value": None if raw is None else round(float(raw), 3), "raw_unit": raw_unit,
            "normalized_value": round(normalized, 4), "weight": rule.weight,
            "contribution": contribution, "source_name": source_name, "source_url": source_url,
            "fetched_at": fetched_at, "geography": provenance["geography"],
            "transformation": transformation, "limitations": limitation,
            "evidence_kind": kind, "cache_age_seconds": provenance.get("cache_age_seconds"),
        })
    metrics.append({
        "key": "population", "category": "people", "label": "Population and household counts",
        "raw_value": None, "raw_unit": "unavailable", "normalized_value": 0.0, "weight": 0.0,
        "contribution": 0.0, "source_name": "No approved people dataset configured", "source_url": None,
        "fetched_at": fetched_at, "geography": provenance["geography"],
        "transformation": f"Excluded from {SCORING_VERSION}; no proxy is converted into a people estimate.",
        "limitations": "OpenStreetMap feature counts are not population or household data. Validate demand through an approved demographic source or field study.",
        "evidence_kind": "missing", "cache_age_seconds": None,
    })
    metrics.append({
        "key": "nearby_savomart_stores", "category": "savomart", "label": "Savomart stores within 5 km",
        "raw_value": None if nearby_store_count is None else float(nearby_store_count), "raw_unit": "stores",
        "normalized_value": 0.0, "weight": 0.0, "contribution": 0.0,
        "source_name": provenance.get("store_source", "Savomart store service"), "source_url": None,
        "fetched_at": fetched_at, "geography": provenance["geography"],
        "transformation": "Count of supplied store points within 5 km of the selected-area centroid; informational only.",
        "limitations": provenance.get("store_limitations", "Straight-line distance, not travel time."),
        "evidence_kind": provenance.get("store_kind", "live"), "cache_age_seconds": None,
    })
    total = round(sum(metric["contribution"] for metric in metrics), 1)
    rating = "Strong fit" if total >= 70 else "Promising" if total >= 55 else "Needs validation" if total >= 40 else "Low evidence fit"
    return total, rating, metrics


def deterministic_summary(score: float, rating: str, metrics: list[dict[str, Any]]) -> str:
    scored_metrics = [metric for metric in metrics if metric["weight"] > 0]
    ranked = sorted(scored_metrics, key=lambda item: item["contribution"], reverse=True)
    strongest = ", ".join(item["label"].lower() for item in ranked[:2])
    weakest = min(scored_metrics, key=lambda item: item["normalized_value"])["label"].lower()
    return (
        f"{rating} at {score:.1f}/100 under {SCORING_VERSION}. The largest contributions are "
        f"{strongest}. The weakest available signal is {weakest}. Mapped feature counts are coverage "
        "signals, not population or household estimates; field scouting should validate the result."
    )
