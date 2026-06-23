from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SourceType(StrEnum):
    MOCK = "MOCK"
    OFFICIAL = "OFFICIAL"
    IMPORTED = "IMPORTED"
    STUDENT_PROVIDED = "STUDENT_PROVIDED"
    INFERRED = "INFERRED"


class ProgramType(StrEnum):
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    CERTIFICATE = "CERTIFICATE"
    CONCENTRATION = "CONCENTRATION"


class DegreeLevel(StrEnum):
    BACHELORS = "BACHELORS"
    MASTERS = "MASTERS"
    DOCTORATE = "DOCTORATE"
    CERTIFICATE = "CERTIFICATE"


class RequirementType(StrEnum):
    GROUP = "GROUP"
    REQUIRED_COURSE = "REQUIRED_COURSE"
    ALL_OF = "ALL_OF"
    ANY_OF = "ANY_OF"
    CHOOSE_N = "CHOOSE_N"
    MINIMUM_CREDITS = "MINIMUM_CREDITS"
    MINIMUM_COURSES = "MINIMUM_COURSES"
    MINIMUM_GRADE = "MINIMUM_GRADE"
    COURSE_LEVEL = "COURSE_LEVEL"
    RESIDENCY = "RESIDENCY"
    TOTAL_CREDITS = "TOTAL_CREDITS"
    CAPSTONE = "CAPSTONE"
    EXCLUSION = "EXCLUSION"


class StudentProgramType(StrEnum):
    PRIMARY_MAJOR = "PRIMARY_MAJOR"
    SECOND_MAJOR = "SECOND_MAJOR"
    MINOR = "MINOR"
    CERTIFICATE = "CERTIFICATE"


class StudentAcademicProgramStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    COMPLETED = "COMPLETED"


class StudentCourseAttemptStatus(StrEnum):
    COMPLETED = "COMPLETED"
    IN_PROGRESS = "IN_PROGRESS"
    PLANNED = "PLANNED"
    FAILED = "FAILED"
    WITHDRAWN = "WITHDRAWN"
    TRANSFERRED = "TRANSFERRED"


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


source_type_enum = Enum(
    SourceType,
    name="source_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
program_type_enum = Enum(
    ProgramType,
    name="program_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
degree_level_enum = Enum(
    DegreeLevel,
    name="degree_level",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
requirement_type_enum = Enum(
    RequirementType,
    name="requirement_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
student_program_type_enum = Enum(
    StudentProgramType,
    name="student_program_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
student_program_status_enum = Enum(
    StudentAcademicProgramStatus,
    name="student_program_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
course_attempt_status_enum = Enum(
    StudentCourseAttemptStatus,
    name="student_course_attempt_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
approval_status_enum = Enum(
    ApprovalStatus,
    name="approval_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)


class UuidPrimaryKeyMixin:
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)


class SourceMetadataMixin:
    source_type: Mapped[SourceType] = mapped_column(source_type_enum, nullable=False)
    is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_retrieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    source_confidence: Mapped[str | None] = mapped_column(String(80), nullable=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Institution(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "institutions"
    __table_args__ = (
        CheckConstraint("length(code) > 0", name="ck_institutions_code_not_empty"),
        CheckConstraint("length(name) > 0", name="ck_institutions_name_not_empty"),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'", name="ck_institutions_mock_not_official"
        ),
        Index("uq_institutions_code", "code", unique=True),
    )

    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="US")
    timezone: Mapped[str] = mapped_column(String(80), nullable=False)


class Campus(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "campuses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_campuses_institution",
            ondelete="RESTRICT",
        ),
        CheckConstraint("length(code) > 0", name="ck_campuses_code_not_empty"),
        CheckConstraint("length(name) > 0", name="ck_campuses_name_not_empty"),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'", name="ck_campuses_mock_not_official"
        ),
        Index("uq_campuses_institution_code", "institution_id", "code", unique=True),
        Index("uq_campuses_id_institution", "id", "institution_id", unique=True),
    )

    institution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AcademicTerm(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "academic_terms"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_academic_terms_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["campus_id", "institution_id"],
            ["campuses.id", "campuses.institution_id"],
            name="fk_academic_terms_campus_institution",
            ondelete="RESTRICT",
        ),
        CheckConstraint("length(term_code) > 0", name="ck_academic_terms_code_not_empty"),
        CheckConstraint("starts_on <= ends_on", name="ck_academic_terms_date_range"),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_academic_terms_mock_not_official",
        ),
        Index("uq_academic_terms_institution_code", "institution_id", "term_code", unique=True),
        Index("uq_academic_terms_id_institution", "id", "institution_id", unique=True),
    )

    institution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    campus_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    term_code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)


class AcademicProgram(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "academic_programs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_academic_programs_institution",
            ondelete="RESTRICT",
        ),
        CheckConstraint("length(code) > 0", name="ck_academic_programs_code_not_empty"),
        CheckConstraint("length(name) > 0", name="ck_academic_programs_name_not_empty"),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_academic_programs_mock_not_official",
        ),
        Index("uq_academic_programs_institution_code", "institution_id", "code", unique=True),
        Index("uq_academic_programs_id_institution", "id", "institution_id", unique=True),
    )

    institution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    program_type: Mapped[ProgramType] = mapped_column(program_type_enum, nullable=False)
    degree_level: Mapped[DegreeLevel] = mapped_column(degree_level_enum, nullable=False)


