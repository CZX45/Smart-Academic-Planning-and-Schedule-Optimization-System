"""create read-only section monitoring tables

Revision ID: 20260701_0013
Revises: 20260701_0012
Create Date: 2026-07-01
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260701_0013"
down_revision: str | None = "20260701_0012"
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
AUDIT_WARNING_SEVERITIES = ("INFO", "WARNING", "ERROR")
SECTION_MONITOR_ALERT_TYPES = (
    "STATUS_CHANGED",
    "SEATS_CHANGED",
    "SECTION_OPENED",
    "SECTION_CLOSED",
    "WAITLIST_CHANGED",
    "MEETING_TIME_CHANGED",
    "INSTRUCTOR_CHANGED",
    "LOCATION_CHANGED",
    "UNKNOWN_CHANGE",
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


def source_metadata_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column("source_type", enum(SOURCE_TYPES, "source_type"), nullable=False),
        sa.Column("is_official", sa.Boolean(), nullable=False),
        sa.Column("source_reference", sa.String(length=500), nullable=True),
        sa.Column("source_retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_confidence", sa.String(length=80), nullable=True),
    ]


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
        "section_monitor_targets",
        uuid_column("id"),
        uuid_column("student_profile_id"),
        sa.Column("course_code", sa.String(length=40), nullable=False),
        sa.Column("section_code", sa.String(length=40), nullable=False),
        sa.Column("term", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("instructor", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_advisory", sa.Boolean(), nullable=False),
        *source_metadata_columns(),
        *timestamp_columns(),
        sa.CheckConstraint("length(course_code) > 0", name="ck_section_monitor_targets_course"),
        sa.CheckConstraint("length(section_code) > 0", name="ck_section_monitor_targets_section"),
        sa.CheckConstraint("length(term) > 0", name="ck_section_monitor_targets_term"),
        sa.CheckConstraint("is_official = false", name="ck_section_monitor_targets_never_official"),
        sa.CheckConstraint(
            "source_type != 'OFFICIAL'",
            name="ck_section_monitor_targets_no_official_source",
        ),
        sa.CheckConstraint("is_advisory = true", name="ck_section_monitor_targets_advisory"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_section_monitor_targets_student",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "student_profile_id",
            "course_code",
            "section_code",
            "term",
            name="uq_section_monitor_targets_student_section_term",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_section_monitor_targets_student_active",
        "section_monitor_targets",
        ["student_profile_id", "is_active", "created_at"],
    )

    op.create_table(
        "section_monitor_snapshots",
        uuid_column("id"),
        uuid_column("student_profile_id"),
        uuid_column("target_id", nullable=True),
        uuid_column("data_import_id", nullable=True),
        sa.Column("course_code", sa.String(length=40), nullable=False),
        sa.Column("section_code", sa.String(length=40), nullable=False),
        sa.Column("term", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=True),
        sa.Column("seats_available", sa.Integer(), nullable=True),
        sa.Column("seats_capacity", sa.Integer(), nullable=True),
        sa.Column("waitlist_available", sa.Integer(), nullable=True),
        sa.Column("waitlist_capacity", sa.Integer(), nullable=True),
        sa.Column("meeting_days", sa.String(length=80), nullable=True),
        sa.Column("meeting_time", sa.String(length=120), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("instructor", sa.String(length=255), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        *source_metadata_columns(),
        created_at_column(),
        sa.CheckConstraint("length(course_code) > 0", name="ck_section_monitor_snapshots_course"),
        sa.CheckConstraint("length(section_code) > 0", name="ck_section_monitor_snapshots_section"),
        sa.CheckConstraint("length(term) > 0", name="ck_section_monitor_snapshots_term"),
        sa.CheckConstraint("length(snapshot_hash) > 0", name="ck_section_monitor_snapshots_hash"),
        sa.CheckConstraint(
            "seats_available IS NULL OR seats_available >= 0",
            name="ck_section_monitor_snapshots_seats_available",
        ),
        sa.CheckConstraint(
            "seats_capacity IS NULL OR seats_capacity >= 0",
            name="ck_section_monitor_snapshots_seats_capacity",
        ),
        sa.CheckConstraint(
            "waitlist_available IS NULL OR waitlist_available >= 0",
            name="ck_section_monitor_snapshots_waitlist_available",
        ),
        sa.CheckConstraint(
            "waitlist_capacity IS NULL OR waitlist_capacity >= 0",
            name="ck_section_monitor_snapshots_waitlist_capacity",
        ),
        sa.CheckConstraint(
            "is_official = false", name="ck_section_monitor_snapshots_never_official"
        ),
        sa.CheckConstraint(
            "source_type != 'OFFICIAL'",
            name="ck_section_monitor_snapshots_no_official_source",
        ),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_section_monitor_snapshots_student",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["section_monitor_targets.id"],
            name="fk_section_monitor_snapshots_target",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["data_import_id"],
            ["data_import_runs.id"],
            name="fk_section_monitor_snapshots_data_import",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "student_profile_id",
            "course_code",
            "section_code",
            "term",
            "snapshot_hash",
            name="uq_section_monitor_snapshots_student_section_hash",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_section_monitor_snapshots_lookup",
        "section_monitor_snapshots",
        ["student_profile_id", "course_code", "section_code", "term", "created_at"],
    )
    op.create_index(
        "ix_section_monitor_snapshots_target_created",
        "section_monitor_snapshots",
        ["target_id", "created_at"],
    )

    op.create_table(
        "section_monitor_alerts",
        uuid_column("id"),
        uuid_column("target_id"),
        uuid_column("previous_snapshot_id"),
        uuid_column("current_snapshot_id"),
        sa.Column(
            "alert_type",
            enum(SECTION_MONITOR_ALERT_TYPES, "section_monitor_alert_type"),
            nullable=False,
        ),
        sa.Column(
            "severity",
            enum(AUDIT_WARNING_SEVERITIES, "audit_warning_severity"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(length=80), nullable=False),
        sa.Column("previous_value", sa.String(length=255), nullable=True),
        sa.Column("current_value", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_acknowledged", sa.Boolean(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_advisory", sa.Boolean(), nullable=False),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False),
        created_at_column(),
        sa.CheckConstraint("length(field_name) > 0", name="ck_section_monitor_alerts_field_name"),
        sa.CheckConstraint("length(message) > 0", name="ck_section_monitor_alerts_message"),
        sa.CheckConstraint("is_advisory = true", name="ck_section_monitor_alerts_advisory"),
        sa.CheckConstraint(
            "requires_manual_review = true",
            name="ck_section_monitor_alerts_manual_review",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["section_monitor_targets.id"],
            name="fk_section_monitor_alerts_target",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["previous_snapshot_id"],
            ["section_monitor_snapshots.id"],
            name="fk_section_monitor_alerts_previous_snapshot",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["current_snapshot_id"],
            ["section_monitor_snapshots.id"],
            name="fk_section_monitor_alerts_current_snapshot",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "previous_snapshot_id",
            "current_snapshot_id",
            "alert_type",
            "field_name",
            name="uq_section_monitor_alerts_snapshot_type_field",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_section_monitor_alerts_target_ack",
        "section_monitor_alerts",
        ["target_id", "is_acknowledged"],
    )
    op.create_index(
        "ix_section_monitor_alerts_created",
        "section_monitor_alerts",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_section_monitor_alerts_created", table_name="section_monitor_alerts")
    op.drop_index("ix_section_monitor_alerts_target_ack", table_name="section_monitor_alerts")
    op.drop_table("section_monitor_alerts")
    op.drop_index(
        "ix_section_monitor_snapshots_target_created",
        table_name="section_monitor_snapshots",
    )
    op.drop_index("ix_section_monitor_snapshots_lookup", table_name="section_monitor_snapshots")
    op.drop_table("section_monitor_snapshots")
    op.drop_index(
        "ix_section_monitor_targets_student_active",
        table_name="section_monitor_targets",
    )
    op.drop_table("section_monitor_targets")
