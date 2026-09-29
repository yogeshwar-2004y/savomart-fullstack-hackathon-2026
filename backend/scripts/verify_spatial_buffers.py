"""Check that the M2 OSM evidence polygon has a metre-accurate PostGIS radius."""

from geoalchemy2 import Geography
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import cast, func, select

from app.db.session import SessionLocal
from app.m2_properties.service import property_evidence_geometry


def main() -> None:
    center = from_shape(Point(80.22, 12.98), srid=4326)
    with SessionLocal() as db:
        buffered = property_evidence_geometry(center, 750, db)
        boundary = from_shape(buffered.boundary, srid=4326)
        distance_m = db.scalar(
            select(func.ST_Distance(cast(center, Geography), cast(boundary, Geography)))
        )
    if buffered.geom_type != "MultiPolygon" or abs(float(distance_m) - 750) > 1:
        raise RuntimeError(f"Expected a 750 m geography buffer, got {distance_m} m")
    print(f"M2 PostGIS buffer boundary: {distance_m:.2f} m")


if __name__ == "__main__":
    main()