class ProgramVersion(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "program_versions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["program_id", "institution_id"],
            ["academic_programs.id", "academic_programs.institution_id"],
            name="fk_program_versions_program_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["campus_id", "institution_id"],
            ["campuses.id", "campuses.institution_id"],
            name="fk_program_versions_campus_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["effective_term_id", "institution_id"],
            ["academic_terms.id", "academic_terms.institution_id"],
            name="fk_program_versions_effective_term_institution",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "total_credits_required > 0", name="ck_program_versions_total_credits_positive"
        ),
        CheckConstraint(
            "length(catalog_year) > 0", name="ck_program_versions_catalog_year_not_empty"
        ),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_program_versions_mock_not_official",
        ),
        Index(
            "uq_program_versions_program_campus_catalog_term",
            "program_id",
            "campus_id",
            "catalog_year",
            "effective_term_id",
            unique=True,
        ),
        Index("uq_program_versions_id_institution", "id", "institution_id", unique=True),
    )

    institution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    program_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    campus_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    effective_term_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    catalog_year: Mapped[str] = mapped_column(String(32), nullable=False)
    version_label: Mapped[str] = mapped_column(String(255), nullable=False)
    total_credits_required: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)


class Course(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "courses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_courses_institution",
            ondelete="RESTRICT",
        ),
        CheckConstraint("credits_min > 0", name="ck_courses_credits_min_positive"),
        CheckConstraint("credits_max >= credits_min", name="ck_courses_credit_range"),
        CheckConstraint("course_level >= 0", name="ck_courses_level_non_negative"),
        CheckConstraint("length(subject_code) > 0", name="ck_courses_subject_not_empty"),
        CheckConstraint("length(course_number) > 0", name="ck_courses_number_not_empty"),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'", name="ck_courses_mock_not_official"
        ),
        Index(
            "uq_courses_institution_subject_number",
            "institution_id",
            "subject_code",
            "course_number",
            unique=True,
        ),
        Index("uq_courses_id_institution", "id", "institution_id", unique=True),
    )

    institution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    subject_code: Mapped[str] = mapped_column(String(16), nullable=False)
    course_number: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    credits_min: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    credits_max: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    course_level: Mapped[int] = mapped_column(nullable=False)
    repeatable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CourseEquivalency(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "course_equivalencies"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_course_equivalencies_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["source_course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_course_equivalencies_source_course_institution",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["equivalent_course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_course_equivalencies_equivalent_course_institution",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "source_course_id != equivalent_course_id",
            name="ck_course_equivalencies_not_self",
        ),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_course_equivalencies_mock_not_official",
        ),
        Index(
            "uq_course_equivalencies_source_equivalent",
            "source_course_id",
            "equivalent_course_id",
            unique=True,
        ),
    )

    institution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    source_course_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    equivalent_course_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class RequirementNode(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "requirement_nodes"
    __table_args__ = (
        ForeignKeyConstraint(
            ["program_version_id", "institution_id"],
            ["program_versions.id", "program_versions.institution_id"],
            name="fk_requirement_nodes_program_version_institution",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["parent_id", "program_version_id", "institution_id"],
            [
                "requirement_nodes.id",
                "requirement_nodes.program_version_id",
                "requirement_nodes.institution_id",
            ],
            name="fk_requirement_nodes_parent_same_program_version",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "parent_id IS NULL OR parent_id != id", name="ck_requirement_nodes_not_self_parent"
        ),
        CheckConstraint(
            "display_order >= 0", name="ck_requirement_nodes_display_order_non_negative"
        ),
        CheckConstraint(
            "minimum_credits IS NULL OR minimum_credits >= 0",
            name="ck_requirement_nodes_minimum_credits_non_negative",
        ),
        CheckConstraint(
            "minimum_courses IS NULL OR minimum_courses >= 0",
            name="ck_requirement_nodes_minimum_courses_non_negative",
        ),
        CheckConstraint(
            "choose_n IS NULL OR choose_n > 0", name="ck_requirement_nodes_choose_n_positive"
        ),
        CheckConstraint(
            "minimum_course_level IS NULL OR minimum_course_level >= 0",
            name="ck_requirement_nodes_minimum_course_level_non_negative",
        ),
        CheckConstraint(
            "minimum_residency_credits IS NULL OR minimum_residency_credits >= 0",
            name="ck_requirement_nodes_minimum_residency_credits_non_negative",
        ),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_requirement_nodes_mock_not_official",
        ),
        UniqueConstraint(
            "id",
            "program_version_id",
            "institution_id",
            name="uq_requirement_nodes_id_program_institution",
        ),
        Index("uq_requirement_nodes_program_code", "program_version_id", "code", unique=True),
    )

    institution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    program_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    requirement_type: Mapped[RequirementType] = mapped_column(requirement_type_enum, nullable=False)
    display_order: Mapped[int] = mapped_column(nullable=False, default=0)
    minimum_credits: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    minimum_courses: Mapped[int | None] = mapped_column(nullable=True)
    choose_n: Mapped[int | None] = mapped_column(nullable=True)
    minimum_grade: Mapped[str | None] = mapped_column(String(8), nullable=True)
    minimum_course_level: Mapped[int | None] = mapped_column(nullable=True)
    minimum_residency_credits: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    allows_overlap: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RequirementCourseOption(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "requirement_course_options"
    __table_args__ = (
        ForeignKeyConstraint(
            ["program_version_id", "institution_id"],
            ["program_versions.id", "program_versions.institution_id"],
            name="fk_requirement_course_options_program_version_institution",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["requirement_node_id", "program_version_id", "institution_id"],
            [
                "requirement_nodes.id",
                "requirement_nodes.program_version_id",
                "requirement_nodes.institution_id",
            ],
            name="fk_requirement_course_options_node_program_institution",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_requirement_course_options_course_institution",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "display_order >= 0", name="ck_requirement_course_options_display_order_non_negative"
        ),
        CheckConstraint(
            "credits_override IS NULL OR credits_override > 0",
            name="ck_requirement_course_options_credits_override_positive",
        ),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_requirement_course_options_mock_not_official",
        ),
        Index(
            "uq_requirement_course_options_node_course",
            "requirement_node_id",
            "course_id",
            unique=True,
        ),
    )

    institution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    program_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    requirement_node_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    display_order: Mapped[int] = mapped_column(nullable=False, default=0)
    minimum_grade: Mapped[str | None] = mapped_column(String(8), nullable=True)
    credits_override: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)


