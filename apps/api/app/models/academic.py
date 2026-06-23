from __future__ import annotations

from datetime import date, datetime, time
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
    Time,
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
    INCOMPLETE = "INCOMPLETE"
    TRANSFERRED = "TRANSFERRED"


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AuditRunStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"


class AuditMode(StrEnum):
    CURRENT = "CURRENT"
    PROJECTED = "PROJECTED"


class RequirementEvaluationStatus(StrEnum):
    SATISFIED = "SATISFIED"
    IN_PROGRESS = "IN_PROGRESS"
    PLANNED = "PLANNED"
    PARTIALLY_SATISFIED = "PARTIALLY_SATISFIED"
    NOT_SATISFIED = "NOT_SATISFIED"
    WAIVED = "WAIVED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AuditApplicationType(StrEnum):
    COURSE_ATTEMPT = "COURSE_ATTEMPT"
    TRANSFER_CREDIT = "TRANSFER_CREDIT"
    WAIVER = "WAIVER"
    SUBSTITUTION = "SUBSTITUTION"
    EQUIVALENCY = "EQUIVALENCY"


class AuditWarningSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class TermType(StrEnum):
    FALL = "FALL"
    SPRING = "SPRING"
    SUMMER = "SUMMER"
    WINTER = "WINTER"
    OTHER = "OTHER"


class FrequencyType(StrEnum):
    EVERY_TERM = "EVERY_TERM"
    ANNUAL = "ANNUAL"
    ALTERNATING_YEARS = "ALTERNATING_YEARS"
    IRREGULAR = "IRREGULAR"
    UNKNOWN = "UNKNOWN"


class CourseRuleType(StrEnum):
    PREREQUISITE = "PREREQUISITE"
    COREQUISITE = "COREQUISITE"
    REGISTRATION_RESTRICTION = "REGISTRATION_RESTRICTION"
    REPEAT_RESTRICTION = "REPEAT_RESTRICTION"
    PERMISSION = "PERMISSION"


class CourseRuleExpressionNodeType(StrEnum):
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    COMPLETED_COURSE = "COMPLETED_COURSE"
    MINIMUM_GRADE = "MINIMUM_GRADE"
    MINIMUM_COMPLETED_CREDITS = "MINIMUM_COMPLETED_CREDITS"
    CLASS_STANDING = "CLASS_STANDING"
    MAJOR_RESTRICTION = "MAJOR_RESTRICTION"
    MINOR_RESTRICTION = "MINOR_RESTRICTION"
    PROGRAM_RESTRICTION = "PROGRAM_RESTRICTION"
    CAMPUS_RESTRICTION = "CAMPUS_RESTRICTION"
    PERMISSION_REQUIRED = "PERMISSION_REQUIRED"


class SectionStatus(StrEnum):
    PLANNED = "PLANNED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    WAITLIST = "WAITLIST"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    UNKNOWN = "UNKNOWN"


class SectionModality(StrEnum):
    IN_PERSON = "IN_PERSON"
    ONLINE_SYNCHRONOUS = "ONLINE_SYNCHRONOUS"
    ONLINE_ASYNCHRONOUS = "ONLINE_ASYNCHRONOUS"
    HYBRID = "HYBRID"
    ARRANGED = "ARRANGED"
    UNKNOWN = "UNKNOWN"


class MeetingType(StrEnum):
    LECTURE = "LECTURE"
    LAB = "LAB"
    RECITATION = "RECITATION"
    SEMINAR = "SEMINAR"
    EXAM = "EXAM"
    OTHER = "OTHER"


