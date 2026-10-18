"""create academic scenario what-if tables

Revision ID: 20260623_0005
Revises: 20260623_0004
Create Date: 2026-06-23
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260623_0005"
down_revision: str | None = "20260623_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCENARIO_TYPES = (
    "ADD_MINOR",
    "ADD_SECOND_MAJOR",
    "ADD_CERTIFICATE",
    "ADD_CONCENTRATION",
    "CHANGE_PRIMARY_MAJOR",
    "CUSTOM_COMBINATION",
)
SCENARIO_STATUSES = (
    "DRAFT",
    "RUNNING",
    "COMPLETED",
    "COMPLETED_WITH_WARNINGS",
    "FAILED",
    "ARCHIVED",
)
SCENARIO_RELATIONSHIP_TYPES = (
    "PRIMARY_MAJOR",
    "MINOR",
    "SECOND_MAJOR",
    "CERTIFICATE",
    "CONCENTRATION",
)
SCENARIO_ALLOCATION_TYPES = (
    "PRIMARY",
    "SHARED",
    "UNIQUE_SECONDARY",
    "TOTAL_CREDIT_ONLY",
    "UNALLOCATED",
)
SOURCE_TYPES = (
    "MOCK",
    "OFFICIAL",
    "IMPORTED",
    "STUDENT_PROVIDED",
    "INFERRED",
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


def source_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column("source_type", enum(SOURCE_TYPES, "source_type"), nullable=False),
        sa.Column("is_official", sa.Boolean(), nullable=False),
        sa.Column("source_reference", sa.String(length=500), nullable=True),
        sa.Column("source_retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_confidence", sa.String(length=80), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "academic_plan_scenarios",
        uuid_column("id"),
        uuid_column("student_profile_id"),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("scenario_type", enum(SCENARIO_TYPES, "scenario_type"), nullable=False),
        sa.Column(
            "status",
            enum(SCENARIO_STATUSES, "academic_plan_scenario_status"),
            nullable=False,
        ),
        uuid_column("base_program_version_id"),
        sa.Column("engine_version", sa.String(length=80), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("length(name) > 0", name="ck_acad_plan_scenarios_name"),
        sa.CheckConstraint(
            "length(engine_version) > 0",
            name="ck_acad_plan_scenarios_engine",
        ),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_acad_plan_scenarios_student",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["base_program_version_id"],
            ["program_versions.id"],
            name="fk_acad_plan_scenarios_base_program",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_acad_plan_scenarios_student_created",
        "academic_plan_scenarios",
        ["student_profile_id", "created_at"],
    )

    op.create_table(
        "scenario_programs",
        uuid_column("id"),
        uuid_column("academic_plan_scenario_id"),
        uuid_column("program_version_id"),
        sa.Column(
            "relationship_type",
            enum(SCENARIO_RELATIONSHIP_TYPES, "scenario_relationship_type"),
            nullable=False,
        ),
        sa.Column("is_existing_program", sa.Boolean(), nullable=False),
        sa.Column("is_hypothetical", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("priority >= 0", name="ck_scenario_programs_priority_non_neg"),
        sa.CheckConstraint(
            "is_existing_program != is_hypothetical",
            name="ck_scenario_programs_snapshot_role",
        ),
        sa.ForeignKeyConstraint(
            ["academic_plan_scenario_id"],
            ["academic_plan_scenarios.id"],
            name="fk_scenario_programs_scenario",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["program_version_id"],
            ["program_versions.id"],
            name="fk_scenario_programs_program",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_scenario_programs_scenario_program",
        "scenario_programs",
        ["academic_plan_scenario_id", "program_version_id"],
        unique=True,
    )
    op.create_index(
        "uq_scenario_programs_one_primary",
        "scenario_programs",
        ["academic_plan_scenario_id"],
        unique=True,
        postgresql_where=sa.text("relationship_type = 'PRIMARY_MAJOR'"),
        sqlite_where=sa.text("relationship_type = 'PRIMARY_MAJOR'"),
    )
    op.create_index(
        "ix_scenario_programs_scenario_priority",
        "scenario_programs",
        ["academic_plan_scenario_id", "priority"],
    )

    op.create_table(
        "program_combination_rules",
        uuid_column("id"),
        uuid_column("primary_program_version_id"),
        uuid_column("secondary_program_version_id"),
        sa.Column(
            "combination_type",
            enum(SCENARIO_RELATIONSHIP_TYPES, "scenario_relationship_type"),
            nullable=False,
        ),
        sa.Column("maximum_shared_credits", sa.Numeric(5, 1), nullable=False),
        sa.Column("minimum_unique_secondary_credits", sa.Numeric(5, 1), nullable=False),
        sa.Column("minimum_unique_courses", sa.Integer(), nullable=False),
        sa.Column("allows_double_counting", sa.Boolean(), nullable=False),
        sa.Column("requires_manual_confirmation", sa.Boolean(), nullable=False),
        *source_columns(),
        sa.Column("notes", sa.Text(), nullable=True),
        uuid_column("effective_term_id"),
        uuid_column("expiration_term_id", nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint(
            "primary_program_version_id != secondary_program_version_id",
            name="ck_program_combo_rules_distinct",
        ),
        sa.CheckConstraint(
            "maximum_shared_credits >= 0",
            name="ck_program_combo_rules_max_shared_non_neg",
        ),
        sa.CheckConstraint(
            "minimum_unique_secondary_credits >= 0",
            name="ck_program_combo_rules_unique_credits_non_neg",
        ),
        sa.CheckConstraint(
            "minimum_unique_courses >= 0",
            name="ck_program_combo_rules_unique_courses_non_neg",
        ),
        sa.CheckConstraint(
            "expiration_term_id IS NULL OR expiration_term_id != effective_term_id",
            name="ck_program_combo_rules_terms_distinct",
        ),
        sa.CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_program_combo_rules_mock_not_official",
        ),
        sa.ForeignKeyConstraint(
            ["primary_program_version_id"],
            ["program_versions.id"],
            name="fk_program_combo_rules_primary",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["secondary_program_version_id"],
            ["program_versions.id"],
            name="fk_program_combo_rules_secondary",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["effective_term_id"],
            ["academic_terms.id"],
            name="fk_program_combo_rules_eff_term",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["expiration_term_id"],
            ["academic_terms.id"],
            name="fk_program_combo_rules_exp_term",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_program_combo_rules_direction",
        "program_combination_rules",
        [
            "primary_program_version_id",
            "secondary_program_version_id",
            "combination_type",
            "effective_term_id",
        ],
        unique=True,
    )

    op.create_table(
        "scenario_program_audits",
        uuid_column("id"),
        uuid_column("academic_plan_scenario_id"),
        uuid_column("scenario_program_id"),
        uuid_column("degree_audit_run_id"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["academic_plan_scenario_id"],
            ["academic_plan_scenarios.id"],
            name="fk_scenario_program_audits_scenario",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scenario_program_id"],
            ["scenario_programs.id"],
            name="fk_scenario_program_audits_program",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["degree_audit_run_id"],
            ["degree_audit_runs.id"],
            name="fk_scenario_program_audits_run",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "academic_plan_scenario_id",
            "scenario_program_id",
            name="uq_scenario_program_audits_program",
        ),
        sa.UniqueConstraint(
            "degree_audit_run_id",
            name="uq_scenario_program_audits_run",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "scenario_course_allocations",
        uuid_column("id"),
        uuid_column("academic_plan_scenario_id"),
        uuid_column("student_course_attempt_id", nullable=True),
        uuid_column("transfer_credit_id", nullable=True),
        uuid_column("course_waiver_id", nullable=True),
        uuid_column("course_substitution_id", nullable=True),
        uuid_column("course_id", nullable=True),
        uuid_column("program_version_id", nullable=True),
        uuid_column("requirement_node_id", nullable=True),
        sa.Column(
            "allocation_type",
            enum(SCENARIO_ALLOCATION_TYPES, "scenario_allocation_type"),
            nullable=False,
        ),
        sa.Column("credit_amount", sa.Numeric(5, 1), nullable=False),
        sa.Column("is_shared", sa.Boolean(), nullable=False),
        sa.Column("is_unique_to_program", sa.Boolean(), nullable=False),
        sa.Column("allocation_rank", sa.Integer(), nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "credit_amount >= 0",
            name="ck_scenario_course_allocs_credit_non_neg",
        ),
        sa.CheckConstraint(
            "allocation_rank >= 0",
            name="ck_scenario_course_allocs_rank_non_neg",
        ),
        sa.CheckConstraint("length(reason_code) > 0", name="ck_scenario_course_allocs_reason"),
        sa.CheckConstraint("length(explanation) > 0", name="ck_scenario_course_allocs_explained"),
        sa.CheckConstraint(
            "(CASE WHEN student_course_attempt_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN transfer_credit_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN course_waiver_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN course_substitution_id IS NOT NULL THEN 1 ELSE 0 END) >= 1",
            name="ck_scenario_course_allocs_source",
        ),
        sa.ForeignKeyConstraint(
            ["academic_plan_scenario_id"],
            ["academic_plan_scenarios.id"],
            name="fk_scenario_course_allocs_scenario",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_course_attempt_id"],
            ["student_course_attempts.id"],
            name="fk_scenario_course_allocs_attempt",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["transfer_credit_id"],
            ["transfer_credits.id"],
            name="fk_scenario_course_allocs_transfer",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_waiver_id"],
            ["course_waivers.id"],
            name="fk_scenario_course_allocs_waiver",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_substitution_id"],
            ["course_substitutions.id"],
            name="fk_scenario_course_allocs_substitution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_scenario_course_allocs_course",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["program_version_id"],
            ["program_versions.id"],
            name="fk_scenario_course_allocs_program",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_node_id"],
            ["requirement_nodes.id"],
            name="fk_scenario_course_allocs_requirement",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scenario_course_allocs_scenario_rank",
        "scenario_course_allocations",
        ["academic_plan_scenario_id", "allocation_rank"],
    )

    op.create_table(
        "scenario_comparison_snapshots",
        uuid_column("academic_plan_scenario_id", primary_key=True),
        sa.Column("completed_credits", sa.Numeric(6, 1), nullable=False),
        sa.Column("in_progress_credits", sa.Numeric(6, 1), nullable=False),
        sa.Column("planned_credits", sa.Numeric(6, 1), nullable=False),
        sa.Column("remaining_requirement_credits", sa.Numeric(6, 1), nullable=False),
        sa.Column("shared_credits", sa.Numeric(6, 1), nullable=False),
        sa.Column("unique_secondary_credits", sa.Numeric(6, 1), nullable=False),
        sa.Column("estimated_additional_credits", sa.Numeric(6, 1), nullable=False),
        sa.Column("unresolved_requirements", sa.Integer(), nullable=False),
        sa.Column("manual_review_count", sa.Integer(), nullable=False),
        sa.Column("completion_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("is_estimate", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("completed_credits >= 0", name="ck_scenario_comparison_completed"),
        sa.CheckConstraint("in_progress_credits >= 0", name="ck_scenario_comparison_in_progress"),
        sa.CheckConstraint("planned_credits >= 0", name="ck_scenario_comparison_planned"),
        sa.CheckConstraint(
            "remaining_requirement_credits >= 0",
            name="ck_scenario_comparison_remaining",
        ),
        sa.CheckConstraint("shared_credits >= 0", name="ck_scenario_comparison_shared"),
        sa.CheckConstraint(
            "unique_secondary_credits >= 0",
            name="ck_scenario_comparison_unique",
        ),
        sa.CheckConstraint(
            "estimated_additional_credits >= 0",
            name="ck_scenario_comparison_additional",
        ),
        sa.CheckConstraint(
            "unresolved_requirements >= 0",
            name="ck_scenario_comparison_unresolved",
        ),
        sa.CheckConstraint("manual_review_count >= 0", name="ck_scenario_comparison_manual"),
        sa.CheckConstraint(
            "completion_percentage >= 0 AND completion_percentage <= 100",
            name="ck_scenario_comparison_completion",
        ),
        sa.ForeignKeyConstraint(
            ["academic_plan_scenario_id"],
            ["academic_plan_scenarios.id"],
            name="fk_scenario_comparison_scenario",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "scenario_warnings",
        uuid_column("id"),
        uuid_column("academic_plan_scenario_id"),
        uuid_column("scenario_program_id", nullable=True),
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
        sa.CheckConstraint("length(warning_code) > 0", name="ck_scenario_warnings_code"),
        sa.CheckConstraint("length(message) > 0", name="ck_scenario_warnings_message"),
        sa.ForeignKeyConstraint(
            ["academic_plan_scenario_id"],
            ["academic_plan_scenarios.id"],
            name="fk_scenario_warnings_scenario",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scenario_program_id"],
            ["scenario_programs.id"],
            name="fk_scenario_warnings_program",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scenario_warnings_scenario_severity",
        "scenario_warnings",
        ["academic_plan_scenario_id", "severity"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scenario_warnings_scenario_severity",
        table_name="scenario_warnings",
    )
    op.drop_table("scenario_warnings")
    op.drop_table("scenario_comparison_snapshots")
    op.drop_index(
        "ix_scenario_course_allocs_scenario_rank",
        table_name="scenario_course_allocations",
    )
    op.drop_table("scenario_course_allocations")
    op.drop_table("scenario_program_audits")
    op.drop_index("uq_program_combo_rules_direction", table_name="program_combination_rules")
    op.drop_table("program_combination_rules")
    op.drop_index(
        "ix_scenario_programs_scenario_priority",
        table_name="scenario_programs",
    )
    op.drop_index("uq_scenario_programs_one_primary", table_name="scenario_programs")
    op.drop_index(
        "uq_scenario_programs_scenario_program",
        table_name="scenario_programs",
    )
    op.drop_table("scenario_programs")
    op.drop_index(
        "ix_acad_plan_scenarios_student_created",
        table_name="academic_plan_scenarios",
    )
    op.drop_table("academic_plan_scenarios")
