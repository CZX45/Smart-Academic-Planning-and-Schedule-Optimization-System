"""create semester schedule optimizer snapshot tables

Revision ID: 20260629_0008
Revises: 20260629_0007
Create Date: 2026-06-29
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260629_0008"
down_revision: str | None = "20260629_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEDULE_PLANNING_MODES = (
    "FROM_DEGREE_AUDIT",
    "FROM_LONG_TERM_PLAN",
    "CUSTOM_COURSE_SET",
)
SCHEDULE_RUN_STATUSES = (
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "COMPLETED_WITH_WARNINGS",
    "FAILED",
)
SCHEDULE_OPTION_STATUSES = (
    "FEASIBLE",
    "FEASIBLE_WITH_WARNINGS",
    "PARTIAL",
    "INFEASIBLE",
)
SCHEDULE_CONFLICT_TYPES = (
    "TIME_OVERLAP",
    "UNAVAILABLE_TIME",
    "EXCLUDED_DAY",
    "CREDIT_LIMIT",
    "DUPLICATE_COURSE",
    "ELIGIBILITY_BLOCKED",
    "COREQUISITE_MISSING",
    "NO_SECTION_AVAILABLE",
    "MANUAL_REVIEW_REQUIRED",
)
DAY_OF_WEEK_VALUES = (
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
    "SUNDAY",
)
ELIGIBILITY_OVERALL_RESULTS = (
    "ELIGIBLE",
    "CONDITIONALLY_ELIGIBLE",
    "NOT_ELIGIBLE",
    "PERMISSION_REQUIRED",
    "MANUAL_REVIEW_REQUIRED",
)
AUDIT_WARNING_SEVERITIES = ("INFO", "WARNING", "ERROR")


def enum(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
    )


def uuid_column(name: str, *, nullable: bool = False, primary_key: bool = False) -> sa.Column[Any]:
    return sa.Column(
        name,
        postgresql.UUID(as_uuid=True),
        nullable=nullable,
        primary_key=primary_key,
    )


def created_at_column() -> sa.Column[Any]:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def timestamp_columns() -> list[sa.Column[Any]]:
    return [
        created_at_column(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "schedule_optimization_runs",
        uuid_column("id"),
        uuid_column("student_profile_id"),
        uuid_column("term_id"),
        uuid_column("academic_plan_run_id", nullable=True),
        sa.Column(
            "planning_mode",
            enum(SCHEDULE_PLANNING_MODES, "schedule_planning_mode"),
            nullable=False,
        ),
        sa.Column(
            "status",
            enum(SCHEDULE_RUN_STATUSES, "schedule_run_status"),
            nullable=False,
        ),
        sa.Column("engine_version", sa.String(length=80), nullable=False),
        sa.Column("minimum_credits", sa.Numeric(5, 1), nullable=False),
        sa.Column("maximum_credits", sa.Numeric(5, 1), nullable=False),
        sa.Column("preferred_credits", sa.Numeric(5, 1), nullable=False),
        sa.Column("requested_option_count", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("length(engine_version) > 0", name="ck_schedule_runs_engine"),
        sa.CheckConstraint("minimum_credits >= 0", name="ck_schedule_runs_min_credits"),
        sa.CheckConstraint("maximum_credits >= 0", name="ck_schedule_runs_max_credits"),
        sa.CheckConstraint("preferred_credits >= 0", name="ck_schedule_runs_pref_credits"),
        sa.CheckConstraint(
            "maximum_credits >= minimum_credits",
            name="ck_schedule_runs_max_ge_min",
        ),
        sa.CheckConstraint(
            "preferred_credits <= maximum_credits",
            name="ck_schedule_runs_pref_under_max",
        ),
        sa.CheckConstraint(
            "requested_option_count > 0 AND requested_option_count <= 20",
            name="ck_schedule_runs_option_count",
        ),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_schedule_runs_student",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["academic_terms.id"],
            name="fk_schedule_runs_term",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["academic_plan_run_id"],
            ["academic_plan_runs.id"],
            name="fk_schedule_runs_academic_plan",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_schedule_runs_student_created",
        "schedule_optimization_runs",
        ["student_profile_id", "created_at"],
    )
    op.create_index(
        "ix_schedule_runs_term_status",
        "schedule_optimization_runs",
        ["term_id", "status"],
    )

    op.create_table(
        "schedule_constraint_sets",
        uuid_column("id"),
        uuid_column("schedule_optimization_run_id"),
        sa.Column("excluded_days", sa.JSON(), nullable=False),
        sa.Column("unavailable_time_blocks", sa.JSON(), nullable=False),
        sa.Column("earliest_start_time", sa.Time(), nullable=True),
        sa.Column("latest_end_time", sa.Time(), nullable=True),
        sa.Column("minimum_gap_minutes", sa.Integer(), nullable=True),
        sa.Column("maximum_gap_minutes", sa.Integer(), nullable=True),
        sa.Column("candidate_course_ids", sa.JSON(), nullable=False),
        sa.Column("allowed_modalities", sa.JSON(), nullable=False),
        sa.Column("excluded_modalities", sa.JSON(), nullable=False),
        sa.Column("required_course_ids", sa.JSON(), nullable=False),
        sa.Column("excluded_course_ids", sa.JSON(), nullable=False),
        sa.Column("required_section_ids", sa.JSON(), nullable=False),
        sa.Column("excluded_section_ids", sa.JSON(), nullable=False),
        sa.Column("prefer_online", sa.Boolean(), nullable=False),
        sa.Column("prefer_compact_schedule", sa.Boolean(), nullable=False),
        sa.Column("prefer_fewer_days", sa.Boolean(), nullable=False),
        sa.Column("prefer_in_person", sa.Boolean(), nullable=False),
        sa.Column("avoid_early_start", sa.Boolean(), nullable=False),
        sa.Column("avoid_late_end", sa.Boolean(), nullable=False),
        sa.Column("allow_permission_required", sa.Boolean(), nullable=False),
        created_at_column(),
        sa.CheckConstraint(
            "earliest_start_time IS NULL OR latest_end_time IS NULL "
            "OR earliest_start_time < latest_end_time",
            name="ck_schedule_constraints_time_window",
        ),
        sa.CheckConstraint(
            "minimum_gap_minutes IS NULL OR minimum_gap_minutes >= 0",
            name="ck_schedule_constraints_min_gap",
        ),
        sa.CheckConstraint(
            "maximum_gap_minutes IS NULL OR maximum_gap_minutes >= 0",
            name="ck_schedule_constraints_max_gap",
        ),
        sa.CheckConstraint(
            "minimum_gap_minutes IS NULL OR maximum_gap_minutes IS NULL "
            "OR maximum_gap_minutes >= minimum_gap_minutes",
            name="ck_schedule_constraints_gap_order",
        ),
        sa.ForeignKeyConstraint(
            ["schedule_optimization_run_id"],
            ["schedule_optimization_runs.id"],
            name="fk_schedule_constraints_run",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "schedule_optimization_run_id",
            name="uq_schedule_constraints_run",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "schedule_options",
        uuid_column("id"),
        uuid_column("schedule_optimization_run_id"),
        sa.Column("option_rank", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            enum(SCHEDULE_OPTION_STATUSES, "schedule_option_status"),
            nullable=False,
        ),
        sa.Column("total_credits", sa.Numeric(5, 1), nullable=False),
        sa.Column("class_days_count", sa.Integer(), nullable=False),
        sa.Column("earliest_start_time", sa.Time(), nullable=True),
        sa.Column("latest_end_time", sa.Time(), nullable=True),
        sa.Column("total_gap_minutes", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(8, 2), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        created_at_column(),
        sa.CheckConstraint("option_rank > 0", name="ck_schedule_options_rank_positive"),
        sa.CheckConstraint("total_credits >= 0", name="ck_schedule_options_credits"),
        sa.CheckConstraint("class_days_count >= 0", name="ck_schedule_options_days"),
        sa.CheckConstraint("total_gap_minutes >= 0", name="ck_schedule_options_gap"),
        sa.CheckConstraint("length(explanation) > 0", name="ck_schedule_options_explained"),
        sa.ForeignKeyConstraint(
            ["schedule_optimization_run_id"],
            ["schedule_optimization_runs.id"],
            name="fk_schedule_options_run",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "schedule_optimization_run_id",
            "option_rank",
            name="uq_schedule_options_run_rank",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_schedule_options_run_rank",
        "schedule_options",
        ["schedule_optimization_run_id", "option_rank"],
    )

    op.create_table(
        "schedule_option_sections",
        uuid_column("id"),
        uuid_column("schedule_option_id"),
        uuid_column("section_id"),
        uuid_column("course_id"),
        sa.Column("credits", sa.Numeric(5, 1), nullable=False),
        sa.Column(
            "eligibility_result",
            enum(ELIGIBILITY_OVERALL_RESULTS, "eligibility_overall_result"),
            nullable=False,
        ),
        sa.Column("selection_reason", sa.String(length=120), nullable=False),
        created_at_column(),
        sa.CheckConstraint("credits >= 0", name="ck_schedule_option_sections_credits"),
        sa.CheckConstraint(
            "length(selection_reason) > 0",
            name="ck_schedule_option_sections_reason",
        ),
        sa.ForeignKeyConstraint(
            ["schedule_option_id"],
            ["schedule_options.id"],
            name="fk_schedule_option_sections_option",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
            name="fk_schedule_option_sections_section",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_schedule_option_sections_course",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "schedule_option_id",
            "course_id",
            name="uq_schedule_option_sections_course",
        ),
        sa.UniqueConstraint(
            "schedule_option_id",
            "section_id",
            name="uq_schedule_option_sections_section",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_schedule_option_sections_option",
        "schedule_option_sections",
        ["schedule_option_id", "course_id"],
    )

    op.create_table(
        "schedule_conflicts",
        uuid_column("id"),
        uuid_column("schedule_optimization_run_id"),
        uuid_column("schedule_option_id", nullable=True),
        sa.Column(
            "conflict_type",
            enum(SCHEDULE_CONFLICT_TYPES, "schedule_conflict_type"),
            nullable=False,
        ),
        uuid_column("section_id", nullable=True),
        uuid_column("other_section_id", nullable=True),
        sa.Column("day_of_week", enum(DAY_OF_WEEK_VALUES, "day_of_week"), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        created_at_column(),
        sa.CheckConstraint("length(message) > 0", name="ck_schedule_conflicts_message"),
        sa.ForeignKeyConstraint(
            ["schedule_optimization_run_id"],
            ["schedule_optimization_runs.id"],
            name="fk_schedule_conflicts_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["schedule_option_id"],
            ["schedule_options.id"],
            name="fk_schedule_conflicts_option",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
            name="fk_schedule_conflicts_section",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["other_section_id"],
            ["sections.id"],
            name="fk_schedule_conflicts_other_section",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_schedule_conflicts_run_type",
        "schedule_conflicts",
        ["schedule_optimization_run_id", "conflict_type"],
    )

    op.create_table(
        "schedule_warnings",
        uuid_column("id"),
        uuid_column("schedule_optimization_run_id"),
        uuid_column("schedule_option_id", nullable=True),
        sa.Column("warning_code", sa.String(length=80), nullable=False),
        sa.Column(
            "severity",
            enum(AUDIT_WARNING_SEVERITIES, "audit_warning_severity"),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("requires_advisor_confirmation", sa.Boolean(), nullable=False),
        created_at_column(),
        sa.CheckConstraint("length(warning_code) > 0", name="ck_schedule_warnings_code"),
        sa.CheckConstraint("length(message) > 0", name="ck_schedule_warnings_message"),
        sa.ForeignKeyConstraint(
            ["schedule_optimization_run_id"],
            ["schedule_optimization_runs.id"],
            name="fk_schedule_warnings_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["schedule_option_id"],
            ["schedule_options.id"],
            name="fk_schedule_warnings_option",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_schedule_warnings_run_severity",
        "schedule_warnings",
        ["schedule_optimization_run_id", "severity"],
    )


def downgrade() -> None:
    op.drop_index("ix_schedule_warnings_run_severity", table_name="schedule_warnings")
    op.drop_table("schedule_warnings")
    op.drop_index("ix_schedule_conflicts_run_type", table_name="schedule_conflicts")
    op.drop_table("schedule_conflicts")
    op.drop_index("ix_schedule_option_sections_option", table_name="schedule_option_sections")
    op.drop_table("schedule_option_sections")
    op.drop_index("ix_schedule_options_run_rank", table_name="schedule_options")
    op.drop_table("schedule_options")
    op.drop_table("schedule_constraint_sets")
    op.drop_index("ix_schedule_runs_term_status", table_name="schedule_optimization_runs")
    op.drop_index("ix_schedule_runs_student_created", table_name="schedule_optimization_runs")
    op.drop_table("schedule_optimization_runs")
