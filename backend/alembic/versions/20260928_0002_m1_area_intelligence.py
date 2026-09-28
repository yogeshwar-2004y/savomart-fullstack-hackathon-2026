"""M1 area intelligence tables and spatial indexes

Revision ID: 20260928_0002
Revises: 20260928_0001
Create Date: 2026-09-28
"""

from collections.abc import Sequence

from alembic import op
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260928_0002"
down_revision: str | None = "20260928_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "areas",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("query", sa.String(160)),
        sa.Column("selection_method", sa.String(24), nullable=False),
        sa.Column("geometry", geoalchemy2.Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False),
        sa.Column("area_sq_km", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_areas_geometry_gist", "areas", ["geometry"], postgresql_using="gist")
    op.create_table(
        "area_analyses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("area_id", sa.Uuid(), sa.ForeignKey("areas.id"), nullable=False),
        sa.Column("requested_by_role", sa.String(32), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("scoring_version", sa.String(40), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_area_analyses_area_id", "area_analyses", ["area_id"])
    op.add_column("analysis_jobs", sa.Column("analysis_id", sa.Uuid(), sa.ForeignKey("area_analyses.id")))
    op.add_column("analysis_jobs", sa.Column("report_id", sa.Uuid()))
    op.add_column("analysis_jobs", sa.Column("attempts", sa.Integer(), server_default="1", nullable=False))
    op.add_column("analysis_jobs", sa.Column("error_code", sa.String(80)))
    op.add_column("analysis_jobs", sa.Column("retryable", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.create_index("ix_analysis_jobs_analysis_id", "analysis_jobs", ["analysis_id"])
    op.create_table(
        "area_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("analysis_id", sa.Uuid(), sa.ForeignKey("area_analyses.id"), nullable=False, unique=True),
        sa.Column("area_id", sa.Uuid(), sa.ForeignKey("areas.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rating", sa.String(40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("scoring_version", sa.String(40), nullable=False),
        sa.Column("source_snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_cached_evidence", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("cache_age_seconds", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_area_reports_area_id", "area_reports", ["area_id"])
    op.create_foreign_key("fk_analysis_jobs_report_id", "analysis_jobs", "area_reports", ["report_id"], ["id"])
    op.create_table(
        "area_metric_evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("report_id", sa.Uuid(), sa.ForeignKey("area_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("raw_value", sa.Float()),
        sa.Column("raw_unit", sa.String(40), nullable=False),
        sa.Column("normalized_value", sa.Float(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("contribution", sa.Float(), nullable=False),
        sa.Column("source_name", sa.String(120), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("geography", sa.Text(), nullable=False),
        sa.Column("transformation", sa.Text(), nullable=False),
        sa.Column("limitations", sa.Text(), nullable=False),
        sa.Column("evidence_kind", sa.String(24), nullable=False),
        sa.Column("cache_age_seconds", sa.Integer()),
    )
    op.create_index("ix_area_metric_evidence_report_id", "area_metric_evidence", ["report_id"])
    op.create_table(
        "scouting_suggestions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("report_id", sa.Uuid(), sa.ForeignKey("area_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("point", geoalchemy2.Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_scouting_suggestions_report_id", "scouting_suggestions", ["report_id"])
    op.create_index("ix_scouting_suggestions_point_gist", "scouting_suggestions", ["point"], postgresql_using="gist")
    op.create_table(
        "external_data_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("cache_key", sa.String(220), nullable=False),
        sa.Column("source_name", sa.String(120), nullable=False),
        sa.Column("geography", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_external_data_snapshots_cache_key", "external_data_snapshots", ["cache_key"])


def downgrade() -> None:
    op.drop_table("external_data_snapshots")
    op.drop_index("ix_scouting_suggestions_point_gist", table_name="scouting_suggestions")
    op.drop_table("scouting_suggestions")
    op.drop_table("area_metric_evidence")
    op.drop_constraint("fk_analysis_jobs_report_id", "analysis_jobs", type_="foreignkey")
    op.drop_table("area_reports")
    op.drop_index("ix_analysis_jobs_analysis_id", table_name="analysis_jobs")
    for column in ("retryable", "error_code", "attempts", "report_id", "analysis_id"):
        op.drop_column("analysis_jobs", column)
    op.drop_table("area_analyses")
    op.drop_index("ix_areas_geometry_gist", table_name="areas")
    op.drop_table("areas")
