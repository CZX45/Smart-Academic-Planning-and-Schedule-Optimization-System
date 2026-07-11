"""add reviewed MyProgress course-state snapshots

Revision ID: 20260711_0014
Revises: 20260701_0013
Create Date: 2026-07-11
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260711_0014"
down_revision: str | None = "20260701_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE_TYPES = (
    "MOCK",
    "OFFICIAL",
    "IMPORTED",
    "BROWSER_EXTENSION",
    "STUDENT_PROVIDED",
    "INFERRED",
)
COURSE_STATE_STATUSES = (
    "COMPLETED",
    "IN_PROGRESS",
    "PLANNED",
    "NOT_STARTED",
    "UNKNOWN",
)
COURSE_STATE_VALIDATION_STATES = (
    "RELIABLE",
    "RELIABLE_WITH_WARNINGS",
    "EXTERNAL_EVIDENCE",
    "EXCEPTION",
)
IMPORTED_RECORD_REVIEW_DECISIONS = (
    "UNREVIEWED",
    "CONFIRMED",
    "REJECTED",
    "NEEDS_ADVISOR_REVIEW",
    "EDITED_AND_CONFIRMED",
    "DEFERRED",
)
OLD_APPLIED_TARGETS = (
    "STUDENT_COURSE_ATTEMPT",
    "TRANSFER_CREDIT",
    "COURSE",
    "SECTION",
    "SECTION_MEETING",
    "COURSE_OFFERING_PATTERN",
    "UNKNOWN",
)
NEW_APPLIED_TARGETS = (*OLD_APPLIED_TARGETS[:-1], "COURSE_STATE", "UNKNOWN")


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


def source_metadata_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column("source_type", enum(SOURCE_TYPES, "source_type"), nullable=False),
        sa.Column("is_official", sa.Boolean(), nullable=False),
        sa.Column("source_reference", sa.String(length=500), nullable=True),
        sa.Column("source_retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_confidence", sa.String(length=80), nullable=True),
    ]


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


def _replace_applied_target_constraint(values: tuple[str, ...]) -> None:
    op.drop_constraint(
        "applied_import_target_entity_type",
        "applied_imported_records",
        type_="check",
    )
    allowed = ", ".join(f"'{value}'" for value in values)
    op.create_check_constraint(
        "applied_import_target_entity_type",
        "applied_imported_records",
        f"target_entity_type IN ({allowed})",
    )


def upgrade() -> None:
    _replace_applied_target_constraint(NEW_APPLIED_TARGETS)

    op.create_table(
        "course_state_snapshots",
        uuid_column("id"),
        uuid_column("student_profile_id"),
        uuid_column("data_import_run_id"),
        uuid_column("review_session_id"),
        uuid_column("data_application_run_id"),
        sa.Column("source_page_type", sa.String(length=120), nullable=False),
        sa.Column("source_validation_state", sa.String(length=80), nullable=False),
        sa.Column("program_mapping_state", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_advisory", sa.Boolean(), nullable=False),
        sa.Column("official_application_ready", sa.Boolean(), nullable=False),
        sa.Column("extraction_bounded", sa.Boolean(), nullable=False),
        sa.Column("extraction_truncated", sa.Boolean(), nullable=False),
        sa.Column("completed_count", sa.Integer(), nullable=False),
        sa.Column("in_progress_count", sa.Integer(), nullable=False),
        sa.Column("planned_count", sa.Integer(), nullable=False),
        sa.Column("not_started_count", sa.Integer(), nullable=False),
        sa.Column("matched_count", sa.Integer(), nullable=False),
        sa.Column("unmatched_count", sa.Integer(), nullable=False),
        sa.Column("exception_count", sa.Integer(), nullable=False),
        sa.Column("program_summary", sa.JSON(), nullable=False),
        sa.Column("credit_summary", sa.JSON(), nullable=False),
        sa.Column("requirement_summary", sa.JSON(), nullable=False),
        sa.Column("readiness_payload", sa.JSON(), nullable=False),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        *source_metadata_columns(),
        *timestamp_columns(),
        sa.CheckConstraint("is_official = false", name="ck_course_state_snapshots_unofficial"),
        sa.CheckConstraint(
            "official_application_ready = false",
            name="ck_course_state_snapshots_not_official_ready",
        ),
        sa.CheckConstraint("is_advisory = true", name="ck_course_state_snapshots_advisory"),
        sa.CheckConstraint("completed_count >= 0", name="ck_course_state_snapshots_completed"),
        sa.CheckConstraint(
            "in_progress_count >= 0",
            name="ck_course_state_snapshots_in_progress",
        ),
        sa.CheckConstraint("planned_count >= 0", name="ck_course_state_snapshots_planned"),
        sa.CheckConstraint(
            "not_started_count >= 0",
            name="ck_course_state_snapshots_not_started",
        ),
        sa.CheckConstraint("matched_count >= 0", name="ck_course_state_snapshots_matched"),
        sa.CheckConstraint("unmatched_count >= 0", name="ck_course_state_snapshots_unmatched"),
        sa.CheckConstraint("exception_count >= 0", name="ck_course_state_snapshots_exception"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_course_state_snapshots_student",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["data_import_run_id"],
            ["data_import_runs.id"],
            name="fk_course_state_snapshots_import",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["review_session_id"],
            ["data_import_review_sessions.id"],
            name="fk_course_state_snapshots_review",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["data_application_run_id"],
            ["data_application_runs.id"],
            name="fk_course_state_snapshots_application",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("data_import_run_id", name="uq_course_state_snapshots_import"),
        sa.UniqueConstraint(
            "data_application_run_id",
            name="uq_course_state_snapshots_application",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_course_state_snapshots_active_student",
        "course_state_snapshots",
        ["student_profile_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
        sqlite_where=sa.text("is_active = true"),
    )
    op.create_index(
        "ix_course_state_snapshots_student_applied",
        "course_state_snapshots",
        ["student_profile_id", "applied_at"],
    )

    op.add_column(
        "student_course_attempts",
        uuid_column("course_state_snapshot_id", nullable=True),
    )
    op.create_foreign_key(
        "fk_student_course_attempts_course_state_snapshot",
        "student_course_attempts",
        "course_state_snapshots",
        ["course_state_snapshot_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_student_course_attempts_course_state_snapshot",
        "student_course_attempts",
        ["course_state_snapshot_id"],
    )

    op.create_table(
        "course_state_records",
        uuid_column("id"),
        uuid_column("snapshot_id"),
        uuid_column("imported_record_id"),
        uuid_column("imported_record_review_id"),
        uuid_column("matched_course_id", nullable=True),
        uuid_column("student_course_attempt_id", nullable=True),
        sa.Column("normalized_course_code", sa.String(length=80), nullable=False),
        sa.Column("source_course_code", sa.String(length=80), nullable=False),
        sa.Column("source_course_title", sa.String(length=500), nullable=False),
        sa.Column("status", enum(COURSE_STATE_STATUSES, "course_state_status"), nullable=False),
        sa.Column("term", sa.String(length=80), nullable=True),
        sa.Column("credits", sa.Numeric(5, 2), nullable=True),
        sa.Column("grade", sa.String(length=16), nullable=True),
        sa.Column("requirement_context", sa.String(length=500), nullable=True),
        sa.Column("source_page_type", sa.String(length=120), nullable=False),
        sa.Column("source_table_index", sa.String(length=80), nullable=True),
        sa.Column("source_row_index", sa.String(length=80), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("confidence_score", sa.Numeric(4, 2), nullable=False),
        sa.Column(
            "validation_state",
            enum(COURSE_STATE_VALIDATION_STATES, "course_state_validation_state"),
            nullable=False,
        ),
        sa.Column(
            "review_decision",
            enum(IMPORTED_RECORD_REVIEW_DECISIONS, "imported_record_review_decision"),
            nullable=False,
        ),
        sa.Column("application_reason_code", sa.String(length=80), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_course_state_records_confidence",
        ),
        sa.CheckConstraint(
            "credits IS NULL OR credits >= 0",
            name="ck_course_state_records_credits",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["course_state_snapshots.id"],
            name="fk_course_state_records_snapshot",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["imported_record_id"],
            ["imported_records.id"],
            name="fk_course_state_records_imported_record",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["imported_record_review_id"],
            ["imported_record_reviews.id"],
            name="fk_course_state_records_record_review",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["matched_course_id"],
            ["courses.id"],
            name="fk_course_state_records_course",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["student_course_attempt_id"],
            ["student_course_attempts.id"],
            name="fk_course_state_records_attempt",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "snapshot_id",
            "imported_record_id",
            name="uq_course_state_records_snapshot_imported_record",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_course_state_records_snapshot_status",
        "course_state_records",
        ["snapshot_id", "status"],
    )
    op.create_index(
        "ix_course_state_records_matched_course",
        "course_state_records",
        ["matched_course_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_course_state_records_matched_course", table_name="course_state_records")
    op.drop_index("ix_course_state_records_snapshot_status", table_name="course_state_records")
    op.drop_table("course_state_records")
    op.drop_index(
        "ix_student_course_attempts_course_state_snapshot",
        table_name="student_course_attempts",
    )
    op.drop_constraint(
        "fk_student_course_attempts_course_state_snapshot",
        "student_course_attempts",
        type_="foreignkey",
    )
    op.drop_column("student_course_attempts", "course_state_snapshot_id")
    op.drop_index(
        "ix_course_state_snapshots_student_applied",
        table_name="course_state_snapshots",
    )
    op.drop_index(
        "uq_course_state_snapshots_active_student",
        table_name="course_state_snapshots",
    )
    op.drop_table("course_state_snapshots")
    _replace_applied_target_constraint(OLD_APPLIED_TARGETS)
