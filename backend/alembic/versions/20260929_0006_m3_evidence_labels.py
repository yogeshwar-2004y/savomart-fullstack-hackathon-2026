"""Label real and demo M3 lane evidence.

Revision ID: 20260929_0006
Revises: 20260929_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260929_0006"
down_revision: str | None = "20260929_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "lane_captures",
        sa.Column("evidence_kind", sa.String(24), server_default="field-survey", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("lane_captures", "evidence_kind")
