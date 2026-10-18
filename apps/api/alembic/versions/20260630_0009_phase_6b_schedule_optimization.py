"""add phase 6b schedule optimization scoring and repair snapshots

Revision ID: 20260630_0009
Revises: 20260629_0008
Create Date: 2026-06-30
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260630_0009"
down_revision: str | None = "20260629_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def uuid_column(name: str, *, nullable: bool = False) -> sa.Column[Any]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)


def upgrade() -> None:
    op.add_column(
        "schedule_constraint_sets",
        sa.Column("preference_weights", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "schedule_constraint_sets",
        sa.Column(
            "course_priority_weights",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column(
        "schedule_constraint_sets",
        sa.Column(
            "section_priority_weights",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column(
        "schedule_constraint_sets",
        sa.Column("prefer_no_gaps", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "schedule_constraint_sets",
        sa.Column("prefer_morning", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "schedule_constraint_sets",
        sa.Column(
            "prefer_afternoon",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "schedule_constraint_sets",
        sa.Column(
            "diversity_mode",
            sa.String(length=32),
            nullable=False,
            server_default="STANDARD",
        ),
    )
    op.add_column(
        "schedule_constraint_sets",
        sa.Column(
            "allow_partial_options",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "schedule_constraint_sets",
        sa.Column("max_combinations", sa.Integer(), nullable=False, server_default="500"),
    )

    op.add_column(
        "schedule_options",
        sa.Column("total_score", sa.Numeric(8, 2), nullable=False, server_default="0.00"),
    )
    op.add_column(
        "schedule_options",
        sa.Column("credit_score", sa.Numeric(8, 2), nullable=False, server_default="0.00"),
    )
    op.add_column(
        "schedule_options",
        sa.Column(
            "compactness_score",
            sa.Numeric(8, 2),
            nullable=False,
            server_default="0.00",
        ),
    )
    op.add_column(
        "schedule_options",
        sa.Column("days_score", sa.Numeric(8, 2), nullable=False, server_default="0.00"),
    )
    op.add_column(
        "schedule_options",
        sa.Column("gap_score", sa.Numeric(8, 2), nullable=False, server_default="0.00"),
    )
    op.add_column(
        "schedule_options",
        sa.Column("modality_score", sa.Numeric(8, 2), nullable=False, server_default="0.00"),
    )
    op.add_column(
        "schedule_options",
        sa.Column(
            "time_preference_score",
            sa.Numeric(8, 2),
            nullable=False,
            server_default="0.00",
        ),
    )
    op.add_column(
        "schedule_options",
        sa.Column("priority_score", sa.Numeric(8, 2), nullable=False, server_default="0.00"),
    )
    op.add_column(
        "schedule_options",
        sa.Column("penalty_score", sa.Numeric(8, 2), nullable=False, server_default="0.00"),
    )
    op.add_column(
        "schedule_options",
        sa.Column("score_explanation", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "schedule_options",
        sa.Column("diversity_rank", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "schedule_options",
        sa.Column(
            "difference_summary",
            sa.Text(),
            nullable=False,
            server_default="Top ranked option.",
        ),
    )
    op.add_column(
        "schedule_options",
        sa.Column(
            "shared_section_count_with_previous_option",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_check_constraint(
        "ck_schedule_options_total_score",
        "schedule_options",
        "total_score >= 0",
    )
    op.create_check_constraint(
        "ck_schedule_options_credit_score",
        "schedule_options",
        "credit_score >= 0",
    )
    op.create_check_constraint(
        "ck_schedule_options_compact_score",
        "schedule_options",
        "compactness_score >= 0",
    )
    op.create_check_constraint(
        "ck_schedule_options_days_score",
        "schedule_options",
        "days_score >= 0",
    )
    op.create_check_constraint(
        "ck_schedule_options_gap_score",
        "schedule_options",
        "gap_score >= 0",
    )
    op.create_check_constraint(
        "ck_schedule_options_modality_score",
        "schedule_options",
        "modality_score >= 0",
    )
    op.create_check_constraint(
        "ck_schedule_options_time_score",
        "schedule_options",
        "time_preference_score >= 0",
    )
    op.create_check_constraint(
        "ck_schedule_options_priority_score",
        "schedule_options",
        "priority_score >= 0",
    )
    op.create_check_constraint(
        "ck_schedule_options_penalty_score",
        "schedule_options",
        "penalty_score <= 0",
    )
    op.create_check_constraint(
        "ck_schedule_options_diversity_rank",
        "schedule_options",
        "diversity_rank > 0",
    )
    op.create_check_constraint(
        "ck_schedule_options_shared_sections",
        "schedule_options",
        "shared_section_count_with_previous_option >= 0",
    )

    op.create_table(
        "schedule_repair_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        uuid_column("schedule_optimization_run_id"),
        sa.Column("suggestion_type", sa.String(length=80), nullable=False),
        sa.Column("affected_constraint", sa.String(length=120), nullable=True),
        uuid_column("affected_course_id", nullable=True),
        uuid_column("affected_section_id", nullable=True),
        sa.Column("estimated_impact", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("requires_advisor_confirmation", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(suggestion_type) > 0",
            name="ck_schedule_repair_suggestions_type",
        ),
        sa.CheckConstraint(
            "length(estimated_impact) > 0",
            name="ck_schedule_repair_suggestions_impact",
        ),
        sa.CheckConstraint(
            "length(message) > 0",
            name="ck_schedule_repair_suggestions_message",
        ),
        sa.ForeignKeyConstraint(
            ["schedule_optimization_run_id"],
            ["schedule_optimization_runs.id"],
            name="fk_schedule_repair_suggestions_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["affected_course_id"],
            ["courses.id"],
            name="fk_schedule_repair_suggestions_course",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["affected_section_id"],
            ["sections.id"],
            name="fk_schedule_repair_suggestions_section",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_schedule_repair_suggestions_run",
        "schedule_repair_suggestions",
        ["schedule_optimization_run_id", "suggestion_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_schedule_repair_suggestions_run",
        table_name="schedule_repair_suggestions",
    )
    op.drop_table("schedule_repair_suggestions")
    op.drop_constraint(
        "ck_schedule_options_shared_sections",
        "schedule_options",
        type_="check",
    )
    op.drop_constraint("ck_schedule_options_diversity_rank", "schedule_options", type_="check")
    op.drop_constraint("ck_schedule_options_penalty_score", "schedule_options", type_="check")
    op.drop_constraint("ck_schedule_options_priority_score", "schedule_options", type_="check")
    op.drop_constraint("ck_schedule_options_time_score", "schedule_options", type_="check")
    op.drop_constraint("ck_schedule_options_modality_score", "schedule_options", type_="check")
    op.drop_constraint("ck_schedule_options_gap_score", "schedule_options", type_="check")
    op.drop_constraint("ck_schedule_options_days_score", "schedule_options", type_="check")
    op.drop_constraint("ck_schedule_options_compact_score", "schedule_options", type_="check")
    op.drop_constraint("ck_schedule_options_credit_score", "schedule_options", type_="check")
    op.drop_constraint("ck_schedule_options_total_score", "schedule_options", type_="check")
    for column_name in (
        "shared_section_count_with_previous_option",
        "difference_summary",
        "diversity_rank",
        "score_explanation",
        "penalty_score",
        "priority_score",
        "time_preference_score",
        "modality_score",
        "gap_score",
        "days_score",
        "compactness_score",
        "credit_score",
        "total_score",
    ):
        op.drop_column("schedule_options", column_name)
    for column_name in (
        "max_combinations",
        "allow_partial_options",
        "diversity_mode",
        "prefer_afternoon",
        "prefer_morning",
        "prefer_no_gaps",
        "section_priority_weights",
        "course_priority_weights",
        "preference_weights",
    ):
        op.drop_column("schedule_constraint_sets", column_name)
