"""create course eligibility check tables

Revision ID: 20260624_0006
Revises: 20260623_0005
Create Date: 2026-06-24
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260624_0006"
down_revision: str | None = "20260623_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ELIGIBILITY_MODES = ("CURRENT", "PROJECTED", "REGISTRATION")
ELIGIBILITY_STATUSES = (
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "COMPLETED_WITH_WARNINGS",
)
ELIGIBILITY_OVERALL_RESULTS = (
    "ELIGIBLE",
    "CONDITIONALLY_ELIGIBLE",
    "NOT_ELIGIBLE",
    "PERMISSION_REQUIRED",
    "MANUAL_REVIEW_REQUIRED",
)
ELIGIBILITY_RULE_RESULTS = (
    "SATISFIED",
    "CONDITIONALLY_SATISFIED",
    "NOT_SATISFIED",
    "PERMISSION_REQUIRED",
    "MANUAL_REVIEW_REQUIRED",
    "NOT_APPLICABLE",
)
COURSE_RULE_TYPES = (
    "PREREQUISITE",
    "COREQUISITE",
    "REGISTRATION_RESTRICTION",
    "REPEAT_RESTRICTION",
    "PERMISSION",
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
        "eligibility_check_runs",
        uuid_column("id"),
        uuid_column("institution_id"),
        uuid_column("student_profile_id"),
        uuid_column("course_id"),
        uuid_column("section_id", nullable=True),
        uuid_column("target_term_id"),
        sa.Column("mode", enum(ELIGIBILITY_MODES, "eligibility_mode"), nullable=False),
        sa.Column(
            "status",
            enum(ELIGIBILITY_STATUSES, "eligibility_check_status"),
            nullable=False,
        ),
        sa.Column("engine_version", sa.String(length=80), nullable=False),
        sa.Column(
            "overall_result",
            enum(ELIGIBILITY_OVERALL_RESULTS, "eligibility_overall_result"),
            nullable=False,
        ),
        sa.Column(
            "academic_eligibility_result",
            enum(ELIGIBILITY_OVERALL_RESULTS, "eligibility_academic_result"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_snapshot_hash", sa.String(length=128), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("length(engine_version) > 0", name="ck_eligibility_runs_engine"),
        sa.CheckConstraint("length(source_snapshot_hash) > 0", name="ck_eligibility_runs_hash"),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_eligibility_runs_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_eligibility_runs_student",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_eligibility_runs_course_inst",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["section_id", "course_id", "institution_id"],
            ["sections.id", "sections.course_id", "sections.institution_id"],
            name="fk_eligibility_runs_section_course_inst",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_term_id", "institution_id"],
            ["academic_terms.id", "academic_terms.institution_id"],
            name="fk_eligibility_runs_term_inst",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_eligibility_runs_student_created",
        "eligibility_check_runs",
        ["student_profile_id", "created_at"],
    )
    op.create_index(
        "ix_eligibility_runs_course_term",
        "eligibility_check_runs",
        ["course_id", "target_term_id", "mode"],
    )

    op.create_table(
        "rule_evaluations",
        uuid_column("id"),
        uuid_column("eligibility_check_run_id"),
        uuid_column("course_rule_id"),
        sa.Column(
            "result",
            enum(ELIGIBILITY_RULE_RESULTS, "eligibility_rule_result"),
            nullable=False,
        ),
        sa.Column("rule_type", enum(COURSE_RULE_TYPES, "course_rule_type"), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "display_order >= 0",
            name="ck_rule_evals_display_order_non_neg",
        ),
        sa.CheckConstraint("length(explanation) > 0", name="ck_rule_evals_explanation"),
        sa.ForeignKeyConstraint(
            ["eligibility_check_run_id"],
            ["eligibility_check_runs.id"],
            name="fk_rule_evaluations_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_rule_id"],
            ["course_rules.id"],
            name="fk_rule_evaluations_rule",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "eligibility_check_run_id",
            "course_rule_id",
            name="uq_rule_evals_run_rule",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rule_evals_run_order",
        "rule_evaluations",
        ["eligibility_check_run_id", "display_order"],
    )

    op.create_table(
        "rule_expression_evaluations",
        uuid_column("id"),
        uuid_column("rule_evaluation_id"),
        uuid_column("course_rule_expression_id"),
        sa.Column(
            "result",
            enum(ELIGIBILITY_RULE_RESULTS, "eligibility_rule_result"),
            nullable=False,
        ),
        sa.Column("actual_value", sa.Text(), nullable=True),
        sa.Column("expected_value", sa.Text(), nullable=True),
        uuid_column("matched_course_id", nullable=True),
        uuid_column("matched_attempt_id", nullable=True),
        sa.Column("reason_code", sa.String(length=80), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("length(reason_code) > 0", name="ck_rule_expr_evals_reason"),
        sa.CheckConstraint("length(explanation) > 0", name="ck_rule_expr_evals_explanation"),
        sa.ForeignKeyConstraint(
            ["rule_evaluation_id"],
            ["rule_evaluations.id"],
            name="fk_rule_expr_evals_rule_eval",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_rule_expression_id"],
            ["course_rule_expressions.id"],
            name="fk_rule_expr_evals_expression",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["matched_course_id"],
            ["courses.id"],
            name="fk_rule_expr_evals_matched_course",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["matched_attempt_id"],
            ["student_course_attempts.id"],
            name="fk_rule_expr_evals_matched_attempt",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "rule_evaluation_id",
            "course_rule_expression_id",
            name="uq_rule_expr_evals_rule_expression",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rule_expr_evals_rule_eval",
        "rule_expression_evaluations",
        ["rule_evaluation_id"],
    )

    op.create_table(
        "eligibility_warnings",
        uuid_column("id"),
        uuid_column("eligibility_check_run_id"),
        uuid_column("rule_evaluation_id", nullable=True),
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
        sa.CheckConstraint("length(warning_code) > 0", name="ck_eligibility_warnings_code"),
        sa.CheckConstraint("length(message) > 0", name="ck_eligibility_warnings_message"),
        sa.ForeignKeyConstraint(
            ["eligibility_check_run_id"],
            ["eligibility_check_runs.id"],
            name="fk_eligibility_warnings_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["rule_evaluation_id"],
            ["rule_evaluations.id"],
            name="fk_eligibility_warnings_rule_eval",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_eligibility_warnings_run_severity",
        "eligibility_warnings",
        ["eligibility_check_run_id", "severity"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_eligibility_warnings_run_severity",
        table_name="eligibility_warnings",
    )
    op.drop_table("eligibility_warnings")
    op.drop_index("ix_rule_expr_evals_rule_eval", table_name="rule_expression_evaluations")
    op.drop_table("rule_expression_evaluations")
    op.drop_index("ix_rule_evals_run_order", table_name="rule_evaluations")
    op.drop_table("rule_evaluations")
    op.drop_index("ix_eligibility_runs_course_term", table_name="eligibility_check_runs")
    op.drop_index("ix_eligibility_runs_student_created", table_name="eligibility_check_runs")
    op.drop_table("eligibility_check_runs")
