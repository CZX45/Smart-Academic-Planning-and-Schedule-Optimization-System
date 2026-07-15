"""persist real-section optimizer input boundary evidence

Revision ID: 20260715_0019
Revises: 20260714_0018
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260715_0019"
down_revision: str | None = "20260714_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "schedule_optimization_runs",
        sa.Column(
            "section_data_mode",
            sa.String(length=20),
            nullable=False,
            server_default="DEMO_MOCK",
        ),
    )
    op.add_column(
        "schedule_optimization_runs",
        sa.Column("source_age_max_minutes", sa.Integer(), nullable=True),
    )
    op.add_column(
        "schedule_optimization_runs",
        sa.Column("input_snapshot_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "schedule_optimization_runs",
        sa.Column("source_readiness_payload", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "schedule_constraint_sets",
        sa.Column("source_age_max_minutes", sa.Integer(), nullable=True),
    )
    op.alter_column("schedule_optimization_runs", "section_data_mode", server_default=None)
    op.alter_column("schedule_optimization_runs", "source_readiness_payload", server_default=None)


def downgrade() -> None:
    op.drop_column("schedule_constraint_sets", "source_age_max_minutes")
    op.drop_column("schedule_optimization_runs", "source_readiness_payload")
    op.drop_column("schedule_optimization_runs", "input_snapshot_hash")
    op.drop_column("schedule_optimization_runs", "source_age_max_minutes")
    op.drop_column("schedule_optimization_runs", "section_data_mode")
