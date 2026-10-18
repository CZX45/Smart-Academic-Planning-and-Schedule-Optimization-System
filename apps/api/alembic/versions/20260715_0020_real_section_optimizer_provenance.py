"""persist selected Section provenance and drift snapshots

Revision ID: 20260715_0020
Revises: 20260715_0019
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260715_0020"
down_revision: str | None = "20260715_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "schedule_option_sections",
        sa.Column("source_provenance", sa.JSON(), nullable=True),
    )
    op.add_column(
        "schedule_option_sections",
        sa.Column("section_snapshot_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "schedule_option_sections",
        sa.Column("source_age_minutes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("schedule_option_sections", "source_age_minutes")
    op.drop_column("schedule_option_sections", "section_snapshot_hash")
    op.drop_column("schedule_option_sections", "source_provenance")
