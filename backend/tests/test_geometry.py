import pytest

from app.m1_areas.geometry import (
    InvalidAreaGeometry,
    area_sq_km,
    normalize_area_geometry,
    normalize_chennai_point,
)

VELACHERY_TEST_POLYGON = {
    "type": "Polygon",
    "coordinates": [[[80.20, 12.97], [80.22, 12.97], [80.22, 12.99], [80.20, 12.99], [80.20, 12.97]]],
}


def test_velachery_selection_is_valid_chennai_multipolygon() -> None:
    geometry = normalize_area_geometry(VELACHERY_TEST_POLYGON)

    assert geometry.geom_type == "MultiPolygon"
    assert 1 < area_sq_km(geometry) < 20
    assert geometry.centroid.x == pytest.approx(80.21, abs=0.02)
    assert geometry.centroid.y == pytest.approx(12.98, abs=0.02)


def test_selection_outside_chennai_is_rejected() -> None:
    with pytest.raises(InvalidAreaGeometry, match="Greater Chennai"):
        normalize_area_geometry({
            "type": "Polygon",
            "coordinates": [[[77.58, 12.95], [77.59, 12.95], [77.59, 12.96], [77.58, 12.96], [77.58, 12.95]]],
        })


def test_reversed_point_coordinates_are_rejected() -> None:
    with pytest.raises(InvalidAreaGeometry, match="Greater Chennai"):
        normalize_chennai_point({"type": "Point", "coordinates": [12.98, 80.21]})
