"""create academic domain

Revision ID: 20260622_0002
Revises: 20260622_0001
Create Date: 2026-06-22
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260622_0002"
down_revision: str | None = "20260622_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE_TYPES = ("MOCK", "OFFICIAL", "IMPORTED", "STUDENT_PROVIDED", "INFERRED")
PROGRAM_TYPES = ("MAJOR", "MINOR", "CERTIFICATE", "CONCENTRATION")
DEGREE_LEVELS = ("BACHELORS", "MASTERS", "DOCTORATE", "CERTIFICATE")
REQUIREMENT_TYPES = (
    "GROUP",
    "REQUIRED_COURSE",
    "ALL_OF",
    "ANY_OF",
    "CHOOSE_N",
    "MINIMUM_CREDITS",
    "MINIMUM_COURSES",
    "MINIMUM_GRADE",
    "COURSE_LEVEL",
    "RESIDENCY",
    "TOTAL_CREDITS",
    "CAPSTONE",
    "EXCLUSION",
)
STUDENT_PROGRAM_TYPES = ("PRIMARY_MAJOR", "SECOND_MAJOR", "MINOR", "CERTIFICATE")
STUDENT_PROGRAM_STATUSES = ("ACTIVE", "INACTIVE", "COMPLETED")
COURSE_ATTEMPT_STATUSES = (
    "COMPLETED",
    "IN_PROGRESS",
    "PLANNED",
    "FAILED",
    "WITHDRAWN",
    "TRANSFERRED",
)
APPROVAL_STATUSES = ("PENDING", "APPROVED", "REJECTED")


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
        "institutions",
        uuid_column("id"),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column("timezone", sa.String(length=80), nullable=False),
        *source_columns(),
        sa.CheckConstraint("length(code) > 0", name="ck_institutions_code_not_empty"),
        sa.CheckConstraint("length(name) > 0", name="ck_institutions_name_not_empty"),
        mock_not_official("ck_institutions_mock_not_official"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_institutions_code", "institutions", ["code"], unique=True)

    op.create_table(
        "campuses",
        uuid_column("id"),
        uuid_column("institution_id"),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        *source_columns(),
        sa.CheckConstraint("length(code) > 0", name="ck_campuses_code_not_empty"),
        sa.CheckConstraint("length(name) > 0", name="ck_campuses_name_not_empty"),
        mock_not_official("ck_campuses_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_campuses_institution",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_campuses_institution_code",
        "campuses",
        ["institution_id", "code"],
        unique=True,
    )
    op.create_index(
        "uq_campuses_id_institution",
        "campuses",
        ["id", "institution_id"],
        unique=True,
    )

    op.create_table(
        "academic_terms",
        uuid_column("id"),
        uuid_column("institution_id"),
        uuid_column("campus_id"),
        sa.Column("term_code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        *source_columns(),
        sa.CheckConstraint("length(term_code) > 0", name="ck_academic_terms_code_not_empty"),
        sa.CheckConstraint("starts_on <= ends_on", name="ck_academic_terms_date_range"),
        mock_not_official("ck_academic_terms_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_academic_terms_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["campus_id", "institution_id"],
            ["campuses.id", "campuses.institution_id"],
            name="fk_academic_terms_campus_institution",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_academic_terms_institution_code",
        "academic_terms",
        ["institution_id", "term_code"],
        unique=True,
    )
    op.create_index(
        "uq_academic_terms_id_institution",
        "academic_terms",
        ["id", "institution_id"],
        unique=True,
    )

    op.create_table(
        "academic_programs",
        uuid_column("id"),
        uuid_column("institution_id"),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("program_type", enum(PROGRAM_TYPES, "program_type"), nullable=False),
        sa.Column("degree_level", enum(DEGREE_LEVELS, "degree_level"), nullable=False),
        *source_columns(),
        sa.CheckConstraint("length(code) > 0", name="ck_academic_programs_code_not_empty"),
        sa.CheckConstraint("length(name) > 0", name="ck_academic_programs_name_not_empty"),
        mock_not_official("ck_academic_programs_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_academic_programs_institution",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_academic_programs_institution_code",
        "academic_programs",
        ["institution_id", "code"],
        unique=True,
    )
    op.create_index(
        "uq_academic_programs_id_institution",
        "academic_programs",
        ["id", "institution_id"],
        unique=True,
    )

    op.create_table(
        "program_versions",
        uuid_column("id"),
        uuid_column("institution_id"),
        uuid_column("program_id"),
        uuid_column("campus_id"),
        uuid_column("effective_term_id"),
        sa.Column("catalog_year", sa.String(length=32), nullable=False),
        sa.Column("version_label", sa.String(length=255), nullable=False),
        sa.Column("total_credits_required", sa.Numeric(5, 1), nullable=False),
        *source_columns(),
        sa.CheckConstraint(
            "total_credits_required > 0",
            name="ck_program_versions_total_credits_positive",
        ),
        sa.CheckConstraint(
            "length(catalog_year) > 0",
            name="ck_program_versions_catalog_year_not_empty",
        ),
        mock_not_official("ck_program_versions_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["program_id", "institution_id"],
            ["academic_programs.id", "academic_programs.institution_id"],
            name="fk_program_versions_program_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["campus_id", "institution_id"],
            ["campuses.id", "campuses.institution_id"],
            name="fk_program_versions_campus_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["effective_term_id", "institution_id"],
            ["academic_terms.id", "academic_terms.institution_id"],
            name="fk_program_versions_effective_term_institution",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_program_versions_program_campus_catalog_term",
        "program_versions",
        ["program_id", "campus_id", "catalog_year", "effective_term_id"],
        unique=True,
    )
    op.create_index(
        "uq_program_versions_id_institution",
        "program_versions",
        ["id", "institution_id"],
        unique=True,
    )

    op.create_table(
        "courses",
        uuid_column("id"),
        uuid_column("institution_id"),
        sa.Column("subject_code", sa.String(length=16), nullable=False),
        sa.Column("course_number", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("credits_min", sa.Numeric(4, 1), nullable=False),
        sa.Column("credits_max", sa.Numeric(4, 1), nullable=False),
        sa.Column("course_level", sa.Integer(), nullable=False),
        sa.Column("repeatable", sa.Boolean(), nullable=False),
        *source_columns(),
        sa.CheckConstraint("credits_min > 0", name="ck_courses_credits_min_positive"),
        sa.CheckConstraint("credits_max >= credits_min", name="ck_courses_credit_range"),
        sa.CheckConstraint("course_level >= 0", name="ck_courses_level_non_negative"),
        sa.CheckConstraint("length(subject_code) > 0", name="ck_courses_subject_not_empty"),
        sa.CheckConstraint("length(course_number) > 0", name="ck_courses_number_not_empty"),
        mock_not_official("ck_courses_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_courses_institution",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_courses_institution_subject_number",
        "courses",
        ["institution_id", "subject_code", "course_number"],
        unique=True,
    )
    op.create_index(
        "uq_courses_id_institution",
        "courses",
        ["id", "institution_id"],
        unique=True,
    )

    op.create_table(
        "course_equivalencies",
        uuid_column("id"),
        uuid_column("institution_id"),
        uuid_column("source_course_id"),
        uuid_column("equivalent_course_id"),
        sa.Column("note", sa.Text(), nullable=True),
        *source_columns(),
        sa.CheckConstraint(
            "source_course_id != equivalent_course_id",
            name="ck_course_equivalencies_not_self",
        ),
        mock_not_official("ck_course_equivalencies_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_course_equivalencies_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_course_equivalencies_source_course_institution",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["equivalent_course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_course_equivalencies_equivalent_course_institution",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_course_equivalencies_source_equivalent",
        "course_equivalencies",
        ["source_course_id", "equivalent_course_id"],
        unique=True,
    )

    op.create_table(
        "requirement_nodes",
        uuid_column("id"),
        uuid_column("institution_id"),
        uuid_column("program_version_id"),
        uuid_column("parent_id", nullable=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "requirement_type",
            enum(REQUIREMENT_TYPES, "requirement_type"),
            nullable=False,
        ),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("minimum_credits", sa.Numeric(5, 1), nullable=True),
        sa.Column("minimum_courses", sa.Integer(), nullable=True),
        sa.Column("choose_n", sa.Integer(), nullable=True),
        sa.Column("minimum_grade", sa.String(length=8), nullable=True),
        sa.Column("minimum_course_level", sa.Integer(), nullable=True),
        sa.Column("minimum_residency_credits", sa.Numeric(5, 1), nullable=True),
        sa.Column("allows_overlap", sa.Boolean(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        *source_columns(),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id != id",
            name="ck_requirement_nodes_not_self_parent",
        ),
        sa.CheckConstraint(
            "display_order >= 0",
            name="ck_requirement_nodes_display_order_non_negative",
        ),
        sa.CheckConstraint(
            "minimum_credits IS NULL OR minimum_credits >= 0",
            name="ck_requirement_nodes_minimum_credits_non_negative",
        ),
        sa.CheckConstraint(
            "minimum_courses IS NULL OR minimum_courses >= 0",
            name="ck_requirement_nodes_minimum_courses_non_negative",
        ),
        sa.CheckConstraint(
            "choose_n IS NULL OR choose_n > 0",
            name="ck_requirement_nodes_choose_n_positive",
        ),
        sa.CheckConstraint(
            "minimum_course_level IS NULL OR minimum_course_level >= 0",
            name="ck_requirement_nodes_minimum_course_level_non_negative",
        ),
        sa.CheckConstraint(
            "minimum_residency_credits IS NULL OR minimum_residency_credits >= 0",
            name="ck_requirement_nodes_minimum_residency_credits_non_negative",
        ),
        mock_not_official("ck_requirement_nodes_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["program_version_id", "institution_id"],
            ["program_versions.id", "program_versions.institution_id"],
            name="fk_requirement_nodes_program_version_institution",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id", "program_version_id", "institution_id"],
            [
                "requirement_nodes.id",
                "requirement_nodes.program_version_id",
                "requirement_nodes.institution_id",
            ],
            name="fk_requirement_nodes_parent_same_program_version",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_requirement_nodes_id_program_institution",
        "requirement_nodes",
        ["id", "program_version_id", "institution_id"],
        unique=True,
    )
    op.create_index(
        "uq_requirement_nodes_program_code",
        "requirement_nodes",
        ["program_version_id", "code"],
        unique=True,
    )

    op.create_table(
        "requirement_course_options",
        uuid_column("id"),
        uuid_column("institution_id"),
        uuid_column("program_version_id"),
        uuid_column("requirement_node_id"),
        uuid_column("course_id"),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("minimum_grade", sa.String(length=8), nullable=True),
        sa.Column("credits_override", sa.Numeric(4, 1), nullable=True),
        *source_columns(),
        sa.CheckConstraint(
            "display_order >= 0",
            name="ck_requirement_course_options_display_order_non_negative",
        ),
        sa.CheckConstraint(
            "credits_override IS NULL OR credits_override > 0",
            name="ck_requirement_course_options_credits_override_positive",
        ),
        mock_not_official("ck_requirement_course_options_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["program_version_id", "institution_id"],
            ["program_versions.id", "program_versions.institution_id"],
            name="fk_requirement_course_options_program_version_institution",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_node_id", "program_version_id", "institution_id"],
            [
                "requirement_nodes.id",
                "requirement_nodes.program_version_id",
                "requirement_nodes.institution_id",
            ],
            name="fk_requirement_course_options_node_program_institution",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_requirement_course_options_course_institution",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_requirement_course_options_node_course",
        "requirement_course_options",
        ["requirement_node_id", "course_id"],
        unique=True,
    )

    op.create_table(
        "student_profiles",
        uuid_column("id"),
        uuid_column("home_institution_id"),
        uuid_column("home_campus_id"),
        uuid_column("expected_graduation_term_id", nullable=True),
        sa.Column("external_ref", sa.String(length=120), nullable=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("class_standing", sa.String(length=40), nullable=True),
        *source_columns(),
        mock_not_official("ck_student_profiles_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["home_institution_id"],
            ["institutions.id"],
            name="fk_student_profiles_home_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["home_campus_id", "home_institution_id"],
            ["campuses.id", "campuses.institution_id"],
            name="fk_student_profiles_home_campus_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["expected_graduation_term_id", "home_institution_id"],
            ["academic_terms.id", "academic_terms.institution_id"],
            name="fk_student_profiles_expected_term_institution",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_student_profiles_institution_external_ref",
        "student_profiles",
        ["home_institution_id", "external_ref"],
        unique=True,
    )

    op.create_table(
        "student_academic_programs",
        uuid_column("id"),
        uuid_column("student_profile_id"),
        uuid_column("program_version_id"),
        sa.Column(
            "program_type",
            enum(STUDENT_PROGRAM_TYPES, "student_program_type"),
            nullable=False,
        ),
        sa.Column(
            "status",
            enum(STUDENT_PROGRAM_STATUSES, "student_program_status"),
            nullable=False,
        ),
        sa.Column("declared_on", sa.Date(), nullable=True),
        *source_columns(),
        mock_not_official("ck_student_academic_programs_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_student_academic_programs_student",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["program_version_id"],
            ["program_versions.id"],
            name="fk_student_academic_programs_program_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_student_academic_programs_active_primary_major",
        "student_academic_programs",
        ["student_profile_id"],
        unique=True,
        postgresql_where=sa.text("program_type = 'PRIMARY_MAJOR' AND status = 'ACTIVE'"),
    )
    op.create_index(
        "uq_student_academic_programs_student_program_type",
        "student_academic_programs",
        ["student_profile_id", "program_version_id", "program_type"],
        unique=True,
    )

    op.create_table(
        "student_course_attempts",
        uuid_column("id"),
        uuid_column("student_profile_id"),
        uuid_column("course_id"),
        uuid_column("term_id"),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            enum(COURSE_ATTEMPT_STATUSES, "student_course_attempt_status"),
            nullable=False,
        ),
        sa.Column("grade", sa.String(length=8), nullable=True),
        sa.Column("credits_attempted", sa.Numeric(4, 1), nullable=False),
        sa.Column("credits_earned", sa.Numeric(4, 1), nullable=False),
        sa.Column("is_repeat", sa.Boolean(), nullable=False),
        *source_columns(),
        sa.CheckConstraint(
            "attempt_number > 0",
            name="ck_student_course_attempts_attempt_positive",
        ),
        sa.CheckConstraint(
            "credits_attempted >= 0",
            name="ck_student_course_attempts_attempted_non_negative",
        ),
        sa.CheckConstraint(
            "credits_earned >= 0",
            name="ck_student_course_attempts_earned_non_negative",
        ),
        sa.CheckConstraint(
            "credits_earned <= credits_attempted",
            name="ck_student_course_attempts_earned_not_above_attempted",
        ),
        mock_not_official("ck_student_course_attempts_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_student_course_attempts_student",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_student_course_attempts_course",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["term_id"],
            ["academic_terms.id"],
            name="fk_student_course_attempts_term",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_student_course_attempts_student_course_attempt",
        "student_course_attempts",
        ["student_profile_id", "course_id", "attempt_number"],
        unique=True,
    )

    op.create_table(
        "transfer_credits",
        uuid_column("id"),
        uuid_column("student_profile_id"),
        uuid_column("equivalent_course_id", nullable=True),
        sa.Column("source_institution_name", sa.String(length=255), nullable=False),
        sa.Column("source_course_code", sa.String(length=80), nullable=False),
        sa.Column("credits_earned", sa.Numeric(4, 1), nullable=False),
        sa.Column("grade", sa.String(length=8), nullable=True),
        sa.Column("status", enum(APPROVAL_STATUSES, "approval_status"), nullable=False),
        *source_columns(),
        sa.CheckConstraint("credits_earned > 0", name="ck_transfer_credits_credits_positive"),
        mock_not_official("ck_transfer_credits_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_transfer_credits_student",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["equivalent_course_id"],
            ["courses.id"],
            name="fk_transfer_credits_equivalent_course",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "course_waivers",
        uuid_column("id"),
        uuid_column("institution_id"),
        uuid_column("student_profile_id"),
        uuid_column("program_version_id"),
        uuid_column("requirement_node_id", nullable=True),
        sa.Column("status", enum(APPROVAL_STATUSES, "approval_status"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        *source_columns(),
        mock_not_official("ck_course_waivers_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_course_waivers_student",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["program_version_id", "institution_id"],
            ["program_versions.id", "program_versions.institution_id"],
            name="fk_course_waivers_program_version_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_node_id", "program_version_id", "institution_id"],
            [
                "requirement_nodes.id",
                "requirement_nodes.program_version_id",
                "requirement_nodes.institution_id",
            ],
            name="fk_course_waivers_requirement_node_program_institution",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "course_substitutions",
        uuid_column("id"),
        uuid_column("institution_id"),
        uuid_column("student_profile_id"),
        uuid_column("program_version_id"),
        uuid_column("requirement_node_id", nullable=True),
        uuid_column("original_course_id"),
        uuid_column("substitute_course_id"),
        sa.Column("status", enum(APPROVAL_STATUSES, "approval_status"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        *source_columns(),
        sa.CheckConstraint(
            "original_course_id != substitute_course_id",
            name="ck_course_substitutions_courses_different",
        ),
        mock_not_official("ck_course_substitutions_mock_not_official"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_course_substitutions_student",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["program_version_id", "institution_id"],
            ["program_versions.id", "program_versions.institution_id"],
            name="fk_course_substitutions_program_version_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requirement_node_id", "program_version_id", "institution_id"],
            [
                "requirement_nodes.id",
                "requirement_nodes.program_version_id",
                "requirement_nodes.institution_id",
            ],
            name="fk_course_substitutions_requirement_node_program_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["original_course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_course_substitutions_original_course_institution",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["substitute_course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_course_substitutions_substitute_course_institution",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("course_substitutions")
    op.drop_table("course_waivers")
    op.drop_table("transfer_credits")
    op.drop_index(
        "uq_student_course_attempts_student_course_attempt",
        table_name="student_course_attempts",
    )
    op.drop_table("student_course_attempts")
    op.drop_index(
        "uq_student_academic_programs_student_program_type",
        table_name="student_academic_programs",
    )
    op.drop_index(
        "uq_student_academic_programs_active_primary_major",
        table_name="student_academic_programs",
    )
    op.drop_table("student_academic_programs")
    op.drop_index(
        "uq_student_profiles_institution_external_ref",
        table_name="student_profiles",
    )
    op.drop_table("student_profiles")
    op.drop_index(
        "uq_requirement_course_options_node_course",
        table_name="requirement_course_options",
    )
    op.drop_table("requirement_course_options")
    op.drop_index("uq_requirement_nodes_program_code", table_name="requirement_nodes")
    op.drop_index(
        "uq_requirement_nodes_id_program_institution",
        table_name="requirement_nodes",
    )
    op.drop_table("requirement_nodes")
    op.drop_index(
        "uq_course_equivalencies_source_equivalent",
        table_name="course_equivalencies",
    )
    op.drop_table("course_equivalencies")
    op.drop_index("uq_courses_id_institution", table_name="courses")
    op.drop_index("uq_courses_institution_subject_number", table_name="courses")
    op.drop_table("courses")
    op.drop_index("uq_program_versions_id_institution", table_name="program_versions")
    op.drop_index(
        "uq_program_versions_program_campus_catalog_term",
        table_name="program_versions",
    )
    op.drop_table("program_versions")
    op.drop_index("uq_academic_programs_id_institution", table_name="academic_programs")
    op.drop_index(
        "uq_academic_programs_institution_code",
        table_name="academic_programs",
    )
    op.drop_table("academic_programs")
    op.drop_index("uq_academic_terms_id_institution", table_name="academic_terms")
    op.drop_index("uq_academic_terms_institution_code", table_name="academic_terms")
    op.drop_table("academic_terms")
    op.drop_index("uq_campuses_id_institution", table_name="campuses")
    op.drop_index("uq_campuses_institution_code", table_name="campuses")
    op.drop_table("campuses")
    op.drop_index("uq_institutions_code", table_name="institutions")
    op.drop_table("institutions")
