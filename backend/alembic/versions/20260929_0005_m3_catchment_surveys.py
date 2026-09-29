"""M3 catchment studies, zones, and lane observations.

Revision ID: 20260929_0005
Revises: 20260929_0004
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260929_0005"
down_revision: str | None = "20260929_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "catchment_studies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("property_id", sa.Uuid(), sa.ForeignKey("properties.id")),
        sa.Column("area_report_id", sa.Uuid(), sa.ForeignKey("area_reports.id")),
        sa.Column("target_type", sa.String(24), nullable=False),
        sa.Column("target_label", sa.String(200), nullable=False),
        sa.Column(
            "target_geometry",
            geoalchemy2.Geometry("MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column(
            "survey_geometry",
            geoalchemy2.Geometry("MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("status", sa.String(24), server_default="requested", nullable=False),
        sa.Column("requested_by_id", sa.String(64), nullable=False),
        sa.Column("requested_by_name", sa.String(120), nullable=False),
        sa.Column("source_study_id", sa.Uuid(), sa.ForeignKey("catchment_studies.id")),
        sa.Column("reuse_coverage", sa.Float(), server_default="0", nullable=False),
        sa.Column("reuse_age_days", sa.Float()),
        sa.Column("reuse_max_age_days", sa.Integer(), nullable=False),
        sa.Column("reuse_min_coverage", sa.Float(), nullable=False),
        sa.Column("summary", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "(property_id IS NOT NULL) <> (area_report_id IS NOT NULL)",
            name="ck_catchment_single_target",
        ),
    )
    op.create_index("ix_catchment_studies_property_id", "catchment_studies", ["property_id"])
    op.create_index("ix_catchment_studies_area_report_id", "catchment_studies", ["area_report_id"])
    op.create_index("ix_catchment_studies_status", "catchment_studies", ["status"])
    op.create_index(
        "ix_catchment_studies_target_gist",
        "catchment_studies",
        ["target_geometry"],
        postgresql_using="gist",
    )
    op.create_index(
        "ix_catchment_studies_survey_gist",
        "catchment_studies",
        ["survey_geometry"],
        postgresql_using="gist",
    )

    op.create_table(
        "survey_zones",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "study_id", sa.Uuid(), sa.ForeignKey("catchment_studies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column(
            "geometry",
            geoalchemy2.Geometry("MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("assignee_id", sa.String(64), nullable=False),
        sa.Column("assignee_name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(24), server_default="assigned", nullable=False),
        sa.Column("mismatch_review", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_survey_zones_study_id", "survey_zones", ["study_id"])
    op.create_index("ix_survey_zones_assignee_id", "survey_zones", ["assignee_id"])
    op.create_index("ix_survey_zones_status", "survey_zones", ["status"])
    op.create_index("ix_survey_zones_geometry_gist", "survey_zones", ["geometry"], postgresql_using="gist")

    op.create_table(
        "lane_captures",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("zone_id", sa.Uuid(), sa.ForeignKey("survey_zones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("study_id", sa.Uuid(), sa.ForeignKey("catchment_studies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_submission_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("submitted_by_id", sa.String(64), nullable=False),
        sa.Column("submitted_by_name", sa.String(120), nullable=False),
        sa.Column("lane_name", sa.String(160), nullable=False),
        sa.Column("location", geoalchemy2.Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("gps_accuracy_m", sa.Float(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("residential_units", sa.Integer(), nullable=False),
        sa.Column("commercial_units", sa.Integer(), nullable=False),
        sa.Column("pedestrian_activity", sa.Integer(), nullable=False),
        sa.Column("vehicle_activity", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.String(24), server_default="submitted", nullable=False),
        sa.Column("location_mismatch", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("mismatch_distance_m", sa.Float(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_lane_captures_zone_id", "lane_captures", ["zone_id"])
    op.create_index("ix_lane_captures_study_id", "lane_captures", ["study_id"])
    op.create_index("ix_lane_captures_client_submission_id", "lane_captures", ["client_submission_id"])
    op.create_index("ix_lane_captures_submitted_by_id", "lane_captures", ["submitted_by_id"])
    op.create_index("ix_lane_captures_location_gist", "lane_captures", ["location"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("ix_lane_captures_location_gist", table_name="lane_captures")
    op.drop_table("lane_captures")
    op.drop_index("ix_survey_zones_geometry_gist", table_name="survey_zones")
    op.drop_table("survey_zones")
    op.drop_index("ix_catchment_studies_survey_gist", table_name="catchment_studies")
    op.drop_index("ix_catchment_studies_target_gist", table_name="catchment_studies")
    op.drop_table("catchment_studies")
