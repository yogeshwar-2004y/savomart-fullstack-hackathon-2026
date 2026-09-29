from datetime import UTC, datetime

from app.scoring.area_v1 import SCORING_VERSION, deterministic_summary, score_area


def test_area_fitness_v2_calculation_is_deterministic() -> None:
    provenance = {
        "geography": "selected polygon", "osm_source": "test OSM", "osm_url": None,
        "osm_kind": "live", "osm_limitations": "test limitation", "store_source": "test stores",
        "store_kind": "live", "store_limitations": "straight line", "cache_age_seconds": None,
    }
    score, rating, metrics = score_area(
        area_sq_km=4,
        counts={"residential": 120, "businesses": 80, "amenities": 40, "access": 50, "competition": 16},
        nearest_store_km=1.5,
        provenance=provenance,
        fetched_at=datetime(2026, 9, 28, tzinfo=UTC),
    )

    assert score == 50.0
    assert rating == "Needs validation"
    assert sum(metric["weight"] for metric in metrics) == 1
    assert [metric["contribution"] for metric in metrics[:6]] == [12.5, 10.0, 10.0, 7.5, 5.0, 5.0]
    people_metric = next(metric for metric in metrics if metric["category"] == "people")
    assert people_metric["evidence_kind"] == "missing"
    assert SCORING_VERSION in deterministic_summary(score, rating, metrics)


def test_missing_store_signal_uses_documented_neutral_value() -> None:
    provenance = {
        "geography": "selected polygon", "osm_source": "test OSM", "osm_url": None,
        "osm_kind": "live", "osm_limitations": "test limitation", "store_source": "unavailable",
        "store_kind": "missing", "store_limitations": "not fetched", "cache_age_seconds": None,
    }
    _, _, metrics = score_area(
        area_sq_km=2, counts={}, nearest_store_km=None,
        provenance=provenance, fetched_at=datetime.now(UTC),
    )

    store_metric = next(metric for metric in metrics if metric["key"] == "savomart_coverage_gap")
    assert store_metric["raw_value"] is None
    assert store_metric["normalized_value"] == 0.5
    assert store_metric["contribution"] == 5.0


def test_store_coverage_gap_reaches_maximum_at_three_km() -> None:
    provenance = {
        "geography": "selected polygon", "osm_source": "test OSM", "osm_url": None,
        "osm_kind": "live", "osm_limitations": "test limitation", "store_source": "test stores",
        "store_kind": "live", "store_limitations": "straight line", "cache_age_seconds": None,
    }
    _, _, metrics = score_area(
        area_sq_km=2, counts={}, nearest_store_km=3.0,
        provenance=provenance, fetched_at=datetime.now(UTC),
    )

    store_metric = next(metric for metric in metrics if metric["key"] == "savomart_coverage_gap")
    assert store_metric["normalized_value"] == 1.0
    assert store_metric["contribution"] == 10.0


def test_census_proxy_is_informational_and_does_not_change_score() -> None:
    fetched_at = datetime(2026, 9, 29, tzinfo=UTC)
    provenance = {
        "geography": "selected polygon", "osm_source": "test OSM", "osm_url": None,
        "osm_kind": "live", "osm_limitations": "test limitation", "store_source": "test stores",
        "store_kind": "snapshot", "store_limitations": "straight line", "cache_age_seconds": None,
    }
    baseline, _, _ = score_area(
        area_sq_km=2, counts={}, nearest_store_km=2, provenance=provenance, fetched_at=fetched_at,
    )
    score, _, metrics = score_area(
        area_sq_km=2, counts={}, nearest_store_km=2, provenance=provenance, fetched_at=fetched_at,
        population_proxy={
            "population_proxy": 12000, "household_proxy": 3100, "ward_count": 2,
            "retrieved_at": fetched_at, "source_url": "https://example.test/gcc-census",
        },
    )

    people = [metric for metric in metrics if metric["category"] == "people"]
    assert score == baseline
    assert len(people) == 2
    assert all(metric["weight"] == 0 and metric["evidence_kind"] == "proxy" for metric in people)
    assert people[0]["raw_value"] == 12000
