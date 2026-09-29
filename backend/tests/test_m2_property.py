import io
from datetime import UTC, datetime

import pytest
from PIL import Image

from app.m2_properties.photos import InvalidPhoto, inspect_photo
from app.scoring.property_v1 import SCORING_VERSION, score_property, validate_transition


def test_property_score_is_deterministic_and_versioned() -> None:
    now = datetime(2026, 9, 29, tzinfo=UTC)
    values = {
        "rent_monthly": 120_000, "size_sq_ft": 2_000, "frontage_ft": 30, "road_width_ft": 40,
        "visibility_rating": 4, "condition_rating": 4, "parking_available": True,
        "power_backup": True, "water_available": True,
        "osm_counts": {"businesses": 20, "amenities": 15, "access": 10, "competition": 2},
        "osm_source": "OpenStreetMap", "osm_kind": "live", "osm_limitations": "Mapped features only.",
        "nearest_store_km": 3, "store_source": "Store service", "store_kind": "live",
        "store_limitations": "Straight-line distance.", "fetched_at": now,
    }
    first = score_property(**values)
    second = score_property(**values)

    assert first == second
    assert first["score"] == 83.1
    assert first["rating"] == "Strong candidate"
    assert sum(metric["weight"] for metric in first["metrics"]) == pytest.approx(1)
    assert SCORING_VERSION == "property-fitness-v1"


def test_pipeline_rejects_invalid_transition() -> None:
    validate_transition("scouted", "shortlisted")
    validate_transition("shortlisted", "survey_requested")
    validate_transition("survey_requested", "under_review")
    with pytest.raises(ValueError, match="Cannot move"):
        validate_transition("scouted", "approved")


def test_photo_inspection_uses_actual_content() -> None:
    output = io.BytesIO()
    Image.new("RGB", (8, 8), "yellow").save(output, format="PNG")
    content_type, extension = inspect_photo(output.getvalue(), "image/png", 1024 * 1024)
    assert (content_type, extension) == ("image/png", ".png")

    with pytest.raises(InvalidPhoto, match="does not match"):
        inspect_photo(output.getvalue(), "image/jpeg", 1024 * 1024)
    with pytest.raises(InvalidPhoto, match="valid JPEG"):
        inspect_photo(b"not an image", "image/png", 1024 * 1024)


def test_photo_inspection_rejects_excessive_dimensions(monkeypatch) -> None:
    class OversizedImage:
        width = 10_000
        height = 5_000

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr("app.m2_properties.photos.Image.open", lambda _content: OversizedImage())
    with pytest.raises(InvalidPhoto, match="40 megapixel"):
        inspect_photo(b"image bytes", "image/png", 1024 * 1024)


def test_photo_inspection_handles_pillow_decompression_guard(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.m2_properties.photos.Image.open",
        lambda _content: (_ for _ in ()).throw(Image.DecompressionBombError("too many pixels")),
    )
    with pytest.raises(InvalidPhoto, match="valid JPEG"):
        inspect_photo(b"image bytes", "image/png", 1024 * 1024)
