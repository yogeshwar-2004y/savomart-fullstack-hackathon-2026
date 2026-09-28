"""Persist truthful area geography provenance.

Revision ID: 20260928_0003
Revises: 20260928_0002
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260928_0003"
down_revision: str | None = "20260928_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("areas", sa.Column("source", sa.String(160), server_default="Legacy area selection", nullable=False))
    op.add_column("areas", sa.Column("source_id", sa.String(220), server_default="legacy:unknown", nullable=False))
    op.add_column("areas", sa.Column("source_url", sa.Text()))
    op.add_column("areas", sa.Column("source_license", sa.String(120)))
    op.add_column("areas", sa.Column("boundary_type", sa.String(32), server_default="user-selected", nullable=False))
    op.add_column("areas", sa.Column("boundary_lookup_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("areas", sa.Column("is_official", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("areas", sa.Column("is_approximate", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("areas", sa.Column("approximation_warning", sa.Text()))
    op.add_column("areas", sa.Column("resolver_cache_age_seconds", sa.Integer()))


def downgrade() -> None:
    for column in (
        "resolver_cache_age_seconds", "approximation_warning", "is_approximate", "is_official",
        "boundary_lookup_at", "boundary_type", "source_license", "source_url", "source_id", "source",
    ):
        op.drop_column("areas", column)