class StudentProfile(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "student_profiles"
    __table_args__ = (
        ForeignKeyConstraint(
            ["home_institution_id"],
            ["institutions.id"],
            name="fk_student_profiles_home_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["home_campus_id", "home_institution_id"],
            ["campuses.id", "campuses.institution_id"],
            name="fk_student_profiles_home_campus_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["expected_graduation_term_id", "home_institution_id"],
            ["academic_terms.id", "academic_terms.institution_id"],
            name="fk_student_profiles_expected_term_institution",
            ondelete="SET NULL",
        ),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_student_profiles_mock_not_official",
        ),
        Index(
            "uq_student_profiles_institution_external_ref",
            "home_institution_id",
            "external_ref",
            unique=True,
        ),
    )

    home_institution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    home_campus_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    expected_graduation_term_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    external_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False, default="Mock Student")
    class_standing: Mapped[str | None] = mapped_column(String(40), nullable=True)


class StudentAcademicProgram(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "student_academic_programs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_student_academic_programs_student",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["program_version_id"],
            ["program_versions.id"],
            name="fk_student_academic_programs_program_version",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_student_academic_programs_mock_not_official",
        ),
        Index(
            "uq_student_academic_programs_active_primary_major",
            "student_profile_id",
            unique=True,
            sqlite_where=text("program_type = 'PRIMARY_MAJOR' AND status = 'ACTIVE'"),
            postgresql_where=text("program_type = 'PRIMARY_MAJOR' AND status = 'ACTIVE'"),
        ),
        Index(
            "uq_student_academic_programs_student_program_type",
            "student_profile_id",
            "program_version_id",
            "program_type",
            unique=True,
        ),
    )

    student_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    program_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    program_type: Mapped[StudentProgramType] = mapped_column(
        student_program_type_enum, nullable=False
    )
    status: Mapped[StudentAcademicProgramStatus] = mapped_column(
        student_program_status_enum, nullable=False
    )
    declared_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class StudentCourseAttempt(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "student_course_attempts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_student_course_attempts_student",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_student_course_attempts_course",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["term_id"],
            ["academic_terms.id"],
            name="fk_student_course_attempts_term",
            ondelete="RESTRICT",
        ),
        CheckConstraint("attempt_number > 0", name="ck_student_course_attempts_attempt_positive"),
        CheckConstraint(
            "credits_attempted >= 0", name="ck_student_course_attempts_attempted_non_negative"
        ),
        CheckConstraint(
            "credits_earned >= 0", name="ck_student_course_attempts_earned_non_negative"
        ),
        CheckConstraint(
            "credits_earned <= credits_attempted",
            name="ck_student_course_attempts_earned_not_above_attempted",
        ),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_student_course_attempts_mock_not_official",
        ),
        Index(
            "uq_student_course_attempts_student_course_attempt",
            "student_profile_id",
            "course_id",
            "attempt_number",
            unique=True,
        ),
    )

    student_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    term_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    attempt_number: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[StudentCourseAttemptStatus] = mapped_column(
        course_attempt_status_enum, nullable=False
    )
    grade: Mapped[str | None] = mapped_column(String(8), nullable=True)
    credits_attempted: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    credits_earned: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    is_repeat: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class TransferCredit(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "transfer_credits"
    __table_args__ = (
        ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_transfer_credits_student",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["equivalent_course_id"],
            ["courses.id"],
            name="fk_transfer_credits_equivalent_course",
            ondelete="RESTRICT",
        ),
        CheckConstraint("credits_earned > 0", name="ck_transfer_credits_credits_positive"),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_transfer_credits_mock_not_official",
        ),
    )

    student_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    equivalent_course_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    source_institution_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_course_code: Mapped[str] = mapped_column(String(80), nullable=False)
    credits_earned: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    grade: Mapped[str | None] = mapped_column(String(8), nullable=True)
    status: Mapped[ApprovalStatus] = mapped_column(approval_status_enum, nullable=False)


