"""Track all prior studies contributing to catchment reuse.

Revision ID: 20260929_0007
Revises: 20260929_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260929_0007"
down_revision: str | None = "20260929_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "catchment_studies",
        sa.Column(
            "source_study_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.execute(
        "UPDATE catchment_studies SET source_study_ids = jsonb_build_array(source_study_id::text) "
        "WHERE source_study_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("catchment_studies", "source_study_ids")
