"""create academic planner snapshot tables

Revision ID: 20260629_0007
Revises: 20260624_0006
Create Date: 2026-06-29
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260629_0007"
down_revision: str | None = "20260624_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACADEMIC_PLANNING_MODES = ("CURRENT_PROGRAM", "WHAT_IF_SCENARIO")
ACADEMIC_PLAN_RUN_STATUSES = (
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "COMPLETED_WITH_WARNINGS",
    "FAILED",
)
ACADEMIC_PLAN_TERM_STATUSES = (
    "PLANNED",
    "PARTIAL",
    "BLOCKED",
    "MANUAL_REVIEW_REQUIRED",
)
ACADEMIC_PLAN_COURSE_SOURCES = (
    "DEGREE_AUDIT_REMAINING",
    "WHAT_IF_REMAINING",
    "PREREQUISITE_UNLOCK",
    "COREQUISITE_PAIR",
    "MANUAL_PLACEHOLDER",
)
ACADEMIC_PLAN_COURSE_STATUSES = (
    "PLANNED",
    "CONDITIONALLY_PLANNED",
    "BLOCKED",
    "ALTERNATIVE",
    "MANUAL_REVIEW_REQUIRED",
)
ACADEMIC_PLAN_COVERAGE_TYPES = (
    "DIRECT_REQUIREMENT",
    "ELECTIVE_POOL",
    "TOTAL_CREDITS",
    "PREREQUISITE_ONLY",
    "WHAT_IF_REQUIREMENT",
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


def timestamp_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "academic_plan_runs",
        uuid_column("id"),
        uuid_column("student_profile_id"),
        uuid_column("program_version_id"),
        uuid_column("academic_plan_scenario_id", nullable=True),
        sa.Column(
            "planning_mode",
            enum(ACADEMIC_PLANNING_MODES, "academic_planning_mode"),
            nullable=False,
        ),
        sa.Column(
            "status",
            enum(ACADEMIC_PLAN_RUN_STATUSES, "academic_plan_run_status"),
            nullable=False,
        ),
        sa.Column("engine_version", sa.String(length=80), nullable=False),
        uuid_column("start_term_id"),
        uuid_column("target_completion_term_id"),
        sa.Column("minimum_credits_per_term", sa.Numeric(5, 1), nullable=False),
        sa.Column("maximum_credits_per_term", sa.Numeric(5, 1), nullable=False),
        sa.Column("preferred_credits_per_term", sa.Numeric(5, 1), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("length(engine_version) > 0", name="ck_academic_plan_runs_engine"),
        sa.CheckConstraint(
            "minimum_credits_per_term >= 0",
            name="ck_academic_plan_runs_min_credits",
        ),
        sa.CheckConstraint(
            "maximum_credits_per_term >= 0",
            name="ck_academic_plan_runs_max_credits",
        ),
        sa.CheckConstraint(
            "preferred_credits_per_term >= 0",
            name="ck_academic_plan_runs_pref_credits",
        ),
        sa.CheckConstraint(
            "preferred_credits_per_term <= maximum_credits_per_term",
            name="ck_academic_plan_runs_pref_under_max",
        ),
        sa.CheckConstraint(
            "planning_mode != 'WHAT_IF_SCENARIO' OR academic_plan_scenario_id IS NOT NULL",
            name="ck_academic_plan_runs_what_if_has_scenario",
        ),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_academic_plan_runs_student",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["program_version_id"],
            ["program_versions.id"],
            name="fk_academic_plan_runs_program",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["academic_plan_scenario_id"],
            ["academic_plan_scenarios.id"],
            name="fk_academic_plan_runs_scenario",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["start_term_id"],
            ["academic_terms.id"],
            name="fk_academic_plan_runs_start_term",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_completion_term_id"],
            ["academic_terms.id"],
            name="fk_academic_plan_runs_target_term",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_academic_plan_runs_student_created",
        "academic_plan_runs",
        ["student_profile_id", "created_at"],
    )
    op.create_index(
        "ix_academic_plan_runs_scenario",
        "academic_plan_runs",
        ["academic_plan_scenario_id"],
    )

    op.create_table(
        "academic_plan_terms",
        uuid_column("id"),
        uuid_column("academic_plan_run_id"),
        uuid_column("term_id"),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column("planned_credits", sa.Numeric(5, 1), nullable=False),
        sa.Column(
            "status",
            enum(ACADEMIC_PLAN_TERM_STATUSES, "academic_plan_term_status"),
            nullable=False,
        ),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("sequence_index >= 0", name="ck_academic_plan_terms_sequence"),
        sa.CheckConstraint("planned_credits >= 0", name="ck_academic_plan_terms_credits"),
        sa.CheckConstraint("length(explanation) > 0", name="ck_academic_plan_terms_explained"),
        sa.ForeignKeyConstraint(
            ["academic_plan_run_id"],
            ["academic_plan_runs.id"],
            name="fk_academic_plan_terms_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["academic_terms.id"],
            name="fk_academic_plan_terms_term",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "academic_plan_run_id",
            "term_id",
            name="uq_academic_plan_terms_run_term",
        ),
        sa.UniqueConstraint(
            "academic_plan_run_id",
            "sequence_index",
            name="uq_academic_plan_terms_run_sequence",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_academic_plan_terms_run_sequence",
        "academic_plan_terms",
        ["academic_plan_run_id", "sequence_index"],
    )

    op.create_table(
        "academic_plan_courses",
        uuid_column("id"),
        uuid_column("academic_plan_term_id"),
        uuid_column("course_id"),
        uuid_column("requirement_node_id", nullable=True),
        sa.Column(
            "source",
            enum(ACADEMIC_PLAN_COURSE_SOURCES, "academic_plan_course_source"),
            nullable=False,
        ),
        sa.Column("priority_rank", sa.Integer(), nullable=False),
        sa.Column("credits", sa.Numeric(5, 1), nullable=False),
        sa.Column(
            "eligibility_result",
            enum(ELIGIBILITY_OVERALL_RESULTS, "eligibility_overall_result"),
            nullable=False,
        ),
        sa.Column(
            "planning_status",
            enum(ACADEMIC_PLAN_COURSE_STATUSES, "academic_plan_course_status"),
            nullable=False,
        ),
        sa.Column("reason_code", sa.String(length=80), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("priority_rank >= 0", name="ck_academic_plan_courses_priority"),
        sa.CheckConstraint("credits >= 0", name="ck_academic_plan_courses_credits"),
        sa.CheckConstraint("length(reason_code) > 0", name="ck_academic_plan_courses_reason"),
        sa.CheckConstraint(
            "length(explanation) > 0",
            name="ck_academic_plan_courses_explained",
        ),
        sa.ForeignKeyConstraint(
            ["academic_plan_term_id"],
            ["academic_plan_terms.id"],
            name="fk_academic_plan_courses_term",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_academic_plan_courses_course",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_node_id"],
            ["requirement_nodes.id"],
            name="fk_academic_plan_courses_requirement",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "academic_plan_term_id",
            "course_id",
            name="uq_academic_plan_courses_term_course",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_academic_plan_courses_term_rank",
        "academic_plan_courses",
        ["academic_plan_term_id", "priority_rank"],
    )

    op.create_table(
        "academic_plan_requirement_coverages",
        uuid_column("id"),
        uuid_column("academic_plan_run_id"),
        uuid_column("academic_plan_course_id"),
        uuid_column("requirement_node_id"),
        sa.Column(
            "coverage_type",
            enum(ACADEMIC_PLAN_COVERAGE_TYPES, "academic_plan_coverage_type"),
            nullable=False,
        ),
        sa.Column("credits", sa.Numeric(5, 1), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("credits >= 0", name="ck_academic_plan_cov_credits"),
        sa.ForeignKeyConstraint(
            ["academic_plan_run_id"],
            ["academic_plan_runs.id"],
            name="fk_academic_plan_cov_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["academic_plan_course_id"],
            ["academic_plan_courses.id"],
            name="fk_academic_plan_cov_course",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_node_id"],
            ["requirement_nodes.id"],
            name="fk_academic_plan_cov_requirement",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "academic_plan_course_id",
            "requirement_node_id",
            "coverage_type",
            name="uq_academic_plan_cov_course_req_type",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_academic_plan_cov_run",
        "academic_plan_requirement_coverages",
        ["academic_plan_run_id"],
    )

    op.create_table(
        "academic_plan_warnings",
        uuid_column("id"),
        uuid_column("academic_plan_run_id"),
        uuid_column("academic_plan_term_id", nullable=True),
        uuid_column("academic_plan_course_id", nullable=True),
        sa.Column("warning_code", sa.String(length=80), nullable=False),
        sa.Column(
            "severity",
            enum(AUDIT_WARNING_SEVERITIES, "audit_warning_severity"),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("requires_advisor_confirmation", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("length(warning_code) > 0", name="ck_academic_plan_warnings_code"),
        sa.CheckConstraint("length(message) > 0", name="ck_academic_plan_warnings_message"),
        sa.ForeignKeyConstraint(
            ["academic_plan_run_id"],
            ["academic_plan_runs.id"],
            name="fk_academic_plan_warnings_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["academic_plan_term_id"],
            ["academic_plan_terms.id"],
            name="fk_academic_plan_warnings_term",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["academic_plan_course_id"],
            ["academic_plan_courses.id"],
            name="fk_academic_plan_warnings_course",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_academic_plan_warnings_run_severity",
        "academic_plan_warnings",
        ["academic_plan_run_id", "severity"],
    )


def downgrade() -> None:
    op.drop_index("ix_academic_plan_warnings_run_severity", table_name="academic_plan_warnings")
    op.drop_table("academic_plan_warnings")
    op.drop_index("ix_academic_plan_cov_run", table_name="academic_plan_requirement_coverages")
    op.drop_table("academic_plan_requirement_coverages")
    op.drop_index("ix_academic_plan_courses_term_rank", table_name="academic_plan_courses")
    op.drop_table("academic_plan_courses")
    op.drop_index("ix_academic_plan_terms_run_sequence", table_name="academic_plan_terms")
    op.drop_table("academic_plan_terms")
    op.drop_index("ix_academic_plan_runs_scenario", table_name="academic_plan_runs")
    op.drop_index("ix_academic_plan_runs_student_created", table_name="academic_plan_runs")
    op.drop_table("academic_plan_runs")