class CourseWaiver(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "course_waivers"
    __table_args__ = (
        ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_course_waivers_student",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["program_version_id", "institution_id"],
            ["program_versions.id", "program_versions.institution_id"],
            name="fk_course_waivers_program_version_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["requirement_node_id", "program_version_id", "institution_id"],
            [
                "requirement_nodes.id",
                "requirement_nodes.program_version_id",
                "requirement_nodes.institution_id",
            ],
            name="fk_course_waivers_requirement_node_program_institution",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_course_waivers_mock_not_official",
        ),
    )

    institution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    student_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    program_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    requirement_node_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    status: Mapped[ApprovalStatus] = mapped_column(approval_status_enum, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class CourseSubstitution(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "course_substitutions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_course_substitutions_student",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["program_version_id", "institution_id"],
            ["program_versions.id", "program_versions.institution_id"],
            name="fk_course_substitutions_program_version_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["requirement_node_id", "program_version_id", "institution_id"],
            [
                "requirement_nodes.id",
                "requirement_nodes.program_version_id",
                "requirement_nodes.institution_id",
            ],
            name="fk_course_substitutions_requirement_node_program_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["original_course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_course_substitutions_original_course_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["substitute_course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_course_substitutions_substitute_course_institution",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "original_course_id != substitute_course_id",
            name="ck_course_substitutions_courses_different",
        ),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_course_substitutions_mock_not_official",
        ),
    )

    institution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    student_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    program_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    requirement_node_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    original_course_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    substitute_course_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[ApprovalStatus] = mapped_column(approval_status_enum, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
