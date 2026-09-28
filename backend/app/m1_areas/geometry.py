from math import cos, radians
from typing import Any

from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.geometry.base import BaseGeometry

CHENNAI_BOUNDS = (80.05, 12.75, 80.35, 13.30)

VELACHERY_GEOMETRY: dict[str, Any] = {
    "type": "Polygon",
    "coordinates": [[
        [80.1942, 12.9848], [80.1987, 12.9914], [80.2129, 12.9921],
        [80.2248, 12.9841], [80.2262, 12.9720], [80.2171, 12.9602],
        [80.2031, 12.9610], [80.1940, 12.9713], [80.1942, 12.9848],
    ]],
}


class InvalidAreaGeometry(ValueError):
    pass


def normalize_area_geometry(geojson: dict[str, Any]) -> MultiPolygon:
    try:
        geometry = shape(geojson)
    except Exception as exc:
        raise InvalidAreaGeometry("Invalid GeoJSON geometry") from exc
    if isinstance(geometry, Polygon):
        geometry = MultiPolygon([geometry])
    if not isinstance(geometry, MultiPolygon) or geometry.is_empty:
        raise InvalidAreaGeometry("Area must be a Polygon or MultiPolygon")
    if not geometry.is_valid:
        geometry = geometry.buffer(0)
    if not isinstance(geometry, MultiPolygon):
        geometry = MultiPolygon([geometry])
    min_lon, min_lat, max_lon, max_lat = geometry.bounds
    c_min_lon, c_min_lat, c_max_lon, c_max_lat = CHENNAI_BOUNDS
    if min_lon < c_min_lon or max_lon > c_max_lon or min_lat < c_min_lat or max_lat > c_max_lat:
        raise InvalidAreaGeometry("Selected geometry must stay within Greater Chennai")
    area = area_sq_km(geometry)
    if area < 0.02 or area > 150:
        raise InvalidAreaGeometry("Selected area must be between 0.02 and 150 square kilometres")
    return geometry


def area_sq_km(geometry: BaseGeometry) -> float:
    latitude = geometry.centroid.y
    return round(geometry.area * 111.32 * 111.32 * cos(radians(latitude)), 3)


def as_geojson(geometry: BaseGeometry) -> dict[str, Any]:
    return mapping(geometry)