class DayOfWeek(StrEnum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


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
audit_run_status_enum = Enum(
    AuditRunStatus,
    name="audit_run_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
audit_mode_enum = Enum(
    AuditMode,
    name="audit_mode",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
requirement_evaluation_status_enum = Enum(
    RequirementEvaluationStatus,
    name="requirement_evaluation_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
audit_application_type_enum = Enum(
    AuditApplicationType,
    name="audit_application_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
audit_warning_severity_enum = Enum(
    AuditWarningSeverity,
    name="audit_warning_severity",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
term_type_enum = Enum(
    TermType,
    name="term_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
frequency_type_enum = Enum(
    FrequencyType,
    name="frequency_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
course_rule_type_enum = Enum(
    CourseRuleType,
    name="course_rule_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
course_rule_expression_node_type_enum = Enum(
    CourseRuleExpressionNodeType,
    name="course_rule_expression_node_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
section_status_enum = Enum(
    SectionStatus,
    name="section_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
section_modality_enum = Enum(
    SectionModality,
    name="section_modality",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
meeting_type_enum = Enum(
    MeetingType,
    name="meeting_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
day_of_week_enum = Enum(
    DayOfWeek,
    name="day_of_week",
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


class CourseOfferingPattern(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "course_offering_patterns"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_course_offering_patterns_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_course_offering_patterns_course_institution",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["campus_id", "institution_id"],
            ["campuses.id", "campuses.institution_id"],
            name="fk_course_offering_patterns_campus_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["effective_term_id", "institution_id"],
            ["academic_terms.id", "academic_terms.institution_id"],
            name="fk_course_offering_patterns_effective_term_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["expiration_term_id", "institution_id"],
            ["academic_terms.id", "academic_terms.institution_id"],
            name="fk_course_offering_patterns_expiration_term_institution",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "confidence_level >= 0 AND confidence_level <= 1",
            name="ck_course_offering_patterns_confidence_range",
        ),
        CheckConstraint(
            "expiration_term_id IS NULL OR expiration_term_id != effective_term_id",
            name="ck_course_offering_patterns_effective_expiration_distinct",
        ),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_course_offering_patterns_mock_not_official",
        ),
        Index(
            "uq_course_offering_patterns_open_range",
            "course_id",
            "campus_id",
            "term_type",
            "effective_term_id",
            unique=True,
            sqlite_where=text("expiration_term_id IS NULL"),
            postgresql_where=text("expiration_term_id IS NULL"),
        ),
        Index(
            "uq_course_offering_patterns_closed_range",
            "course_id",
            "campus_id",
            "term_type",
            "effective_term_id",
            "expiration_term_id",
            unique=True,
            sqlite_where=text("expiration_term_id IS NOT NULL"),
            postgresql_where=text("expiration_term_id IS NOT NULL"),
        ),
    )

    institution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    campus_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    term_type: Mapped[TermType] = mapped_column(term_type_enum, nullable=False)
    frequency_type: Mapped[FrequencyType] = mapped_column(frequency_type_enum, nullable=False)
    effective_term_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    expiration_term_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    confidence_level: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Section(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "sections"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_sections_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_sections_course_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["term_id", "institution_id"],
            ["academic_terms.id", "academic_terms.institution_id"],
            name="fk_sections_term_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["campus_id", "institution_id"],
            ["campuses.id", "campuses.institution_id"],
            name="fk_sections_campus_institution",
            ondelete="RESTRICT",
        ),
        CheckConstraint("length(section_code) > 0", name="ck_sections_code_not_empty"),
        CheckConstraint("credits IS NULL OR credits >= 0", name="ck_sections_credits_non_negative"),
        CheckConstraint(
            "capacity IS NULL OR capacity >= 0", name="ck_sections_capacity_non_negative"
        ),
        CheckConstraint(
            "available_seats IS NULL OR available_seats >= 0",
            name="ck_sections_available_seats_non_negative",
        ),
        CheckConstraint(
            "waitlist_capacity IS NULL OR waitlist_capacity >= 0",
            name="ck_sections_waitlist_capacity_non_negative",
        ),
        CheckConstraint(
            "waitlist_available IS NULL OR waitlist_available >= 0",
            name="ck_sections_waitlist_available_non_negative",
        ),
        CheckConstraint(
            "capacity IS NULL OR available_seats IS NULL OR available_seats <= capacity",
            name="ck_sections_available_not_above_capacity",
        ),
        CheckConstraint(
            "waitlist_capacity IS NULL OR waitlist_available IS NULL "
            "OR waitlist_available <= waitlist_capacity",
            name="ck_sections_waitlist_available_not_above_capacity",
        ),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_sections_mock_not_official",
        ),
        UniqueConstraint(
            "id",
            "course_id",
            "institution_id",
            name="uq_sections_id_course_institution",
        ),
        Index(
            "uq_sections_institution_term_course_code",
            "institution_id",
            "term_id",
            "course_id",
            "section_code",
            unique=True,
        ),
        Index("ix_sections_term_status_modality", "term_id", "status", "modality"),
        Index("ix_sections_course_term", "course_id", "term_id"),
    )

    institution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    term_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    campus_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    section_code: Mapped[str] = mapped_column(String(40), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    title_override: Mapped[str | None] = mapped_column(String(255), nullable=True)
    credits: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    status: Mapped[SectionStatus] = mapped_column(section_status_enum, nullable=False)
    modality: Mapped[SectionModality] = mapped_column(section_modality_enum, nullable=False)
    capacity: Mapped[int | None] = mapped_column(nullable=True)
    available_seats: Mapped[int | None] = mapped_column(nullable=True)
    waitlist_capacity: Mapped[int | None] = mapped_column(nullable=True)
    waitlist_available: Mapped[int | None] = mapped_column(nullable=True)
    instructor_display: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SectionMeeting(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "section_meetings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
            name="fk_section_meetings_section",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "display_order >= 0", name="ck_section_meetings_display_order_non_negative"
        ),
        CheckConstraint(
            "is_arranged = true OR is_online = true OR "
            "(day_of_week IS NOT NULL AND start_time IS NOT NULL AND end_time IS NOT NULL)",
            name="ck_section_meetings_fixed_meeting_has_time",
        ),
        CheckConstraint(
            "start_time IS NULL OR end_time IS NULL OR end_time > start_time",
            name="ck_section_meetings_time_range",
        ),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="ck_section_meetings_date_range",
        ),
        CheckConstraint("length(timezone) > 0", name="ck_section_meetings_timezone_not_empty"),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_section_meetings_mock_not_official",
        ),
        Index("ix_section_meetings_section_order", "section_id", "display_order"),
    )

    section_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    meeting_type: Mapped[MeetingType] = mapped_column(meeting_type_enum, nullable=False)
    day_of_week: Mapped[DayOfWeek | None] = mapped_column(day_of_week_enum, nullable=True)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    building: Mapped[str | None] = mapped_column(String(120), nullable=True)
    room: Mapped[str | None] = mapped_column(String(120), nullable=True)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False)
    is_arranged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_order: Mapped[int] = mapped_column(nullable=False, default=0)


class CourseRule(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "course_rules"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_course_rules_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_course_rules_course_institution",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["section_id", "course_id", "institution_id"],
            ["sections.id", "sections.course_id", "sections.institution_id"],
            name="fk_course_rules_section_course_institution",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["effective_term_id", "institution_id"],
            ["academic_terms.id", "academic_terms.institution_id"],
            name="fk_course_rules_effective_term_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["expiration_term_id", "institution_id"],
            ["academic_terms.id", "academic_terms.institution_id"],
            name="fk_course_rules_expiration_term_institution",
            ondelete="RESTRICT",
        ),
        CheckConstraint("course_id IS NOT NULL", name="ck_course_rules_has_course_scope"),
        CheckConstraint("length(name) > 0", name="ck_course_rules_name_not_empty"),
        CheckConstraint(
            "expiration_term_id IS NULL OR expiration_term_id != effective_term_id",
            name="ck_course_rules_effective_expiration_distinct",
        ),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_course_rules_mock_not_official",
        ),
        UniqueConstraint("id", "institution_id", name="uq_course_rules_id_institution"),
        Index(
            "uq_course_rules_course_scope",
            "institution_id",
            "course_id",
            "rule_type",
            "name",
            "effective_term_id",
            unique=True,
            sqlite_where=text("section_id IS NULL"),
            postgresql_where=text("section_id IS NULL"),
        ),
        Index(
            "uq_course_rules_section_scope",
            "section_id",
            "rule_type",
            "name",
            "effective_term_id",
            unique=True,
            sqlite_where=text("section_id IS NOT NULL"),
            postgresql_where=text("section_id IS NOT NULL"),
        ),
    )

    institution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    section_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    rule_type: Mapped[CourseRuleType] = mapped_column(course_rule_type_enum, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_term_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    expiration_term_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    requires_manual_confirmation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )


class CourseRuleExpression(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "course_rule_expressions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["course_rule_id", "institution_id"],
            ["course_rules.id", "course_rules.institution_id"],
            name="fk_course_rule_expressions_rule_institution",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["parent_id", "course_rule_id", "institution_id"],
            [
                "course_rule_expressions.id",
                "course_rule_expressions.course_rule_id",
                "course_rule_expressions.institution_id",
            ],
            name="fk_course_rule_expressions_parent_same_rule",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["referenced_course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_course_rule_expressions_referenced_course_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["referenced_program_id", "institution_id"],
            ["academic_programs.id", "academic_programs.institution_id"],
            name="fk_course_rule_expressions_referenced_program_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["referenced_campus_id", "institution_id"],
            ["campuses.id", "campuses.institution_id"],
            name="fk_course_rule_expressions_referenced_campus_institution",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "parent_id IS NULL OR parent_id != id",
            name="ck_course_rule_expressions_not_self_parent",
        ),
        CheckConstraint(
            "display_order >= 0",
            name="ck_course_rule_expressions_display_order_non_negative",
        ),
        CheckConstraint(
            "minimum_completed_credits IS NULL OR minimum_completed_credits >= 0",
            name="ck_course_rule_expr_min_completed_credits_non_negative",
        ),
        CheckConstraint(
            "node_type NOT IN ('AND', 'OR', 'NOT') OR "
            "(referenced_course_id IS NULL AND minimum_grade IS NULL "
            "AND minimum_completed_credits IS NULL AND class_standing IS NULL "
            "AND referenced_program_id IS NULL AND referenced_campus_id IS NULL "
            "AND permission_type IS NULL)",
            name="ck_course_rule_expressions_operator_has_no_operand",
        ),
        CheckConstraint(
            "node_type != 'COMPLETED_COURSE' OR referenced_course_id IS NOT NULL",
            name="ck_course_rule_expressions_completed_course_operand",
        ),
        CheckConstraint(
            "node_type != 'MINIMUM_GRADE' OR "
            "(referenced_course_id IS NOT NULL AND minimum_grade IS NOT NULL)",
            name="ck_course_rule_expressions_minimum_grade_operand",
        ),
        CheckConstraint(
            "node_type != 'MINIMUM_COMPLETED_CREDITS' OR minimum_completed_credits IS NOT NULL",
            name="ck_course_rule_expressions_minimum_credits_operand",
        ),
        CheckConstraint(
            "node_type != 'CLASS_STANDING' OR class_standing IS NOT NULL",
            name="ck_course_rule_expressions_class_standing_operand",
        ),
        CheckConstraint(
            "node_type NOT IN ('MAJOR_RESTRICTION', 'MINOR_RESTRICTION', "
            "'PROGRAM_RESTRICTION') OR referenced_program_id IS NOT NULL",
            name="ck_course_rule_expressions_program_operand",
        ),
        CheckConstraint(
            "node_type != 'CAMPUS_RESTRICTION' OR referenced_campus_id IS NOT NULL",
            name="ck_course_rule_expressions_campus_operand",
        ),
        CheckConstraint(
            "node_type != 'PERMISSION_REQUIRED' OR permission_type IS NOT NULL",
            name="ck_course_rule_expressions_permission_operand",
        ),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_course_rule_expressions_mock_not_official",
        ),
        UniqueConstraint(
            "id",
            "course_rule_id",
            "institution_id",
            name="uq_course_rule_expressions_id_rule_institution",
        ),
        Index(
            "uq_course_rule_expressions_single_root",
            "course_rule_id",
            unique=True,
            sqlite_where=text("parent_id IS NULL"),
            postgresql_where=text("parent_id IS NULL"),
        ),
        Index(
            "ix_course_rule_expressions_rule_parent_order",
            "course_rule_id",
            "parent_id",
            "display_order",
        ),
    )

    institution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_rule_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    node_type: Mapped[CourseRuleExpressionNodeType] = mapped_column(
        course_rule_expression_node_type_enum,
        nullable=False,
    )
    display_order: Mapped[int] = mapped_column(nullable=False, default=0)
    referenced_course_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    minimum_grade: Mapped[str | None] = mapped_column(String(8), nullable=True)
    minimum_completed_credits: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 1),
        nullable=True,
    )
    class_standing: Mapped[str | None] = mapped_column(String(40), nullable=True)
    referenced_program_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    referenced_campus_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    permission_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    text_value: Mapped[str | None] = mapped_column(Text, nullable=True)


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


class DegreeAuditRun(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "degree_audit_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_degree_audit_runs_student",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["program_version_id"],
            ["program_versions.id"],
            name="fk_degree_audit_runs_program_version",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "total_required_credits >= 0",
            name="ck_degree_audit_runs_total_required_non_negative",
        ),
        CheckConstraint(
            "completed_credits >= 0", name="ck_degree_audit_runs_completed_non_negative"
        ),
        CheckConstraint(
            "in_progress_credits >= 0",
            name="ck_degree_audit_runs_in_progress_non_negative",
        ),
        CheckConstraint("planned_credits >= 0", name="ck_degree_audit_runs_planned_non_negative"),
        CheckConstraint(
            "remaining_credits >= 0", name="ck_degree_audit_runs_remaining_non_negative"
        ),
        CheckConstraint(
            "completion_percentage >= 0 AND completion_percentage <= 100",
            name="ck_degree_audit_runs_completion_percentage_range",
        ),
        CheckConstraint("length(engine_version) > 0", name="ck_degree_audit_runs_engine_version"),
        CheckConstraint(
            "length(source_snapshot_hash) > 0",
            name="ck_degree_audit_runs_source_hash",
        ),
        Index(
            "ix_degree_audit_runs_student_created",
            "student_profile_id",
            "created_at",
        ),
    )

    student_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    program_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[AuditRunStatus] = mapped_column(audit_run_status_enum, nullable=False)
    engine_version: Mapped[str] = mapped_column(String(80), nullable=False)
    calculation_mode: Mapped[AuditMode] = mapped_column(audit_mode_enum, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_required_credits: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    completed_credits: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    in_progress_credits: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    planned_credits: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    remaining_credits: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    completion_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    source_snapshot_hash: Mapped[str] = mapped_column(String(128), nullable=False)


class RequirementEvaluation(UuidPrimaryKeyMixin, Base):
    __tablename__ = "requirement_evaluations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["degree_audit_run_id"],
            ["degree_audit_runs.id"],
            name="fk_requirement_evaluations_audit_run",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["requirement_node_id"],
            ["requirement_nodes.id"],
            name="fk_requirement_evaluations_requirement_node",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "required_credits IS NULL OR required_credits >= 0",
            name="ck_requirement_evaluations_required_credits_non_negative",
        ),
        CheckConstraint(
            "satisfied_credits >= 0",
            name="ck_requirement_evaluations_satisfied_credits_non_negative",
        ),
        CheckConstraint(
            "remaining_credits >= 0",
            name="ck_requirement_evaluations_remaining_credits_non_negative",
        ),
        CheckConstraint(
            "required_courses IS NULL OR required_courses >= 0",
            name="ck_requirement_evaluations_required_courses_non_negative",
        ),
        CheckConstraint(
            "satisfied_courses >= 0",
            name="ck_requirement_evaluations_satisfied_courses_non_negative",
        ),
        CheckConstraint(
            "remaining_courses >= 0",
            name="ck_requirement_evaluations_remaining_courses_non_negative",
        ),
        CheckConstraint(
            "display_order >= 0",
            name="ck_requirement_evaluations_display_order_non_negative",
        ),
        CheckConstraint("length(explanation) > 0", name="ck_requirement_evaluations_explained"),
        UniqueConstraint(
            "degree_audit_run_id",
            "requirement_node_id",
            name="uq_requirement_evaluations_run_node",
        ),
        Index(
            "ix_requirement_evaluations_run_order",
            "degree_audit_run_id",
            "display_order",
        ),
    )

    degree_audit_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    requirement_node_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[RequirementEvaluationStatus] = mapped_column(
        requirement_evaluation_status_enum, nullable=False
    )
    required_credits: Mapped[Decimal | None] = mapped_column(Numeric(6, 1), nullable=True)
    satisfied_credits: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    remaining_credits: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    required_courses: Mapped[int | None] = mapped_column(nullable=True)
    satisfied_courses: Mapped[int] = mapped_column(nullable=False)
    remaining_courses: Mapped[int] = mapped_column(nullable=False)
    minimum_grade: Mapped[str | None] = mapped_column(String(8), nullable=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class AuditCourseApplication(UuidPrimaryKeyMixin, Base):
    __tablename__ = "audit_course_applications"
    __table_args__ = (
        ForeignKeyConstraint(
            ["degree_audit_run_id"],
            ["degree_audit_runs.id"],
            name="fk_audit_course_applications_audit_run",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["requirement_evaluation_id"],
            ["requirement_evaluations.id"],
            name="fk_audit_course_applications_evaluation",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_audit_course_applications_course",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["student_course_attempt_id"],
            ["student_course_attempts.id"],
            name="fk_audit_course_applications_attempt",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["transfer_credit_id"],
            ["transfer_credits.id"],
            name="fk_audit_course_applications_transfer",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["course_waiver_id"],
            ["course_waivers.id"],
            name="fk_audit_course_applications_waiver",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["course_substitution_id"],
            ["course_substitutions.id"],
            name="fk_audit_course_applications_substitution",
            ondelete="RESTRICT",
        ),
        CheckConstraint("credit_amount >= 0", name="ck_audit_course_applications_credit_non_neg"),
        CheckConstraint("length(explanation) > 0", name="ck_audit_course_applications_explained"),
        CheckConstraint(
            "(CASE WHEN student_course_attempt_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN transfer_credit_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN course_waiver_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN course_substitution_id IS NOT NULL THEN 1 ELSE 0 END) = 1 "
            "OR (student_course_attempt_id IS NOT NULL AND course_substitution_id IS NOT NULL "
            "AND transfer_credit_id IS NULL AND course_waiver_id IS NULL)",
            name="ck_audit_course_applications_source_shape",
        ),
        Index(
            "ix_audit_course_applications_run_eval",
            "degree_audit_run_id",
            "requirement_evaluation_id",
        ),
    )

    degree_audit_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    requirement_evaluation_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    student_course_attempt_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    transfer_credit_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    course_waiver_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    course_substitution_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    application_type: Mapped[AuditApplicationType] = mapped_column(
        audit_application_type_enum, nullable=False
    )
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    grade: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_in_progress: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_planned: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DegreeAuditWarning(UuidPrimaryKeyMixin, Base):
    __tablename__ = "degree_audit_warnings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["degree_audit_run_id"],
            ["degree_audit_runs.id"],
            name="fk_degree_audit_warnings_audit_run",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["requirement_evaluation_id"],
            ["requirement_evaluations.id"],
            name="fk_degree_audit_warnings_evaluation",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(warning_code) > 0", name="ck_degree_audit_warnings_code"),
        CheckConstraint("length(message) > 0", name="ck_degree_audit_warnings_message"),
        Index(
            "ix_degree_audit_warnings_run_severity",
            "degree_audit_run_id",
            "severity",
        ),
    )

    degree_audit_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    requirement_evaluation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    warning_code: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[AuditWarningSeverity] = mapped_column(
        audit_warning_severity_enum, nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    requires_advisor_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
