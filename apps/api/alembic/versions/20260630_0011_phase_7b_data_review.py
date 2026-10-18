"""create phase 7b data review and application tables

Revision ID: 20260630_0011
Revises: 20260630_0010
Create Date: 2026-06-30
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260630_0011"
down_revision: str | None = "20260630_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUDIT_WARNING_SEVERITIES = ("INFO", "WARNING", "ERROR")
DATA_IMPORT_REVIEW_STATUSES = (
    "DRAFT",
    "IN_REVIEW",
    "READY_TO_APPLY",
    "APPLYING",
    "APPLIED",
    "APPLIED_WITH_WARNINGS",
    "FAILED",
    "ARCHIVED",
)
IMPORTED_RECORD_REVIEW_DECISIONS = (
    "UNREVIEWED",
    "CONFIRMED",
    "REJECTED",
    "NEEDS_ADVISOR_REVIEW",
    "EDITED_AND_CONFIRMED",
    "DEFERRED",
)
DATA_APPLICATION_STATUSES = (
    "PENDING",
    "APPLYING",
    "APPLIED",
    "APPLIED_WITH_WARNINGS",
    "FAILED",
    "ROLLED_BACK",
)
APPLIED_IMPORT_TARGET_ENTITY_TYPES = (
    "STUDENT_COURSE_ATTEMPT",
    "TRANSFER_CREDIT",
    "COURSE",
    "SECTION",
    "SECTION_MEETING",
    "COURSE_OFFERING_PATTERN",
    "UNKNOWN",
)
APPLIED_IMPORT_ACTIONS = (
    "CREATED",
    "UPDATED",
    "SKIPPED_DUPLICATE",
    "SKIPPED_REJECTED",
    "SKIPPED_DEFERRED",
    "SKIPPED_ADVISOR_REVIEW",
    "SKIPPED_UNSUPPORTED",
)
APPLIED_IMPORT_STATUSES = ("SUCCESS", "WARNING", "FAILED", "SKIPPED")


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
        "data_import_review_sessions",
        uuid_column("id"),
        uuid_column("data_import_run_id"),
        uuid_column("student_profile_id"),
        sa.Column(
            "status",
            enum(DATA_IMPORT_REVIEW_STATUSES, "data_import_review_status"),
            nullable=False,
        ),
        sa.Column("reviewer_label", sa.String(length=255), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("length(reviewer_label) > 0", name="ck_data_import_reviews_reviewer"),
        sa.ForeignKeyConstraint(
            ["data_import_run_id"],
            ["data_import_runs.id"],
            name="fk_data_import_review_sessions_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_data_import_review_sessions_student",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_data_import_reviews_run_status",
        "data_import_review_sessions",
        ["data_import_run_id", "status"],
    )
    op.create_index(
        "ix_data_import_reviews_student_created",
        "data_import_review_sessions",
        ["student_profile_id", "created_at"],
    )

    op.create_table(
        "imported_record_reviews",
        uuid_column("id"),
        uuid_column("review_session_id"),
        uuid_column("imported_record_id"),
        uuid_column("selected_mapping_candidate_id", nullable=True),
        sa.Column(
            "decision",
            enum(IMPORTED_RECORD_REVIEW_DECISIONS, "imported_record_review_decision"),
            nullable=False,
        ),
        sa.Column("edited_normalized_payload", sa.JSON(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("requires_advisor_confirmation", sa.Boolean(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["review_session_id"],
            ["data_import_review_sessions.id"],
            name="fk_imported_record_reviews_session",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["imported_record_id"],
            ["imported_records.id"],
            name="fk_imported_record_reviews_record",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["selected_mapping_candidate_id"],
            ["import_mapping_candidates.id"],
            name="fk_imported_record_reviews_candidate",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "review_session_id",
            "imported_record_id",
            name="uq_imported_record_reviews_session_record",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_imported_record_reviews_session_decision",
        "imported_record_reviews",
        ["review_session_id", "decision"],
    )

    op.create_table(
        "data_application_runs",
        uuid_column("id"),
        uuid_column("review_session_id"),
        sa.Column(
            "status",
            enum(DATA_APPLICATION_STATUSES, "data_application_status"),
            nullable=False,
        ),
        sa.Column("applied_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("applied_count >= 0", name="ck_data_applications_applied_count"),
        sa.CheckConstraint("skipped_count >= 0", name="ck_data_applications_skipped_count"),
        sa.CheckConstraint("warning_count >= 0", name="ck_data_applications_warning_count"),
        sa.CheckConstraint("error_count >= 0", name="ck_data_applications_error_count"),
        sa.ForeignKeyConstraint(
            ["review_session_id"],
            ["data_import_review_sessions.id"],
            name="fk_data_application_runs_review",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_data_applications_review_created",
        "data_application_runs",
        ["review_session_id", "created_at"],
    )

    op.create_table(
        "applied_imported_records",
        uuid_column("id"),
        uuid_column("data_application_run_id"),
        uuid_column("imported_record_review_id"),
        uuid_column("imported_record_id"),
        sa.Column(
            "target_entity_type",
            enum(APPLIED_IMPORT_TARGET_ENTITY_TYPES, "applied_import_target_entity_type"),
            nullable=False,
        ),
        uuid_column("target_entity_id", nullable=True),
        sa.Column("action", enum(APPLIED_IMPORT_ACTIONS, "applied_import_action"), nullable=False),
        sa.Column(
            "status",
            enum(APPLIED_IMPORT_STATUSES, "applied_import_status"),
            nullable=False,
        ),
        sa.Column("reason_code", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        created_at_column(),
        sa.CheckConstraint(
            "length(reason_code) > 0",
            name="ck_applied_imported_records_reason_code",
        ),
        sa.CheckConstraint("length(message) > 0", name="ck_applied_imported_records_message"),
        sa.ForeignKeyConstraint(
            ["data_application_run_id"],
            ["data_application_runs.id"],
            name="fk_applied_imported_records_application",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["imported_record_review_id"],
            ["imported_record_reviews.id"],
            name="fk_applied_imported_records_review",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["imported_record_id"],
            ["imported_records.id"],
            name="fk_applied_imported_records_record",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "data_application_run_id",
            "imported_record_id",
            name="uq_applied_imported_records_application_record",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_applied_imported_records_target",
        "applied_imported_records",
        ["target_entity_type", "target_entity_id"],
    )

    op.create_table(
        "data_review_warnings",
        uuid_column("id"),
        uuid_column("review_session_id"),
        uuid_column("imported_record_review_id", nullable=True),
        uuid_column("data_application_run_id", nullable=True),
        sa.Column("warning_code", sa.String(length=80), nullable=False),
        sa.Column(
            "severity",
            enum(AUDIT_WARNING_SEVERITIES, "audit_warning_severity"),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("requires_advisor_confirmation", sa.Boolean(), nullable=False),
        created_at_column(),
        sa.CheckConstraint("length(warning_code) > 0", name="ck_data_review_warnings_code"),
        sa.CheckConstraint("length(message) > 0", name="ck_data_review_warnings_message"),
        sa.ForeignKeyConstraint(
            ["review_session_id"],
            ["data_import_review_sessions.id"],
            name="fk_data_review_warnings_session",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["imported_record_review_id"],
            ["imported_record_reviews.id"],
            name="fk_data_review_warnings_record_review",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["data_application_run_id"],
            ["data_application_runs.id"],
            name="fk_data_review_warnings_application",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_data_review_warnings_session_severity",
        "data_review_warnings",
        ["review_session_id", "severity"],
    )


def downgrade() -> None:
    op.drop_index("ix_data_review_warnings_session_severity", table_name="data_review_warnings")
    op.drop_table("data_review_warnings")
    op.drop_index("ix_applied_imported_records_target", table_name="applied_imported_records")
    op.drop_table("applied_imported_records")
    op.drop_index("ix_data_applications_review_created", table_name="data_application_runs")
    op.drop_table("data_application_runs")
    op.drop_index(
        "ix_imported_record_reviews_session_decision",
        table_name="imported_record_reviews",
    )
    op.drop_table("imported_record_reviews")
    op.drop_index(
        "ix_data_import_reviews_student_created",
        table_name="data_import_review_sessions",
    )
    op.drop_index("ix_data_import_reviews_run_status", table_name="data_import_review_sessions")
    op.drop_table("data_import_review_sessions")
