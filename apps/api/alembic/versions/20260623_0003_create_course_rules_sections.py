"""create course rules and sections

Revision ID: 20260623_0003
Revises: 20260622_0002
Create Date: 2026-06-23
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260623_0003"
down_revision: str | None = "20260622_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE_TYPES = ("MOCK", "OFFICIAL", "IMPORTED", "STUDENT_PROVIDED", "INFERRED")
TERM_TYPES = ("FALL", "SPRING", "SUMMER", "WINTER", "OTHER")
FREQUENCY_TYPES = ("EVERY_TERM", "ANNUAL", "ALTERNATING_YEARS", "IRREGULAR", "UNKNOWN")
COURSE_RULE_TYPES = (
    "PREREQUISITE",
    "COREQUISITE",
    "REGISTRATION_RESTRICTION",
    "REPEAT_RESTRICTION",
    "PERMISSION",
)
COURSE_RULE_EXPRESSION_NODE_TYPES = (
    "AND",
    "OR",
    "NOT",
    "COMPLETED_COURSE",
    "MINIMUM_GRADE",
    "MINIMUM_COMPLETED_CREDITS",
    "CLASS_STANDING",
    "MAJOR_RESTRICTION",
    "MINOR_RESTRICTION",
    "PROGRAM_RESTRICTION",
    "CAMPUS_RESTRICTION",
    "PERMISSION_REQUIRED",
)
SECTION_STATUSES = ("PLANNED", "OPEN", "CLOSED", "WAITLIST", "CANCELLED", "COMPLETED", "UNKNOWN")
SECTION_MODALITIES = (
    "IN_PERSON",
    "ONLINE_SYNCHRONOUS",
    "ONLINE_ASYNCHRONOUS",
    "HYBRID",
    "ARRANGED",
    "UNKNOWN",
)
MEETING_TYPES = ("LECTURE", "LAB", "RECITATION", "SEMINAR", "EXAM", "OTHER")
DAYS_OF_WEEK = (
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
    "SUNDAY",
)


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


def source_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column("source_type", enum(SOURCE_TYPES, "source_type"), nullable=False),
        sa.Column("is_official", sa.Boolean(), nullable=False),
        sa.Column("source_reference", sa.String(length=500), nullable=True),
        sa.Column("source_retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_confidence", sa.String(length=80), nullable=True),
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


def mock_not_official(name: str) -> sa.CheckConstraint:
    return sa.CheckConstraint("is_official = false OR source_type != 'MOCK'", name=name)


def upgrade() -> None:
    op.create_table(
        "course_offering_patterns",
        uuid_column("id"),
        uuid_column("institution_id"),
        uuid_column("course_id"),
        uuid_column("campus_id"),
        sa.Column("term_type", enum(TERM_TYPES, "term_type"), nullable=False),
        sa.Column("frequency_type", enum(FREQUENCY_TYPES, "frequency_type"), nullable=False),
        uuid_column("effective_term_id"),
        uuid_column("expiration_term_id", nullable=True),
        sa.Column("confidence_level", sa.Numeric(4, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *source_columns(),
        sa.CheckConstraint(
            "confidence_level >= 0 AND confidence_level <= 1",
            name="ck_course_offering_patterns_confidence_range",
        ),
        sa.CheckConstraint(
            "expiration_term_id IS NULL OR expiration_term_id != effective_term_id",
            name="ck_course_offering_patterns_effective_expiration_distinct",
        ),
        mock_not_official("ck_course_offering_patterns_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_course_offering_patterns_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_course_offering_patterns_course_institution",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["campus_id", "institution_id"],
            ["campuses.id", "campuses.institution_id"],
            name="fk_course_offering_patterns_campus_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["effective_term_id", "institution_id"],
            ["academic_terms.id", "academic_terms.institution_id"],
            name="fk_course_offering_patterns_effective_term_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["expiration_term_id", "institution_id"],
            ["academic_terms.id", "academic_terms.institution_id"],
            name="fk_course_offering_patterns_expiration_term_institution",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_course_offering_patterns_open_range",
        "course_offering_patterns",
        ["course_id", "campus_id", "term_type", "effective_term_id"],
        unique=True,
        postgresql_where=sa.text("expiration_term_id IS NULL"),
        sqlite_where=sa.text("expiration_term_id IS NULL"),
    )
    op.create_index(
        "uq_course_offering_patterns_closed_range",
        "course_offering_patterns",
        ["course_id", "campus_id", "term_type", "effective_term_id", "expiration_term_id"],
        unique=True,
        postgresql_where=sa.text("expiration_term_id IS NOT NULL"),
        sqlite_where=sa.text("expiration_term_id IS NOT NULL"),
    )

    op.create_table(
        "sections",
        uuid_column("id"),
        uuid_column("institution_id"),
        uuid_column("course_id"),
        uuid_column("term_id"),
        uuid_column("campus_id"),
        sa.Column("section_code", sa.String(length=40), nullable=False),
        sa.Column("external_reference", sa.String(length=120), nullable=True),
        sa.Column("title_override", sa.String(length=255), nullable=True),
        sa.Column("credits", sa.Numeric(4, 1), nullable=True),
        sa.Column("status", enum(SECTION_STATUSES, "section_status"), nullable=False),
        sa.Column("modality", enum(SECTION_MODALITIES, "section_modality"), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("available_seats", sa.Integer(), nullable=True),
        sa.Column("waitlist_capacity", sa.Integer(), nullable=True),
        sa.Column("waitlist_available", sa.Integer(), nullable=True),
        sa.Column("instructor_display", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        *source_columns(),
        sa.CheckConstraint("length(section_code) > 0", name="ck_sections_code_not_empty"),
        sa.CheckConstraint(
            "credits IS NULL OR credits >= 0", name="ck_sections_credits_non_negative"
        ),
        sa.CheckConstraint(
            "capacity IS NULL OR capacity >= 0", name="ck_sections_capacity_non_negative"
        ),
        sa.CheckConstraint(
            "available_seats IS NULL OR available_seats >= 0",
            name="ck_sections_available_seats_non_negative",
        ),
        sa.CheckConstraint(
            "waitlist_capacity IS NULL OR waitlist_capacity >= 0",
            name="ck_sections_waitlist_capacity_non_negative",
        ),
        sa.CheckConstraint(
            "waitlist_available IS NULL OR waitlist_available >= 0",
            name="ck_sections_waitlist_available_non_negative",
        ),
        sa.CheckConstraint(
            "capacity IS NULL OR available_seats IS NULL OR available_seats <= capacity",
            name="ck_sections_available_not_above_capacity",
        ),
        sa.CheckConstraint(
            "waitlist_capacity IS NULL OR waitlist_available IS NULL "
            "OR waitlist_available <= waitlist_capacity",
            name="ck_sections_waitlist_available_not_above_capacity",
        ),
        mock_not_official("ck_sections_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_sections_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_sections_course_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["term_id", "institution_id"],
            ["academic_terms.id", "academic_terms.institution_id"],
            name="fk_sections_term_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["campus_id", "institution_id"],
            ["campuses.id", "campuses.institution_id"],
            name="fk_sections_campus_institution",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "id", "course_id", "institution_id", name="uq_sections_id_course_institution"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_sections_institution_term_course_code",
        "sections",
        ["institution_id", "term_id", "course_id", "section_code"],
        unique=True,
    )
    op.create_index(
        "ix_sections_term_status_modality",
        "sections",
        ["term_id", "status", "modality"],
    )
    op.create_index("ix_sections_course_term", "sections", ["course_id", "term_id"])

    op.create_table(
        "section_meetings",
        uuid_column("id"),
        uuid_column("section_id"),
        sa.Column("meeting_type", enum(MEETING_TYPES, "meeting_type"), nullable=False),
        sa.Column("day_of_week", enum(DAYS_OF_WEEK, "day_of_week"), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("building", sa.String(length=120), nullable=True),
        sa.Column("room", sa.String(length=120), nullable=True),
        sa.Column("timezone", sa.String(length=80), nullable=False),
        sa.Column("is_arranged", sa.Boolean(), nullable=False),
        sa.Column("is_online", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        *source_columns(),
        sa.CheckConstraint(
            "display_order >= 0",
            name="ck_section_meetings_display_order_non_negative",
        ),
        sa.CheckConstraint(
            "is_arranged = true OR is_online = true OR "
            "(day_of_week IS NOT NULL AND start_time IS NOT NULL AND end_time IS NOT NULL)",
            name="ck_section_meetings_fixed_meeting_has_time",
        ),
        sa.CheckConstraint(
            "start_time IS NULL OR end_time IS NULL OR end_time > start_time",
            name="ck_section_meetings_time_range",
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="ck_section_meetings_date_range",
        ),
        sa.CheckConstraint("length(timezone) > 0", name="ck_section_meetings_timezone_not_empty"),
        mock_not_official("ck_section_meetings_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
            name="fk_section_meetings_section",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_section_meetings_section_order",
        "section_meetings",
        ["section_id", "display_order"],
    )

    op.create_table(
        "course_rules",
        uuid_column("id"),
        uuid_column("institution_id"),
        uuid_column("course_id"),
        uuid_column("section_id", nullable=True),
        sa.Column("rule_type", enum(COURSE_RULE_TYPES, "course_rule_type"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        uuid_column("effective_term_id"),
        uuid_column("expiration_term_id", nullable=True),
        sa.Column("requires_manual_confirmation", sa.Boolean(), nullable=False),
        *source_columns(),
        sa.CheckConstraint("course_id IS NOT NULL", name="ck_course_rules_has_course_scope"),
        sa.CheckConstraint("length(name) > 0", name="ck_course_rules_name_not_empty"),
        sa.CheckConstraint(
            "expiration_term_id IS NULL OR expiration_term_id != effective_term_id",
            name="ck_course_rules_effective_expiration_distinct",
        ),
        mock_not_official("ck_course_rules_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_course_rules_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_course_rules_course_institution",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["section_id", "course_id", "institution_id"],
            ["sections.id", "sections.course_id", "sections.institution_id"],
            name="fk_course_rules_section_course_institution",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["effective_term_id", "institution_id"],
            ["academic_terms.id", "academic_terms.institution_id"],
            name="fk_course_rules_effective_term_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["expiration_term_id", "institution_id"],
            ["academic_terms.id", "academic_terms.institution_id"],
            name="fk_course_rules_expiration_term_institution",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("id", "institution_id", name="uq_course_rules_id_institution"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_course_rules_course_scope",
        "course_rules",
        ["institution_id", "course_id", "rule_type", "name", "effective_term_id"],
        unique=True,
        postgresql_where=sa.text("section_id IS NULL"),
        sqlite_where=sa.text("section_id IS NULL"),
    )
    op.create_index(
        "uq_course_rules_section_scope",
        "course_rules",
        ["section_id", "rule_type", "name", "effective_term_id"],
        unique=True,
        postgresql_where=sa.text("section_id IS NOT NULL"),
        sqlite_where=sa.text("section_id IS NOT NULL"),
    )

    op.create_table(
        "course_rule_expressions",
        uuid_column("id"),
        uuid_column("institution_id"),
        uuid_column("course_rule_id"),
        uuid_column("parent_id", nullable=True),
        sa.Column(
            "node_type",
            enum(COURSE_RULE_EXPRESSION_NODE_TYPES, "course_rule_expression_node_type"),
            nullable=False,
        ),
        sa.Column("display_order", sa.Integer(), nullable=False),
        uuid_column("referenced_course_id", nullable=True),
        sa.Column("minimum_grade", sa.String(length=8), nullable=True),
        sa.Column("minimum_completed_credits", sa.Numeric(5, 1), nullable=True),
        sa.Column("class_standing", sa.String(length=40), nullable=True),
        uuid_column("referenced_program_id", nullable=True),
        uuid_column("referenced_campus_id", nullable=True),
        sa.Column("permission_type", sa.String(length=80), nullable=True),
        sa.Column("text_value", sa.Text(), nullable=True),
        *source_columns(),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id != id",
            name="ck_course_rule_expressions_not_self_parent",
        ),
        sa.CheckConstraint(
            "display_order >= 0",
            name="ck_course_rule_expressions_display_order_non_negative",
        ),
        sa.CheckConstraint(
            "minimum_completed_credits IS NULL OR minimum_completed_credits >= 0",
            name="ck_course_rule_expressions_minimum_completed_credits_non_negative",
        ),
        sa.CheckConstraint(
            "node_type NOT IN ('AND', 'OR', 'NOT') OR "
            "(referenced_course_id IS NULL AND minimum_grade IS NULL "
            "AND minimum_completed_credits IS NULL AND class_standing IS NULL "
            "AND referenced_program_id IS NULL AND referenced_campus_id IS NULL "
            "AND permission_type IS NULL)",
            name="ck_course_rule_expressions_operator_has_no_operand",
        ),
        sa.CheckConstraint(
            "node_type != 'COMPLETED_COURSE' OR referenced_course_id IS NOT NULL",
            name="ck_course_rule_expressions_completed_course_operand",
        ),
        sa.CheckConstraint(
            "node_type != 'MINIMUM_GRADE' OR "
            "(referenced_course_id IS NOT NULL AND minimum_grade IS NOT NULL)",
            name="ck_course_rule_expressions_minimum_grade_operand",
        ),
        sa.CheckConstraint(
            "node_type != 'MINIMUM_COMPLETED_CREDITS' OR minimum_completed_credits IS NOT NULL",
            name="ck_course_rule_expressions_minimum_credits_operand",
        ),
        sa.CheckConstraint(
            "node_type != 'CLASS_STANDING' OR class_standing IS NOT NULL",
            name="ck_course_rule_expressions_class_standing_operand",
        ),
        sa.CheckConstraint(
            "node_type NOT IN ('MAJOR_RESTRICTION', 'MINOR_RESTRICTION', "
            "'PROGRAM_RESTRICTION') OR referenced_program_id IS NOT NULL",
            name="ck_course_rule_expressions_program_operand",
        ),
        sa.CheckConstraint(
            "node_type != 'CAMPUS_RESTRICTION' OR referenced_campus_id IS NOT NULL",
            name="ck_course_rule_expressions_campus_operand",
        ),
        sa.CheckConstraint(
            "node_type != 'PERMISSION_REQUIRED' OR permission_type IS NOT NULL",
            name="ck_course_rule_expressions_permission_operand",
        ),
        mock_not_official("ck_course_rule_expressions_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["course_rule_id", "institution_id"],
            ["course_rules.id", "course_rules.institution_id"],
            name="fk_course_rule_expressions_rule_institution",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id", "course_rule_id", "institution_id"],
            [
                "course_rule_expressions.id",
                "course_rule_expressions.course_rule_id",
                "course_rule_expressions.institution_id",
            ],
            name="fk_course_rule_expressions_parent_same_rule",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["referenced_course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_course_rule_expressions_referenced_course_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["referenced_program_id", "institution_id"],
            ["academic_programs.id", "academic_programs.institution_id"],
            name="fk_course_rule_expressions_referenced_program_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["referenced_campus_id", "institution_id"],
            ["campuses.id", "campuses.institution_id"],
            name="fk_course_rule_expressions_referenced_campus_institution",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "id",
            "course_rule_id",
            "institution_id",
            name="uq_course_rule_expressions_id_rule_institution",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_course_rule_expressions_single_root",
        "course_rule_expressions",
        ["course_rule_id"],
        unique=True,
        postgresql_where=sa.text("parent_id IS NULL"),
        sqlite_where=sa.text("parent_id IS NULL"),
    )
    op.create_index(
        "ix_course_rule_expressions_rule_parent_order",
        "course_rule_expressions",
        ["course_rule_id", "parent_id", "display_order"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_course_rule_expressions_rule_parent_order",
        table_name="course_rule_expressions",
    )
    op.drop_index("uq_course_rule_expressions_single_root", table_name="course_rule_expressions")
    op.drop_table("course_rule_expressions")
    op.drop_index("uq_course_rules_section_scope", table_name="course_rules")
    op.drop_index("uq_course_rules_course_scope", table_name="course_rules")
    op.drop_table("course_rules")
    op.drop_index("ix_section_meetings_section_order", table_name="section_meetings")
    op.drop_table("section_meetings")
    op.drop_index("ix_sections_course_term", table_name="sections")
    op.drop_index("ix_sections_term_status_modality", table_name="sections")
    op.drop_index("uq_sections_institution_term_course_code", table_name="sections")
    op.drop_table("sections")
    op.drop_index(
        "uq_course_offering_patterns_closed_range",
        table_name="course_offering_patterns",
    )
    op.drop_index(
        "uq_course_offering_patterns_open_range",
        table_name="course_offering_patterns",
    )
    op.drop_table("course_offering_patterns")
