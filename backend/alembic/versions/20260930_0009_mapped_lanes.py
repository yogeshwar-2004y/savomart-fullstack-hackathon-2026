"""Persist reviewed mapped-lane suggestions and zone links."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260930_0009"
down_revision = "20260929_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("catchment_studies", sa.Column("lane_suggestions", JSONB(), nullable=True))
    op.add_column("catchment_studies", sa.Column("lane_suggestions_fetched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("catchment_studies", sa.Column("lane_suggestions_error", sa.Text(), nullable=True))
    op.add_column("survey_zones", sa.Column("suggested_lane_ids", JSONB(), nullable=False, server_default="[]"))
    op.add_column("lane_captures", sa.Column("suggested_lane_id", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("lane_captures", "suggested_lane_id")
    op.drop_column("survey_zones", "suggested_lane_ids")
    op.drop_column("catchment_studies", "lane_suggestions_error")
    op.drop_column("catchment_studies", "lane_suggestions_fetched_at")
    op.drop_column("catchment_studies", "lane_suggestions")
