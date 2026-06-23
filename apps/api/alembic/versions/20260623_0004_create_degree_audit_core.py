"""create degree audit core

Revision ID: 20260623_0004
Revises: 20260623_0003
Create Date: 2026-06-23
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260623_0004"
down_revision: str | None = "20260623_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COURSE_ATTEMPT_STATUSES = (
    "COMPLETED",
    "IN_PROGRESS",
    "PLANNED",
    "FAILED",
    "WITHDRAWN",
    "INCOMPLETE",
    "TRANSFERRED",
)
OLD_COURSE_ATTEMPT_STATUSES = (
    "COMPLETED",
    "IN_PROGRESS",
    "PLANNED",
    "FAILED",
    "WITHDRAWN",
    "TRANSFERRED",
)
AUDIT_RUN_STATUSES = (
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "COMPLETED_WITH_WARNINGS",
)
AUDIT_MODES = ("CURRENT", "PROJECTED")
REQUIREMENT_EVALUATION_STATUSES = (
    "SATISFIED",
    "IN_PROGRESS",
    "PLANNED",
    "PARTIALLY_SATISFIED",
    "NOT_SATISFIED",
    "WAIVED",
    "MANUAL_REVIEW_REQUIRED",
    "NOT_APPLICABLE",
)
AUDIT_APPLICATION_TYPES = (
    "COURSE_ATTEMPT",
    "TRANSFER_CREDIT",
    "WAIVER",
    "SUBSTITUTION",
    "EQUIVALENCY",
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


def uuid_column(name: str, *, nullable: bool = False) -> sa.Column[Any]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)


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


def replace_attempt_status_constraint(values: tuple[str, ...]) -> None:
    op.drop_constraint(
        "student_course_attempt_status",
        "student_course_attempts",
        type_="check",
    )
    quoted = ", ".join(f"'{value}'" for value in values)
    op.create_check_constraint(
        "student_course_attempt_status",
        "student_course_attempts",
        f"status IN ({quoted})",
    )


def upgrade() -> None:
    replace_attempt_status_constraint(COURSE_ATTEMPT_STATUSES)

    op.create_table(
        "degree_audit_runs",
        uuid_column("id"),
        uuid_column("student_profile_id"),
        uuid_column("program_version_id"),
        sa.Column("status", enum(AUDIT_RUN_STATUSES, "audit_run_status"), nullable=False),
        sa.Column("engine_version", sa.String(length=80), nullable=False),
        sa.Column("calculation_mode", enum(AUDIT_MODES, "audit_mode"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_required_credits", sa.Numeric(6, 1), nullable=False),
        sa.Column("completed_credits", sa.Numeric(6, 1), nullable=False),
        sa.Column("in_progress_credits", sa.Numeric(6, 1), nullable=False),
        sa.Column("planned_credits", sa.Numeric(6, 1), nullable=False),
        sa.Column("remaining_credits", sa.Numeric(6, 1), nullable=False),
        sa.Column("completion_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("source_snapshot_hash", sa.String(length=128), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "total_required_credits >= 0",
            name="ck_degree_audit_runs_total_required_non_negative",
        ),
        sa.CheckConstraint(
            "completed_credits >= 0",
            name="ck_degree_audit_runs_completed_non_negative",
        ),
        sa.CheckConstraint(
            "in_progress_credits >= 0",
            name="ck_degree_audit_runs_in_progress_non_negative",
        ),
        sa.CheckConstraint(
            "planned_credits >= 0",
            name="ck_degree_audit_runs_planned_non_negative",
        ),
        sa.CheckConstraint(
            "remaining_credits >= 0",
            name="ck_degree_audit_runs_remaining_non_negative",
        ),
        sa.CheckConstraint(
            "completion_percentage >= 0 AND completion_percentage <= 100",
            name="ck_degree_audit_runs_completion_percentage_range",
        ),
        sa.CheckConstraint(
            "length(engine_version) > 0",
            name="ck_degree_audit_runs_engine_version",
        ),
        sa.CheckConstraint(
            "length(source_snapshot_hash) > 0",
            name="ck_degree_audit_runs_source_hash",
        ),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_degree_audit_runs_student",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["program_version_id"],
            ["program_versions.id"],
            name="fk_degree_audit_runs_program_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_degree_audit_runs_student_created",
        "degree_audit_runs",
        ["student_profile_id", "created_at"],
    )

    op.create_table(
        "requirement_evaluations",
        uuid_column("id"),
        uuid_column("degree_audit_run_id"),
        uuid_column("requirement_node_id"),
        sa.Column(
            "status",
            enum(REQUIREMENT_EVALUATION_STATUSES, "requirement_evaluation_status"),
            nullable=False,
        ),
        sa.Column("required_credits", sa.Numeric(6, 1), nullable=True),
        sa.Column("satisfied_credits", sa.Numeric(6, 1), nullable=False),
        sa.Column("remaining_credits", sa.Numeric(6, 1), nullable=False),
        sa.Column("required_courses", sa.Integer(), nullable=True),
        sa.Column("satisfied_courses", sa.Integer(), nullable=False),
        sa.Column("remaining_courses", sa.Integer(), nullable=False),
        sa.Column("minimum_grade", sa.String(length=8), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "required_credits IS NULL OR required_credits >= 0",
            name="ck_requirement_evaluations_required_credits_non_negative",
        ),
        sa.CheckConstraint(
            "satisfied_credits >= 0",
            name="ck_requirement_evaluations_satisfied_credits_non_negative",
        ),
        sa.CheckConstraint(
            "remaining_credits >= 0",
            name="ck_requirement_evaluations_remaining_credits_non_negative",
        ),
        sa.CheckConstraint(
            "required_courses IS NULL OR required_courses >= 0",
            name="ck_requirement_evaluations_required_courses_non_negative",
        ),
        sa.CheckConstraint(
            "satisfied_courses >= 0",
            name="ck_requirement_evaluations_satisfied_courses_non_negative",
        ),
        sa.CheckConstraint(
            "remaining_courses >= 0",
            name="ck_requirement_evaluations_remaining_courses_non_negative",
        ),
        sa.CheckConstraint(
            "display_order >= 0",
            name="ck_requirement_evaluations_display_order_non_negative",
        ),
        sa.CheckConstraint(
            "length(explanation) > 0",
            name="ck_requirement_evaluations_explained",
        ),
        sa.ForeignKeyConstraint(
            ["degree_audit_run_id"],
            ["degree_audit_runs.id"],
            name="fk_requirement_evaluations_audit_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_node_id"],
            ["requirement_nodes.id"],
            name="fk_requirement_evaluations_requirement_node",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "degree_audit_run_id",
            "requirement_node_id",
            name="uq_requirement_evaluations_run_node",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_requirement_evaluations_run_order",
        "requirement_evaluations",
        ["degree_audit_run_id", "display_order"],
    )

    op.create_table(
        "audit_course_applications",
        uuid_column("id"),
        uuid_column("degree_audit_run_id"),
        uuid_column("requirement_evaluation_id"),
        uuid_column("course_id", nullable=True),
        uuid_column("student_course_attempt_id", nullable=True),
        uuid_column("transfer_credit_id", nullable=True),
        uuid_column("course_waiver_id", nullable=True),
        uuid_column("course_substitution_id", nullable=True),
        sa.Column(
            "application_type",
            enum(AUDIT_APPLICATION_TYPES, "audit_application_type"),
            nullable=False,
        ),
        sa.Column("credit_amount", sa.Numeric(5, 1), nullable=False),
        sa.Column("grade", sa.String(length=8), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.Column("is_in_progress", sa.Boolean(), nullable=False),
        sa.Column("is_planned", sa.Boolean(), nullable=False),
        sa.Column("is_shared", sa.Boolean(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "credit_amount >= 0",
            name="ck_audit_course_applications_credit_non_neg",
        ),
        sa.CheckConstraint(
            "length(explanation) > 0",
            name="ck_audit_course_applications_explained",
        ),
        sa.CheckConstraint(
            "(CASE WHEN student_course_attempt_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN transfer_credit_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN course_waiver_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN course_substitution_id IS NOT NULL THEN 1 ELSE 0 END) = 1 "
            "OR (student_course_attempt_id IS NOT NULL AND course_substitution_id IS NOT NULL "
            "AND transfer_credit_id IS NULL AND course_waiver_id IS NULL)",
            name="ck_audit_course_applications_source_shape",
        ),
        sa.ForeignKeyConstraint(
            ["degree_audit_run_id"],
            ["degree_audit_runs.id"],
            name="fk_audit_course_applications_audit_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_evaluation_id"],
            ["requirement_evaluations.id"],
            name="fk_audit_course_applications_evaluation",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_audit_course_applications_course",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_course_attempt_id"],
            ["student_course_attempts.id"],
            name="fk_audit_course_applications_attempt",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["transfer_credit_id"],
            ["transfer_credits.id"],
            name="fk_audit_course_applications_transfer",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_waiver_id"],
            ["course_waivers.id"],
            name="fk_audit_course_applications_waiver",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_substitution_id"],
            ["course_substitutions.id"],
            name="fk_audit_course_applications_substitution",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_course_applications_run_eval",
        "audit_course_applications",
        ["degree_audit_run_id", "requirement_evaluation_id"],
    )

    op.create_table(
        "degree_audit_warnings",
        uuid_column("id"),
        uuid_column("degree_audit_run_id"),
        uuid_column("requirement_evaluation_id", nullable=True),
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
        sa.CheckConstraint(
            "length(warning_code) > 0",
            name="ck_degree_audit_warnings_code",
        ),
        sa.CheckConstraint(
            "length(message) > 0",
            name="ck_degree_audit_warnings_message",
        ),
        sa.ForeignKeyConstraint(
            ["degree_audit_run_id"],
            ["degree_audit_runs.id"],
            name="fk_degree_audit_warnings_audit_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_evaluation_id"],
            ["requirement_evaluations.id"],
            name="fk_degree_audit_warnings_evaluation",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_degree_audit_warnings_run_severity",
        "degree_audit_warnings",
        ["degree_audit_run_id", "severity"],
    )


def downgrade() -> None:
    op.drop_index("ix_degree_audit_warnings_run_severity", table_name="degree_audit_warnings")
    op.drop_table("degree_audit_warnings")
    op.drop_index(
        "ix_audit_course_applications_run_eval",
        table_name="audit_course_applications",
    )
    op.drop_table("audit_course_applications")
    op.drop_index(
        "ix_requirement_evaluations_run_order",
        table_name="requirement_evaluations",
    )
    op.drop_table("requirement_evaluations")
    op.drop_index("ix_degree_audit_runs_student_created", table_name="degree_audit_runs")
    op.drop_table("degree_audit_runs")
    replace_attempt_status_constraint(OLD_COURSE_ATTEMPT_STATUSES)
