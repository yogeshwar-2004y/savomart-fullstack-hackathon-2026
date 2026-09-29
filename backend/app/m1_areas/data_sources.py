from typing import Any

from geoalchemy2.shape import to_shape
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import OperationalStore


def list_chennai_stores(db: Session) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(OperationalStore)
        .where(OperationalStore.is_operational.is_(True), OperationalStore.zone == "CHN")
        .order_by(OperationalStore.name)
    ).all()
    return [{
        "store_code": row.store_code, "name": row.name, "address": row.address,
        "latitude": to_shape(row.location).y, "longitude": to_shape(row.location).x,
        "source": row.source_name, "source_url": row.source_url,
        "source_status": row.source_status, "retrieved_at": row.retrieved_at,
    } for row in rows]


def census_proxy_for_area(db: Session, area_id: str) -> dict[str, Any] | None:
    row = db.execute(text("""
        SELECT COUNT(*) AS ward_count,
               SUM(w.population_2011 * ST_Area(ST_Intersection(w.geometry, a.geometry)::geography)
                   / NULLIF(ST_Area(w.geometry::geography), 0)) AS population_proxy,
               SUM(w.households_2011 * ST_Area(ST_Intersection(w.geometry, a.geometry)::geography)
                   / NULLIF(ST_Area(w.geometry::geography), 0)) AS household_proxy,
               MAX(w.retrieved_at) AS retrieved_at,
               MAX(w.census_source_url) AS source_url
        FROM ward_census w
        JOIN areas a ON a.id = CAST(:area_id AS uuid)
        WHERE ST_Intersects(w.geometry, a.geometry)
    """), {"area_id": area_id}).mappings().one()
    if not row["ward_count"] or row["population_proxy"] is None:
        return None
    return {
        "population_proxy": round(float(row["population_proxy"])),
        "household_proxy": round(float(row["household_proxy"])),
        "ward_count": int(row["ward_count"]),
        "retrieved_at": row["retrieved_at"], "source_url": row["source_url"],
    }
