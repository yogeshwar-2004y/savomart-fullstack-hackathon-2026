import os

import pytest
from geoalchemy2 import Geography
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import cast, func, select

from app.db.session import SessionLocal
from app.m2_properties.service import property_evidence_geometry

pytestmark = pytest.mark.skipif(
    os.getenv("SAVO_RUN_POSTGIS_TESTS") != "1",
    reason="Set SAVO_RUN_POSTGIS_TESTS=1 to run against a PostGIS database",
)


def test_property_evidence_buffer_is_750_metres_in_postgis() -> None:
    center = from_shape(Point(80.22, 12.98), srid=4326)
    with SessionLocal() as db:
        buffered = property_evidence_geometry(center, 750, db)
        boundary = from_shape(buffered.boundary, srid=4326)
        distance = db.scalar(
            select(func.ST_Distance(cast(center, Geography), cast(boundary, Geography)))
        )

    assert buffered.geom_type == "MultiPolygon"
    assert distance == pytest.approx(750, abs=1)
