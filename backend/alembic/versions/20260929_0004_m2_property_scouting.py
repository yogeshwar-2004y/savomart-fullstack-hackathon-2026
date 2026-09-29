"""M2 property scouting, evaluation, and pipeline.

Revision ID: 20260929_0004
Revises: 20260928_0003
"""

from collections.abc import Sequence

from alembic import op
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260929_0004"
down_revision: str | None = "20260928_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scout_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("area_report_id", sa.Uuid(), sa.ForeignKey("area_reports.id"), nullable=False),
        sa.Column("suggestion_id", sa.Uuid(), sa.ForeignKey("scouting_suggestions.id")),
        sa.Column("target_label", sa.String(160), nullable=False),
        sa.Column("target_geometry", geoalchemy2.Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("assignee_id", sa.String(64), nullable=False),
        sa.Column("assignee_name", sa.String(120), nullable=False),
        sa.Column("created_by_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), server_default="assigned", nullable=False),
        sa.Column("instructions", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scout_assignments_area_report_id", "scout_assignments", ["area_report_id"])
    op.create_index("ix_scout_assignments_suggestion_id", "scout_assignments", ["suggestion_id"])
    op.create_index("ix_scout_assignments_assignee_id", "scout_assignments", ["assignee_id"])
    op.create_index("ix_scout_assignments_target_gist", "scout_assignments", ["target_geometry"], postgresql_using="gist")

    op.create_table(
        "properties",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("assignment_id", sa.Uuid(), sa.ForeignKey("scout_assignments.id"), nullable=False),
        sa.Column("captured_by_id", sa.String(64), nullable=False),
        sa.Column("location", geoalchemy2.Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("address", sa.String(240), nullable=False),
        sa.Column("rent_monthly", sa.Float(), nullable=False),
        sa.Column("size_sq_ft", sa.Float(), nullable=False),
        sa.Column("frontage_ft", sa.Float()),
        sa.Column("road_width_ft", sa.Float()),
        sa.Column("property_type", sa.String(40), nullable=False),
        sa.Column("floor_level", sa.String(40), nullable=False),
        sa.Column("visibility_rating", sa.Integer(), nullable=False),
        sa.Column("condition_rating", sa.Integer(), nullable=False),
        sa.Column("parking_available", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("power_backup", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("water_available", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("stage", sa.String(32), server_default="scouted", nullable=False),
        sa.Column("duplicate_review", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("suspicious_gps", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("review_flags", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_properties_assignment_id", "properties", ["assignment_id"])
    op.create_index("ix_properties_captured_by_id", "properties", ["captured_by_id"])
    op.create_index("ix_properties_stage", "properties", ["stage"])
    op.create_index("ix_properties_location_gist", "properties", ["location"], postgresql_using="gist")

    op.create_table(
        "property_photos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("property_id", sa.Uuid(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storage_key", sa.String(240), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(240), nullable=False),
        sa.Column("content_type", sa.String(40), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_property_photos_property_id", "property_photos", ["property_id"])

    op.create_table(
        "property_evaluations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("property_id", sa.Uuid(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("scoring_version", sa.String(48), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rating", sa.String(40), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("insights", postgresql.JSONB(), nullable=False),
        sa.Column("risks", postgresql.JSONB(), nullable=False),
        sa.Column("limitations", postgresql.JSONB(), nullable=False),
        sa.Column("source_snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("property_id", "version", name="uq_property_evaluation_version"),
    )
    op.create_index("ix_property_evaluations_property_id", "property_evaluations", ["property_id"])

    op.create_table(
        "property_stage_transitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("property_id", sa.Uuid(), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_stage", sa.String(32)),
        sa.Column("to_stage", sa.String(32), nullable=False),
        sa.Column("actor_id", sa.String(64), nullable=False),
        sa.Column("actor_name", sa.String(120), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_property_stage_transitions_property_id", "property_stage_transitions", ["property_id"])


def downgrade() -> None:
    op.drop_table("property_stage_transitions")
    op.drop_table("property_evaluations")
    op.drop_table("property_photos")
    op.drop_index("ix_properties_location_gist", table_name="properties")
    op.drop_table("properties")
    op.drop_index("ix_scout_assignments_target_gist", table_name="scout_assignments")
    op.drop_table("scout_assignments")
