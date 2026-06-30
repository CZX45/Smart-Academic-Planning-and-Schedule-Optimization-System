"""create phase 7a read-only data import staging tables

Revision ID: 20260630_0010
Revises: 20260630_0009
Create Date: 2026-06-30
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260630_0010"
down_revision: str | None = "20260630_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE_TYPES = ("MOCK", "OFFICIAL", "IMPORTED", "STUDENT_PROVIDED", "INFERRED")
AUDIT_WARNING_SEVERITIES = ("INFO", "WARNING", "ERROR")
DATA_IMPORT_TYPES = (
    "UNOFFICIAL_TRANSCRIPT",
    "DEGREE_AUDIT_EXPORT",
    "COURSE_CATALOG",
    "SECTION_SCHEDULE",
    "GENERIC_CSV",
    "GENERIC_JSON",
    "UNKNOWN",
)
DATA_IMPORT_STATUSES = (
    "PENDING",
    "PARSING",
    "PARSED",
    "PARSED_WITH_WARNINGS",
    "FAILED",
    "REVIEW_REQUIRED",
    "ARCHIVED",
)
DATA_IMPORT_STORAGE_STRATEGIES = (
    "METADATA_ONLY",
    "LOCAL_DEV_FIXTURE",
    "EXTERNAL_OBJECT_REFERENCE",
    "NOT_STORED",
)
IMPORTED_RECORD_TYPES = (
    "COURSE_ATTEMPT",
    "TRANSFER_CREDIT",
    "REQUIREMENT",
    "COURSE",
    "SECTION",
    "SECTION_MEETING",
    "PROGRAM",
    "UNKNOWN",
)
IMPORTED_RECORD_STATUSES = (
    "VALID",
    "VALID_WITH_WARNINGS",
    "AMBIGUOUS",
    "DUPLICATE",
    "INVALID",
    "UNSUPPORTED",
)
IMPORT_TARGET_ENTITY_TYPES = (
    "COURSE",
    "SECTION",
    "ACADEMIC_TERM",
    "REQUIREMENT_NODE",
    "PROGRAM_VERSION",
    "STUDENT_COURSE_ATTEMPT",
    "UNKNOWN",
)
IMPORT_MATCH_TYPES = (
    "EXACT_CODE",
    "NORMALIZED_CODE",
    "TITLE_SIMILARITY",
    "TERM_MATCH",
    "MANUAL_REQUIRED",
    "NO_MATCH",
)


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
        "data_import_runs",
        uuid_column("id"),
        uuid_column("student_profile_id"),
        sa.Column("import_type", enum(DATA_IMPORT_TYPES, "data_import_type"), nullable=False),
        sa.Column("status", enum(DATA_IMPORT_STATUSES, "data_import_status"), nullable=False),
        sa.Column(
            "storage_strategy",
            enum(DATA_IMPORT_STORAGE_STRATEGIES, "data_import_storage_strategy"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_mime_type", sa.String(length=120), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("parser_version", sa.String(length=80), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("valid_record_count", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("official_application_ready", sa.Boolean(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *source_columns(),
        *timestamp_columns(),
        sa.CheckConstraint("is_official = false", name="ck_data_import_runs_never_official"),
        sa.CheckConstraint(
            "source_type != 'OFFICIAL'",
            name="ck_data_import_runs_no_official_source",
        ),
        sa.CheckConstraint(
            "official_application_ready = false",
            name="ck_data_import_runs_preview_only",
        ),
        sa.CheckConstraint("length(file_name) > 0", name="ck_data_import_runs_file_name"),
        sa.CheckConstraint("length(file_mime_type) > 0", name="ck_data_import_runs_mime"),
        sa.CheckConstraint("file_size_bytes >= 0", name="ck_data_import_runs_file_size"),
        sa.CheckConstraint("length(file_sha256) = 64", name="ck_data_import_runs_sha256"),
        sa.CheckConstraint("length(parser_version) > 0", name="ck_data_import_runs_parser"),
        sa.CheckConstraint("record_count >= 0", name="ck_data_import_runs_record_count"),
        sa.CheckConstraint("valid_record_count >= 0", name="ck_data_import_runs_valid_count"),
        sa.CheckConstraint("warning_count >= 0", name="ck_data_import_runs_warning_count"),
        sa.CheckConstraint("error_count >= 0", name="ck_data_import_runs_error_count"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_data_import_runs_student",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_data_import_runs_student_created",
        "data_import_runs",
        ["student_profile_id", "created_at"],
    )
    op.create_index(
        "ix_data_import_runs_status_type",
        "data_import_runs",
        ["status", "import_type"],
    )

    op.create_table(
        "data_import_files",
        uuid_column("id"),
        uuid_column("data_import_run_id"),
        sa.Column(
            "storage_strategy",
            enum(DATA_IMPORT_STORAGE_STRATEGIES, "data_import_storage_strategy"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_mime_type", sa.String(length=120), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("content_preview", sa.String(length=500), nullable=True),
        sa.Column("external_object_reference", sa.String(length=500), nullable=True),
        created_at_column(),
        sa.CheckConstraint("length(file_name) > 0", name="ck_data_import_files_file_name"),
        sa.CheckConstraint("length(file_mime_type) > 0", name="ck_data_import_files_mime"),
        sa.CheckConstraint("file_size_bytes >= 0", name="ck_data_import_files_file_size"),
        sa.CheckConstraint("length(file_sha256) = 64", name="ck_data_import_files_sha256"),
        sa.CheckConstraint(
            "content_preview IS NULL OR length(content_preview) <= 500",
            name="ck_data_import_files_preview_length",
        ),
        sa.ForeignKeyConstraint(
            ["data_import_run_id"],
            ["data_import_runs.id"],
            name="fk_data_import_files_run",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("data_import_run_id", name="uq_data_import_files_run"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "imported_records",
        uuid_column("id"),
        uuid_column("data_import_run_id"),
        sa.Column(
            "record_type",
            enum(IMPORTED_RECORD_TYPES, "imported_record_type"),
            nullable=False,
        ),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            enum(IMPORTED_RECORD_STATUSES, "imported_record_status"),
            nullable=False,
        ),
        sa.Column("external_identifier", sa.String(length=255), nullable=True),
        sa.Column("raw_label", sa.String(length=500), nullable=False),
        sa.Column("normalized_payload", sa.JSON(), nullable=False),
        sa.Column("confidence_score", sa.Numeric(4, 2), nullable=False),
        created_at_column(),
        sa.CheckConstraint("row_number > 0", name="ck_imported_records_row_number"),
        sa.CheckConstraint("length(raw_label) > 0", name="ck_imported_records_raw_label"),
        sa.CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_imported_records_confidence",
        ),
        sa.ForeignKeyConstraint(
            ["data_import_run_id"],
            ["data_import_runs.id"],
            name="fk_imported_records_run",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "data_import_run_id",
            "row_number",
            name="uq_imported_records_run_row",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_imported_records_run_status",
        "imported_records",
        ["data_import_run_id", "status"],
    )

    op.create_table(
        "import_mapping_candidates",
        uuid_column("id"),
        uuid_column("imported_record_id"),
        sa.Column(
            "target_entity_type",
            enum(IMPORT_TARGET_ENTITY_TYPES, "import_target_entity_type"),
            nullable=False,
        ),
        uuid_column("target_entity_id", nullable=True),
        sa.Column("match_type", enum(IMPORT_MATCH_TYPES, "import_match_type"), nullable=False),
        sa.Column("confidence_score", sa.Numeric(4, 2), nullable=False),
        sa.Column("is_selected", sa.Boolean(), nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        created_at_column(),
        sa.CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_import_mapping_candidates_confidence",
        ),
        sa.CheckConstraint(
            "length(reason_code) > 0",
            name="ck_import_mapping_candidates_reason",
        ),
        sa.CheckConstraint(
            "length(explanation) > 0",
            name="ck_import_mapping_candidates_explained",
        ),
        sa.ForeignKeyConstraint(
            ["imported_record_id"],
            ["imported_records.id"],
            name="fk_import_mapping_candidates_record",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_import_mapping_candidates_record_score",
        "import_mapping_candidates",
        ["imported_record_id", "confidence_score"],
    )

    op.create_table(
        "import_validation_warnings",
        uuid_column("id"),
        uuid_column("data_import_run_id"),
        uuid_column("imported_record_id", nullable=True),
        sa.Column("warning_code", sa.String(length=80), nullable=False),
        sa.Column(
            "severity",
            enum(AUDIT_WARNING_SEVERITIES, "audit_warning_severity"),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("requires_advisor_confirmation", sa.Boolean(), nullable=False),
        created_at_column(),
        sa.CheckConstraint("length(warning_code) > 0", name="ck_import_warnings_code"),
        sa.CheckConstraint("length(message) > 0", name="ck_import_warnings_message"),
        sa.ForeignKeyConstraint(
            ["data_import_run_id"],
            ["data_import_runs.id"],
            name="fk_import_validation_warnings_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["imported_record_id"],
            ["imported_records.id"],
            name="fk_import_validation_warnings_record",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_import_warnings_run_severity",
        "import_validation_warnings",
        ["data_import_run_id", "severity"],
    )

    op.create_table(
        "import_preview_summaries",
        uuid_column("id"),
        uuid_column("data_import_run_id"),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("valid_record_count", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("official_application_ready", sa.Boolean(), nullable=False),
        sa.Column("summary_payload", sa.JSON(), nullable=False),
        created_at_column(),
        sa.CheckConstraint("record_count >= 0", name="ck_import_previews_record_count"),
        sa.CheckConstraint("valid_record_count >= 0", name="ck_import_previews_valid_count"),
        sa.CheckConstraint("warning_count >= 0", name="ck_import_previews_warning_count"),
        sa.CheckConstraint("error_count >= 0", name="ck_import_previews_error_count"),
        sa.CheckConstraint(
            "official_application_ready = false",
            name="ck_import_previews_preview_only",
        ),
        sa.ForeignKeyConstraint(
            ["data_import_run_id"],
            ["data_import_runs.id"],
            name="fk_import_preview_summaries_run",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("data_import_run_id", name="uq_import_previews_run"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("import_preview_summaries")
    op.drop_index("ix_import_warnings_run_severity", table_name="import_validation_warnings")
    op.drop_table("import_validation_warnings")
    op.drop_index(
        "ix_import_mapping_candidates_record_score",
        table_name="import_mapping_candidates",
    )
    op.drop_table("import_mapping_candidates")
    op.drop_index("ix_imported_records_run_status", table_name="imported_records")
    op.drop_table("imported_records")
    op.drop_table("data_import_files")
    op.drop_index("ix_data_import_runs_status_type", table_name="data_import_runs")
    op.drop_index("ix_data_import_runs_student_created", table_name="data_import_runs")
    op.drop_table("data_import_runs")
