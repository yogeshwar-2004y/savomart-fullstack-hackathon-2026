"""Add operational stores and GCC ward census sources.

Revision ID: 20260929_0008
Revises: 20260929_0007
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "20260929_0008"
down_revision: str | None = "20260929_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "operational_stores",
        sa.Column("store_code", sa.String(40), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("address", sa.Text()),
        sa.Column("zone", sa.String(20)),
        sa.Column("is_operational", sa.Boolean(), nullable=False),
        sa.Column("location", geoalchemy2.Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("source_name", sa.String(160), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("source_status", sa.String(24), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_operational_stores_zone", "operational_stores", ["zone"])
    op.create_index("ix_operational_stores_operational", "operational_stores", ["is_operational"])
    op.create_index("ix_operational_stores_location_gist", "operational_stores", ["location"], postgresql_using="gist")
    op.create_table(
        "ward_census",
        sa.Column("ward_id", sa.String(3), primary_key=True),
        sa.Column("zone", sa.Integer()),
        sa.Column("residential_buildings", sa.Integer(), nullable=False),
        sa.Column("households_2011", sa.Integer(), nullable=False),
        sa.Column("population_2011", sa.Integer(), nullable=False),
        sa.Column("geometry", geoalchemy2.Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False),
        sa.Column("boundary_source_url", sa.Text(), nullable=False),
        sa.Column("census_source_url", sa.Text(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ward_census_zone", "ward_census", ["zone"])
    op.create_index("ix_ward_census_geometry_gist", "ward_census", ["geometry"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("ix_ward_census_geometry_gist", table_name="ward_census")
    op.drop_table("ward_census")
    op.drop_index("ix_operational_stores_location_gist", table_name="operational_stores")
    op.drop_table("operational_stores")
