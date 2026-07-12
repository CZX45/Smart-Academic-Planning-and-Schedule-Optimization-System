from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
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
    BROWSER_EXTENSION = "BROWSER_EXTENSION"
    STUDENT_PROVIDED = "STUDENT_PROVIDED"
    INFERRED = "INFERRED"


class AuthUserRole(StrEnum):
    STUDENT = "STUDENT"
    ADVISOR = "ADVISOR"
    TENANT_ADMIN = "TENANT_ADMIN"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"


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


class CourseStateStatus(StrEnum):
    COMPLETED = "COMPLETED"
    IN_PROGRESS = "IN_PROGRESS"
    PLANNED = "PLANNED"
    NOT_STARTED = "NOT_STARTED"
    UNKNOWN = "UNKNOWN"


class CourseStateValidationState(StrEnum):
    RELIABLE = "RELIABLE"
    RELIABLE_WITH_WARNINGS = "RELIABLE_WITH_WARNINGS"
    EXTERNAL_EVIDENCE = "EXTERNAL_EVIDENCE"
    EXCEPTION = "EXCEPTION"


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


class EligibilityMode(StrEnum):
    CURRENT = "CURRENT"
    PROJECTED = "PROJECTED"
    REGISTRATION = "REGISTRATION"


class EligibilityCheckStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"


class EligibilityOverallResult(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    CONDITIONALLY_ELIGIBLE = "CONDITIONALLY_ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    PERMISSION_REQUIRED = "PERMISSION_REQUIRED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class EligibilityRuleResult(StrEnum):
    SATISFIED = "SATISFIED"
    CONDITIONALLY_SATISFIED = "CONDITIONALLY_SATISFIED"
    NOT_SATISFIED = "NOT_SATISFIED"
    PERMISSION_REQUIRED = "PERMISSION_REQUIRED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


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


class ScenarioType(StrEnum):
    ADD_MINOR = "ADD_MINOR"
    ADD_SECOND_MAJOR = "ADD_SECOND_MAJOR"
    ADD_CERTIFICATE = "ADD_CERTIFICATE"
    ADD_CONCENTRATION = "ADD_CONCENTRATION"
    CHANGE_PRIMARY_MAJOR = "CHANGE_PRIMARY_MAJOR"
    CUSTOM_COMBINATION = "CUSTOM_COMBINATION"


class AcademicPlanScenarioStatus(StrEnum):
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class AcademicPlanningMode(StrEnum):
    CURRENT_PROGRAM = "CURRENT_PROGRAM"
    WHAT_IF_SCENARIO = "WHAT_IF_SCENARIO"


class AcademicPlanRunStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"


class AcademicPlanTermStatus(StrEnum):
    PLANNED = "PLANNED"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class AcademicPlanCourseSource(StrEnum):
    DEGREE_AUDIT_REMAINING = "DEGREE_AUDIT_REMAINING"
    WHAT_IF_REMAINING = "WHAT_IF_REMAINING"
    PREREQUISITE_UNLOCK = "PREREQUISITE_UNLOCK"
    COREQUISITE_PAIR = "COREQUISITE_PAIR"
    MANUAL_PLACEHOLDER = "MANUAL_PLACEHOLDER"


class AcademicPlanCourseStatus(StrEnum):
    PLANNED = "PLANNED"
    CONDITIONALLY_PLANNED = "CONDITIONALLY_PLANNED"
    BLOCKED = "BLOCKED"
    ALTERNATIVE = "ALTERNATIVE"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class AcademicPlanCoverageType(StrEnum):
    DIRECT_REQUIREMENT = "DIRECT_REQUIREMENT"
    ELECTIVE_POOL = "ELECTIVE_POOL"
    TOTAL_CREDITS = "TOTAL_CREDITS"
    PREREQUISITE_ONLY = "PREREQUISITE_ONLY"
    WHAT_IF_REQUIREMENT = "WHAT_IF_REQUIREMENT"


class SchedulePlanningMode(StrEnum):
    FROM_DEGREE_AUDIT = "FROM_DEGREE_AUDIT"
    FROM_LONG_TERM_PLAN = "FROM_LONG_TERM_PLAN"
    CUSTOM_COURSE_SET = "CUSTOM_COURSE_SET"


class ScheduleRunStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"


class ScheduleOptionStatus(StrEnum):
    FEASIBLE = "FEASIBLE"
    FEASIBLE_WITH_WARNINGS = "FEASIBLE_WITH_WARNINGS"
    PARTIAL = "PARTIAL"
    INFEASIBLE = "INFEASIBLE"


class ScheduleConflictType(StrEnum):
    TIME_OVERLAP = "TIME_OVERLAP"
    UNAVAILABLE_TIME = "UNAVAILABLE_TIME"
    EXCLUDED_DAY = "EXCLUDED_DAY"
    CREDIT_LIMIT = "CREDIT_LIMIT"
    DUPLICATE_COURSE = "DUPLICATE_COURSE"
    ELIGIBILITY_BLOCKED = "ELIGIBILITY_BLOCKED"
    COREQUISITE_MISSING = "COREQUISITE_MISSING"
    NO_SECTION_AVAILABLE = "NO_SECTION_AVAILABLE"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class DataImportType(StrEnum):
    UNOFFICIAL_TRANSCRIPT = "UNOFFICIAL_TRANSCRIPT"
    DEGREE_AUDIT_EXPORT = "DEGREE_AUDIT_EXPORT"
    COURSE_CATALOG = "COURSE_CATALOG"
    SECTION_SCHEDULE = "SECTION_SCHEDULE"
    GENERIC_CSV = "GENERIC_CSV"
    GENERIC_JSON = "GENERIC_JSON"
    UNKNOWN = "UNKNOWN"


class DataImportStatus(StrEnum):
    PENDING = "PENDING"
    PARSING = "PARSING"
    PARSED = "PARSED"
    PARSED_WITH_WARNINGS = "PARSED_WITH_WARNINGS"
    FAILED = "FAILED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    ARCHIVED = "ARCHIVED"


class DataImportStorageStrategy(StrEnum):
    METADATA_ONLY = "METADATA_ONLY"
    LOCAL_DEV_FIXTURE = "LOCAL_DEV_FIXTURE"
    EXTERNAL_OBJECT_REFERENCE = "EXTERNAL_OBJECT_REFERENCE"
    NOT_STORED = "NOT_STORED"


class ImportedRecordType(StrEnum):
    COURSE_ATTEMPT = "COURSE_ATTEMPT"
    TRANSFER_CREDIT = "TRANSFER_CREDIT"
    REQUIREMENT = "REQUIREMENT"
    COURSE = "COURSE"
    SECTION = "SECTION"
    SECTION_MEETING = "SECTION_MEETING"
    PROGRAM = "PROGRAM"
    UNKNOWN = "UNKNOWN"


class ImportedRecordStatus(StrEnum):
    VALID = "VALID"
    VALID_WITH_WARNINGS = "VALID_WITH_WARNINGS"
    AMBIGUOUS = "AMBIGUOUS"
    DUPLICATE = "DUPLICATE"
    INVALID = "INVALID"
    UNSUPPORTED = "UNSUPPORTED"


class ImportTargetEntityType(StrEnum):
    COURSE = "COURSE"
    SECTION = "SECTION"
    ACADEMIC_TERM = "ACADEMIC_TERM"
    REQUIREMENT_NODE = "REQUIREMENT_NODE"
    PROGRAM_VERSION = "PROGRAM_VERSION"
    STUDENT_COURSE_ATTEMPT = "STUDENT_COURSE_ATTEMPT"
    UNKNOWN = "UNKNOWN"


class ImportMatchType(StrEnum):
    EXACT_CODE = "EXACT_CODE"
    NORMALIZED_CODE = "NORMALIZED_CODE"
    TITLE_SIMILARITY = "TITLE_SIMILARITY"
    TERM_MATCH = "TERM_MATCH"
    MANUAL_REQUIRED = "MANUAL_REQUIRED"
    NO_MATCH = "NO_MATCH"


class DataImportReviewStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    READY_TO_APPLY = "READY_TO_APPLY"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    APPLIED_WITH_WARNINGS = "APPLIED_WITH_WARNINGS"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class ImportedRecordReviewDecision(StrEnum):
    UNREVIEWED = "UNREVIEWED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    NEEDS_ADVISOR_REVIEW = "NEEDS_ADVISOR_REVIEW"
    EDITED_AND_CONFIRMED = "EDITED_AND_CONFIRMED"
    DEFERRED = "DEFERRED"


class DataApplicationStatus(StrEnum):
    PENDING = "PENDING"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    APPLIED_WITH_WARNINGS = "APPLIED_WITH_WARNINGS"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class AppliedImportTargetEntityType(StrEnum):
    STUDENT_COURSE_ATTEMPT = "STUDENT_COURSE_ATTEMPT"
    TRANSFER_CREDIT = "TRANSFER_CREDIT"
    COURSE = "COURSE"
    SECTION = "SECTION"
    SECTION_MEETING = "SECTION_MEETING"
    COURSE_OFFERING_PATTERN = "COURSE_OFFERING_PATTERN"
    COURSE_STATE = "COURSE_STATE"
    UNKNOWN = "UNKNOWN"


class AppliedImportAction(StrEnum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    SKIPPED_DUPLICATE = "SKIPPED_DUPLICATE"
    SKIPPED_REJECTED = "SKIPPED_REJECTED"
    SKIPPED_DEFERRED = "SKIPPED_DEFERRED"
    SKIPPED_ADVISOR_REVIEW = "SKIPPED_ADVISOR_REVIEW"
    SKIPPED_UNSUPPORTED = "SKIPPED_UNSUPPORTED"


class AppliedImportStatus(StrEnum):
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ScenarioRelationshipType(StrEnum):
    PRIMARY_MAJOR = "PRIMARY_MAJOR"
    MINOR = "MINOR"
    SECOND_MAJOR = "SECOND_MAJOR"
    CERTIFICATE = "CERTIFICATE"
    CONCENTRATION = "CONCENTRATION"


class ScenarioAllocationType(StrEnum):
    PRIMARY = "PRIMARY"
    SHARED = "SHARED"
    UNIQUE_SECONDARY = "UNIQUE_SECONDARY"
    TOTAL_CREDIT_ONLY = "TOTAL_CREDIT_ONLY"
    UNALLOCATED = "UNALLOCATED"


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


class SectionMonitorAlertType(StrEnum):
    STATUS_CHANGED = "STATUS_CHANGED"
    SEATS_CHANGED = "SEATS_CHANGED"
    SECTION_OPENED = "SECTION_OPENED"
    SECTION_CLOSED = "SECTION_CLOSED"
    WAITLIST_CHANGED = "WAITLIST_CHANGED"
    MEETING_TIME_CHANGED = "MEETING_TIME_CHANGED"
    INSTRUCTOR_CHANGED = "INSTRUCTOR_CHANGED"
    LOCATION_CHANGED = "LOCATION_CHANGED"
    UNKNOWN_CHANGE = "UNKNOWN_CHANGE"


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
auth_user_role_enum = Enum(
    AuthUserRole,
    name="auth_user_role",
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
course_state_status_enum = Enum(
    CourseStateStatus,
    name="course_state_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
course_state_validation_state_enum = Enum(
    CourseStateValidationState,
    name="course_state_validation_state",
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
eligibility_mode_enum = Enum(
    EligibilityMode,
    name="eligibility_mode",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
eligibility_check_status_enum = Enum(
    EligibilityCheckStatus,
    name="eligibility_check_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
eligibility_overall_result_enum = Enum(
    EligibilityOverallResult,
    name="eligibility_overall_result",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
eligibility_academic_result_enum = Enum(
    EligibilityOverallResult,
    name="eligibility_academic_result",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
eligibility_rule_result_enum = Enum(
    EligibilityRuleResult,
    name="eligibility_rule_result",
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
scenario_type_enum = Enum(
    ScenarioType,
    name="scenario_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
academic_plan_scenario_status_enum = Enum(
    AcademicPlanScenarioStatus,
    name="academic_plan_scenario_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
academic_planning_mode_enum = Enum(
    AcademicPlanningMode,
    name="academic_planning_mode",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
academic_plan_run_status_enum = Enum(
    AcademicPlanRunStatus,
    name="academic_plan_run_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
academic_plan_term_status_enum = Enum(
    AcademicPlanTermStatus,
    name="academic_plan_term_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
academic_plan_course_source_enum = Enum(
    AcademicPlanCourseSource,
    name="academic_plan_course_source",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
academic_plan_course_status_enum = Enum(
    AcademicPlanCourseStatus,
    name="academic_plan_course_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
academic_plan_coverage_type_enum = Enum(
    AcademicPlanCoverageType,
    name="academic_plan_coverage_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
schedule_planning_mode_enum = Enum(
    SchedulePlanningMode,
    name="schedule_planning_mode",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
schedule_run_status_enum = Enum(
    ScheduleRunStatus,
    name="schedule_run_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
schedule_option_status_enum = Enum(
    ScheduleOptionStatus,
    name="schedule_option_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
schedule_conflict_type_enum = Enum(
    ScheduleConflictType,
    name="schedule_conflict_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
data_import_type_enum = Enum(
    DataImportType,
    name="data_import_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
data_import_status_enum = Enum(
    DataImportStatus,
    name="data_import_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
data_import_storage_strategy_enum = Enum(
    DataImportStorageStrategy,
    name="data_import_storage_strategy",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
imported_record_type_enum = Enum(
    ImportedRecordType,
    name="imported_record_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
imported_record_status_enum = Enum(
    ImportedRecordStatus,
    name="imported_record_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
import_target_entity_type_enum = Enum(
    ImportTargetEntityType,
    name="import_target_entity_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
import_match_type_enum = Enum(
    ImportMatchType,
    name="import_match_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
data_import_review_status_enum = Enum(
    DataImportReviewStatus,
    name="data_import_review_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
imported_record_review_decision_enum = Enum(
    ImportedRecordReviewDecision,
    name="imported_record_review_decision",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
data_application_status_enum = Enum(
    DataApplicationStatus,
    name="data_application_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
applied_import_target_entity_type_enum = Enum(
    AppliedImportTargetEntityType,
    name="applied_import_target_entity_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
applied_import_action_enum = Enum(
    AppliedImportAction,
    name="applied_import_action",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
applied_import_status_enum = Enum(
    AppliedImportStatus,
    name="applied_import_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
scenario_relationship_type_enum = Enum(
    ScenarioRelationshipType,
    name="scenario_relationship_type",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
scenario_allocation_type_enum = Enum(
    ScenarioAllocationType,
    name="scenario_allocation_type",
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
section_monitor_alert_type_enum = Enum(
    SectionMonitorAlertType,
    name="section_monitor_alert_type",
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


class AuthTenant(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "auth_tenants"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_auth_tenants_institution",
            ondelete="RESTRICT",
        ),
        CheckConstraint("length(slug) > 0", name="ck_auth_tenants_slug_not_empty"),
        CheckConstraint("length(display_name) > 0", name="ck_auth_tenants_name_not_empty"),
        Index("uq_auth_tenants_slug", "slug", unique=True),
        Index("ix_auth_tenants_institution", "institution_id"),
    )

    institution_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AuthUser(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "auth_users"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id"],
            ["auth_tenants.id"],
            name="fk_auth_users_tenant",
            ondelete="RESTRICT",
        ),
        CheckConstraint("length(external_subject) > 0", name="ck_auth_users_subject_not_empty"),
        CheckConstraint(
            "email IS NULL OR length(email) > 0",
            name="ck_auth_users_email_not_empty",
        ),
        Index("uq_auth_users_tenant_subject", "tenant_id", "external_subject", unique=True),
        Index("ix_auth_users_tenant_role", "tenant_id", "role"),
    )

    tenant_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    external_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[AuthUserRole] = mapped_column(auth_user_role_enum, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AuthApiToken(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "auth_api_tokens"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"],
            ["auth_users.id"],
            name="fk_auth_api_tokens_user",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(token_hash) = 64", name="ck_auth_api_tokens_hash_length"),
        CheckConstraint("length(label) > 0", name="ck_auth_api_tokens_label_not_empty"),
        Index("uq_auth_api_tokens_hash", "token_hash", unique=True),
        Index("ix_auth_api_tokens_user", "user_id"),
    )

    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StudentProfileAccess(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "student_profile_access_grants"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"],
            ["auth_users.id"],
            name="fk_student_profile_access_user",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_student_profile_access_student",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(grant_reason) > 0", name="ck_student_profile_access_reason"),
        Index(
            "uq_student_profile_access_user_student",
            "user_id",
            "student_profile_id",
            unique=True,
        ),
        Index("ix_student_profile_access_student", "student_profile_id"),
    )

    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    student_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    role: Mapped[AuthUserRole] = mapped_column(auth_user_role_enum, nullable=False)
    grant_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
        ForeignKeyConstraint(
            ["course_state_snapshot_id"],
            ["course_state_snapshots.id"],
            name="fk_student_course_attempts_course_state_snapshot",
            ondelete="SET NULL",
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
        Index(
            "ix_student_course_attempts_course_state_snapshot",
            "course_state_snapshot_id",
        ),
    )

    student_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    term_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_state_snapshot_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
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


class EligibilityCheckRun(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "eligibility_check_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_eligibility_runs_institution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_eligibility_runs_student",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["course_id", "institution_id"],
            ["courses.id", "courses.institution_id"],
            name="fk_eligibility_runs_course_inst",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["section_id", "course_id", "institution_id"],
            ["sections.id", "sections.course_id", "sections.institution_id"],
            name="fk_eligibility_runs_section_course_inst",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["target_term_id", "institution_id"],
            ["academic_terms.id", "academic_terms.institution_id"],
            name="fk_eligibility_runs_term_inst",
            ondelete="RESTRICT",
        ),
        CheckConstraint("length(engine_version) > 0", name="ck_eligibility_runs_engine"),
        CheckConstraint("length(source_snapshot_hash) > 0", name="ck_eligibility_runs_hash"),
        Index(
            "ix_eligibility_runs_student_created",
            "student_profile_id",
            "created_at",
        ),
        Index(
            "ix_eligibility_runs_course_term",
            "course_id",
            "target_term_id",
            "mode",
        ),
    )

    institution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    student_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    section_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    target_term_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    mode: Mapped[EligibilityMode] = mapped_column(eligibility_mode_enum, nullable=False)
    status: Mapped[EligibilityCheckStatus] = mapped_column(
        eligibility_check_status_enum,
        nullable=False,
    )
    engine_version: Mapped[str] = mapped_column(String(80), nullable=False)
    overall_result: Mapped[EligibilityOverallResult] = mapped_column(
        eligibility_overall_result_enum,
        nullable=False,
    )
    academic_eligibility_result: Mapped[EligibilityOverallResult] = mapped_column(
        eligibility_academic_result_enum,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_snapshot_hash: Mapped[str] = mapped_column(String(128), nullable=False)


class RuleEvaluation(UuidPrimaryKeyMixin, Base):
    __tablename__ = "rule_evaluations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["eligibility_check_run_id"],
            ["eligibility_check_runs.id"],
            name="fk_rule_evaluations_run",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["course_rule_id"],
            ["course_rules.id"],
            name="fk_rule_evaluations_rule",
            ondelete="RESTRICT",
        ),
        CheckConstraint("display_order >= 0", name="ck_rule_evals_display_order_non_neg"),
        CheckConstraint("length(explanation) > 0", name="ck_rule_evals_explanation"),
        UniqueConstraint(
            "eligibility_check_run_id",
            "course_rule_id",
            name="uq_rule_evals_run_rule",
        ),
        Index(
            "ix_rule_evals_run_order",
            "eligibility_check_run_id",
            "display_order",
        ),
    )

    eligibility_check_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_rule_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    result: Mapped[EligibilityRuleResult] = mapped_column(
        eligibility_rule_result_enum,
        nullable=False,
    )
    rule_type: Mapped[CourseRuleType] = mapped_column(course_rule_type_enum, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class RuleExpressionEvaluation(UuidPrimaryKeyMixin, Base):
    __tablename__ = "rule_expression_evaluations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["rule_evaluation_id"],
            ["rule_evaluations.id"],
            name="fk_rule_expr_evals_rule_eval",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["course_rule_expression_id"],
            ["course_rule_expressions.id"],
            name="fk_rule_expr_evals_expression",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["matched_course_id"],
            ["courses.id"],
            name="fk_rule_expr_evals_matched_course",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["matched_attempt_id"],
            ["student_course_attempts.id"],
            name="fk_rule_expr_evals_matched_attempt",
            ondelete="RESTRICT",
        ),
        CheckConstraint("length(reason_code) > 0", name="ck_rule_expr_evals_reason"),
        CheckConstraint("length(explanation) > 0", name="ck_rule_expr_evals_explanation"),
        UniqueConstraint(
            "rule_evaluation_id",
            "course_rule_expression_id",
            name="uq_rule_expr_evals_rule_expression",
        ),
        Index(
            "ix_rule_expr_evals_rule_eval",
            "rule_evaluation_id",
        ),
    )

    rule_evaluation_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_rule_expression_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    result: Mapped[EligibilityRuleResult] = mapped_column(
        eligibility_rule_result_enum,
        nullable=False,
    )
    actual_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_course_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    matched_attempt_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class EligibilityWarning(UuidPrimaryKeyMixin, Base):
    __tablename__ = "eligibility_warnings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["eligibility_check_run_id"],
            ["eligibility_check_runs.id"],
            name="fk_eligibility_warnings_run",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["rule_evaluation_id"],
            ["rule_evaluations.id"],
            name="fk_eligibility_warnings_rule_eval",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(warning_code) > 0", name="ck_eligibility_warnings_code"),
        CheckConstraint("length(message) > 0", name="ck_eligibility_warnings_message"),
        Index(
            "ix_eligibility_warnings_run_severity",
            "eligibility_check_run_id",
            "severity",
        ),
    )

    eligibility_check_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    rule_evaluation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    warning_code: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[AuditWarningSeverity] = mapped_column(
        audit_warning_severity_enum,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    requires_advisor_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class AcademicPlanScenario(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "academic_plan_scenarios"
    __table_args__ = (
        ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_acad_plan_scenarios_student",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["base_program_version_id"],
            ["program_versions.id"],
            name="fk_acad_plan_scenarios_base_program",
            ondelete="RESTRICT",
        ),
        CheckConstraint("length(name) > 0", name="ck_acad_plan_scenarios_name"),
        CheckConstraint(
            "length(engine_version) > 0",
            name="ck_acad_plan_scenarios_engine",
        ),
        Index(
            "ix_acad_plan_scenarios_student_created",
            "student_profile_id",
            "created_at",
        ),
    )

    student_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario_type: Mapped[ScenarioType] = mapped_column(scenario_type_enum, nullable=False)
    status: Mapped[AcademicPlanScenarioStatus] = mapped_column(
        academic_plan_scenario_status_enum,
        nullable=False,
    )
    base_program_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(80), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScenarioProgram(UuidPrimaryKeyMixin, Base):
    __tablename__ = "scenario_programs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["academic_plan_scenario_id"],
            ["academic_plan_scenarios.id"],
            name="fk_scenario_programs_scenario",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["program_version_id"],
            ["program_versions.id"],
            name="fk_scenario_programs_program",
            ondelete="RESTRICT",
        ),
        CheckConstraint("priority >= 0", name="ck_scenario_programs_priority_non_neg"),
        CheckConstraint(
            "is_existing_program != is_hypothetical",
            name="ck_scenario_programs_snapshot_role",
        ),
        Index(
            "uq_scenario_programs_scenario_program",
            "academic_plan_scenario_id",
            "program_version_id",
            unique=True,
        ),
        Index(
            "uq_scenario_programs_one_primary",
            "academic_plan_scenario_id",
            unique=True,
            sqlite_where=text("relationship_type = 'PRIMARY_MAJOR'"),
            postgresql_where=text("relationship_type = 'PRIMARY_MAJOR'"),
        ),
        Index(
            "ix_scenario_programs_scenario_priority",
            "academic_plan_scenario_id",
            "priority",
        ),
    )

    academic_plan_scenario_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    program_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    relationship_type: Mapped[ScenarioRelationshipType] = mapped_column(
        scenario_relationship_type_enum,
        nullable=False,
    )
    is_existing_program: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_hypothetical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ProgramCombinationRule(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "program_combination_rules"
    __table_args__ = (
        ForeignKeyConstraint(
            ["primary_program_version_id"],
            ["program_versions.id"],
            name="fk_program_combo_rules_primary",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["secondary_program_version_id"],
            ["program_versions.id"],
            name="fk_program_combo_rules_secondary",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["effective_term_id"],
            ["academic_terms.id"],
            name="fk_program_combo_rules_eff_term",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["expiration_term_id"],
            ["academic_terms.id"],
            name="fk_program_combo_rules_exp_term",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "primary_program_version_id != secondary_program_version_id",
            name="ck_program_combo_rules_distinct",
        ),
        CheckConstraint(
            "maximum_shared_credits >= 0",
            name="ck_program_combo_rules_max_shared_non_neg",
        ),
        CheckConstraint(
            "minimum_unique_secondary_credits >= 0",
            name="ck_program_combo_rules_unique_credits_non_neg",
        ),
        CheckConstraint(
            "minimum_unique_courses >= 0",
            name="ck_program_combo_rules_unique_courses_non_neg",
        ),
        CheckConstraint(
            "expiration_term_id IS NULL OR expiration_term_id != effective_term_id",
            name="ck_program_combo_rules_terms_distinct",
        ),
        CheckConstraint(
            "is_official = false OR source_type != 'MOCK'",
            name="ck_program_combo_rules_mock_not_official",
        ),
        Index(
            "uq_program_combo_rules_direction",
            "primary_program_version_id",
            "secondary_program_version_id",
            "combination_type",
            "effective_term_id",
            unique=True,
        ),
    )

    primary_program_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    secondary_program_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    combination_type: Mapped[ScenarioRelationshipType] = mapped_column(
        scenario_relationship_type_enum,
        nullable=False,
    )
    maximum_shared_credits: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    minimum_unique_secondary_credits: Mapped[Decimal] = mapped_column(
        Numeric(5, 1),
        nullable=False,
    )
    minimum_unique_courses: Mapped[int] = mapped_column(nullable=False, default=0)
    allows_double_counting: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_manual_confirmation: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_term_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    expiration_term_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)


class ScenarioProgramAudit(UuidPrimaryKeyMixin, Base):
    __tablename__ = "scenario_program_audits"
    __table_args__ = (
        ForeignKeyConstraint(
            ["academic_plan_scenario_id"],
            ["academic_plan_scenarios.id"],
            name="fk_scenario_program_audits_scenario",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["scenario_program_id"],
            ["scenario_programs.id"],
            name="fk_scenario_program_audits_program",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["degree_audit_run_id"],
            ["degree_audit_runs.id"],
            name="fk_scenario_program_audits_run",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "academic_plan_scenario_id",
            "scenario_program_id",
            name="uq_scenario_program_audits_program",
        ),
        UniqueConstraint(
            "degree_audit_run_id",
            name="uq_scenario_program_audits_run",
        ),
    )

    academic_plan_scenario_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    scenario_program_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    degree_audit_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ScenarioCourseAllocation(UuidPrimaryKeyMixin, Base):
    __tablename__ = "scenario_course_allocations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["academic_plan_scenario_id"],
            ["academic_plan_scenarios.id"],
            name="fk_scenario_course_allocs_scenario",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["student_course_attempt_id"],
            ["student_course_attempts.id"],
            name="fk_scenario_course_allocs_attempt",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["transfer_credit_id"],
            ["transfer_credits.id"],
            name="fk_scenario_course_allocs_transfer",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["course_waiver_id"],
            ["course_waivers.id"],
            name="fk_scenario_course_allocs_waiver",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["course_substitution_id"],
            ["course_substitutions.id"],
            name="fk_scenario_course_allocs_substitution",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_scenario_course_allocs_course",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["program_version_id"],
            ["program_versions.id"],
            name="fk_scenario_course_allocs_program",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["requirement_node_id"],
            ["requirement_nodes.id"],
            name="fk_scenario_course_allocs_requirement",
            ondelete="RESTRICT",
        ),
        CheckConstraint("credit_amount >= 0", name="ck_scenario_course_allocs_credit_non_neg"),
        CheckConstraint("allocation_rank >= 0", name="ck_scenario_course_allocs_rank_non_neg"),
        CheckConstraint("length(reason_code) > 0", name="ck_scenario_course_allocs_reason"),
        CheckConstraint("length(explanation) > 0", name="ck_scenario_course_allocs_explained"),
        CheckConstraint(
            "(CASE WHEN student_course_attempt_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN transfer_credit_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN course_waiver_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN course_substitution_id IS NOT NULL THEN 1 ELSE 0 END) >= 1",
            name="ck_scenario_course_allocs_source",
        ),
        Index(
            "ix_scenario_course_allocs_scenario_rank",
            "academic_plan_scenario_id",
            "allocation_rank",
        ),
    )

    academic_plan_scenario_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    student_course_attempt_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    transfer_credit_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    course_waiver_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    course_substitution_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    course_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    program_version_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    requirement_node_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    allocation_type: Mapped[ScenarioAllocationType] = mapped_column(
        scenario_allocation_type_enum,
        nullable=False,
    )
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_unique_to_program: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allocation_rank: Mapped[int] = mapped_column(nullable=False, default=0)
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ScenarioComparisonSnapshot(Base):
    __tablename__ = "scenario_comparison_snapshots"
    __table_args__ = (
        ForeignKeyConstraint(
            ["academic_plan_scenario_id"],
            ["academic_plan_scenarios.id"],
            name="fk_scenario_comparison_scenario",
            ondelete="CASCADE",
        ),
        CheckConstraint("completed_credits >= 0", name="ck_scenario_comparison_completed"),
        CheckConstraint("in_progress_credits >= 0", name="ck_scenario_comparison_in_progress"),
        CheckConstraint("planned_credits >= 0", name="ck_scenario_comparison_planned"),
        CheckConstraint(
            "remaining_requirement_credits >= 0",
            name="ck_scenario_comparison_remaining",
        ),
        CheckConstraint("shared_credits >= 0", name="ck_scenario_comparison_shared"),
        CheckConstraint(
            "unique_secondary_credits >= 0",
            name="ck_scenario_comparison_unique",
        ),
        CheckConstraint(
            "estimated_additional_credits >= 0",
            name="ck_scenario_comparison_additional",
        ),
        CheckConstraint(
            "unresolved_requirements >= 0",
            name="ck_scenario_comparison_unresolved",
        ),
        CheckConstraint("manual_review_count >= 0", name="ck_scenario_comparison_manual"),
        CheckConstraint(
            "completion_percentage >= 0 AND completion_percentage <= 100",
            name="ck_scenario_comparison_completion",
        ),
    )

    academic_plan_scenario_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    completed_credits: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    in_progress_credits: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    planned_credits: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    remaining_requirement_credits: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    shared_credits: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    unique_secondary_credits: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    estimated_additional_credits: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    unresolved_requirements: Mapped[int] = mapped_column(nullable=False)
    manual_review_count: Mapped[int] = mapped_column(nullable=False)
    completion_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    is_estimate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ScenarioWarning(UuidPrimaryKeyMixin, Base):
    __tablename__ = "scenario_warnings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["academic_plan_scenario_id"],
            ["academic_plan_scenarios.id"],
            name="fk_scenario_warnings_scenario",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["scenario_program_id"],
            ["scenario_programs.id"],
            name="fk_scenario_warnings_program",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(warning_code) > 0", name="ck_scenario_warnings_code"),
        CheckConstraint("length(message) > 0", name="ck_scenario_warnings_message"),
        Index(
            "ix_scenario_warnings_scenario_severity",
            "academic_plan_scenario_id",
            "severity",
        ),
    )

    academic_plan_scenario_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    scenario_program_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    warning_code: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[AuditWarningSeverity] = mapped_column(
        audit_warning_severity_enum,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    requires_advisor_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class AcademicPlanRun(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "academic_plan_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_academic_plan_runs_student",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["program_version_id"],
            ["program_versions.id"],
            name="fk_academic_plan_runs_program",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["academic_plan_scenario_id"],
            ["academic_plan_scenarios.id"],
            name="fk_academic_plan_runs_scenario",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["start_term_id"],
            ["academic_terms.id"],
            name="fk_academic_plan_runs_start_term",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["target_completion_term_id"],
            ["academic_terms.id"],
            name="fk_academic_plan_runs_target_term",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "length(engine_version) > 0",
            name="ck_academic_plan_runs_engine",
        ),
        CheckConstraint(
            "minimum_credits_per_term >= 0",
            name="ck_academic_plan_runs_min_credits",
        ),
        CheckConstraint(
            "maximum_credits_per_term >= 0",
            name="ck_academic_plan_runs_max_credits",
        ),
        CheckConstraint(
            "preferred_credits_per_term >= 0",
            name="ck_academic_plan_runs_pref_credits",
        ),
        CheckConstraint(
            "preferred_credits_per_term <= maximum_credits_per_term",
            name="ck_academic_plan_runs_pref_under_max",
        ),
        CheckConstraint(
            "planning_mode != 'WHAT_IF_SCENARIO' OR academic_plan_scenario_id IS NOT NULL",
            name="ck_academic_plan_runs_what_if_has_scenario",
        ),
        Index(
            "ix_academic_plan_runs_student_created",
            "student_profile_id",
            "created_at",
        ),
        Index(
            "ix_academic_plan_runs_scenario",
            "academic_plan_scenario_id",
        ),
    )

    student_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    program_version_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    academic_plan_scenario_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    planning_mode: Mapped[AcademicPlanningMode] = mapped_column(
        academic_planning_mode_enum,
        nullable=False,
    )
    status: Mapped[AcademicPlanRunStatus] = mapped_column(
        academic_plan_run_status_enum,
        nullable=False,
    )
    engine_version: Mapped[str] = mapped_column(String(80), nullable=False)
    start_term_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    target_completion_term_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    minimum_credits_per_term: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    maximum_credits_per_term: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    preferred_credits_per_term: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AcademicPlanTerm(UuidPrimaryKeyMixin, Base):
    __tablename__ = "academic_plan_terms"
    __table_args__ = (
        ForeignKeyConstraint(
            ["academic_plan_run_id"],
            ["academic_plan_runs.id"],
            name="fk_academic_plan_terms_run",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["term_id"],
            ["academic_terms.id"],
            name="fk_academic_plan_terms_term",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "sequence_index >= 0",
            name="ck_academic_plan_terms_sequence",
        ),
        CheckConstraint(
            "planned_credits >= 0",
            name="ck_academic_plan_terms_credits",
        ),
        CheckConstraint(
            "length(explanation) > 0",
            name="ck_academic_plan_terms_explained",
        ),
        UniqueConstraint(
            "academic_plan_run_id",
            "term_id",
            name="uq_academic_plan_terms_run_term",
        ),
        UniqueConstraint(
            "academic_plan_run_id",
            "sequence_index",
            name="uq_academic_plan_terms_run_sequence",
        ),
        Index(
            "ix_academic_plan_terms_run_sequence",
            "academic_plan_run_id",
            "sequence_index",
        ),
    )

    academic_plan_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    term_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    sequence_index: Mapped[int] = mapped_column(nullable=False)
    planned_credits: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    status: Mapped[AcademicPlanTermStatus] = mapped_column(
        academic_plan_term_status_enum,
        nullable=False,
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class AcademicPlanCourse(UuidPrimaryKeyMixin, Base):
    __tablename__ = "academic_plan_courses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["academic_plan_term_id"],
            ["academic_plan_terms.id"],
            name="fk_academic_plan_courses_term",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_academic_plan_courses_course",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["requirement_node_id"],
            ["requirement_nodes.id"],
            name="fk_academic_plan_courses_requirement",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "priority_rank >= 0",
            name="ck_academic_plan_courses_priority",
        ),
        CheckConstraint("credits >= 0", name="ck_academic_plan_courses_credits"),
        CheckConstraint("length(reason_code) > 0", name="ck_academic_plan_courses_reason"),
        CheckConstraint("length(explanation) > 0", name="ck_academic_plan_courses_explained"),
        UniqueConstraint(
            "academic_plan_term_id",
            "course_id",
            name="uq_academic_plan_courses_term_course",
        ),
        Index(
            "ix_academic_plan_courses_term_rank",
            "academic_plan_term_id",
            "priority_rank",
        ),
    )

    academic_plan_term_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    requirement_node_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    source: Mapped[AcademicPlanCourseSource] = mapped_column(
        academic_plan_course_source_enum,
        nullable=False,
    )
    priority_rank: Mapped[int] = mapped_column(nullable=False)
    credits: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    eligibility_result: Mapped[EligibilityOverallResult] = mapped_column(
        eligibility_overall_result_enum,
        nullable=False,
    )
    planning_status: Mapped[AcademicPlanCourseStatus] = mapped_column(
        academic_plan_course_status_enum,
        nullable=False,
    )
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class AcademicPlanRequirementCoverage(UuidPrimaryKeyMixin, Base):
    __tablename__ = "academic_plan_requirement_coverages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["academic_plan_run_id"],
            ["academic_plan_runs.id"],
            name="fk_academic_plan_cov_run",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["academic_plan_course_id"],
            ["academic_plan_courses.id"],
            name="fk_academic_plan_cov_course",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["requirement_node_id"],
            ["requirement_nodes.id"],
            name="fk_academic_plan_cov_requirement",
            ondelete="RESTRICT",
        ),
        CheckConstraint("credits >= 0", name="ck_academic_plan_cov_credits"),
        UniqueConstraint(
            "academic_plan_course_id",
            "requirement_node_id",
            "coverage_type",
            name="uq_academic_plan_cov_course_req_type",
        ),
        Index(
            "ix_academic_plan_cov_run",
            "academic_plan_run_id",
        ),
    )

    academic_plan_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    academic_plan_course_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    requirement_node_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    coverage_type: Mapped[AcademicPlanCoverageType] = mapped_column(
        academic_plan_coverage_type_enum,
        nullable=False,
    )
    credits: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class AcademicPlanWarning(UuidPrimaryKeyMixin, Base):
    __tablename__ = "academic_plan_warnings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["academic_plan_run_id"],
            ["academic_plan_runs.id"],
            name="fk_academic_plan_warnings_run",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["academic_plan_term_id"],
            ["academic_plan_terms.id"],
            name="fk_academic_plan_warnings_term",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["academic_plan_course_id"],
            ["academic_plan_courses.id"],
            name="fk_academic_plan_warnings_course",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(warning_code) > 0", name="ck_academic_plan_warnings_code"),
        CheckConstraint("length(message) > 0", name="ck_academic_plan_warnings_message"),
        Index(
            "ix_academic_plan_warnings_run_severity",
            "academic_plan_run_id",
            "severity",
        ),
    )

    academic_plan_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    academic_plan_term_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    academic_plan_course_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    warning_code: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[AuditWarningSeverity] = mapped_column(
        audit_warning_severity_enum,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    requires_advisor_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ScheduleOptimizationRun(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "schedule_optimization_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_schedule_runs_student",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["term_id"],
            ["academic_terms.id"],
            name="fk_schedule_runs_term",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["academic_plan_run_id"],
            ["academic_plan_runs.id"],
            name="fk_schedule_runs_academic_plan",
            ondelete="SET NULL",
        ),
        CheckConstraint("length(engine_version) > 0", name="ck_schedule_runs_engine"),
        CheckConstraint("minimum_credits >= 0", name="ck_schedule_runs_min_credits"),
        CheckConstraint("maximum_credits >= 0", name="ck_schedule_runs_max_credits"),
        CheckConstraint("preferred_credits >= 0", name="ck_schedule_runs_pref_credits"),
        CheckConstraint(
            "maximum_credits >= minimum_credits",
            name="ck_schedule_runs_max_ge_min",
        ),
        CheckConstraint(
            "preferred_credits <= maximum_credits",
            name="ck_schedule_runs_pref_under_max",
        ),
        CheckConstraint(
            "requested_option_count > 0 AND requested_option_count <= 20",
            name="ck_schedule_runs_option_count",
        ),
        Index(
            "ix_schedule_runs_student_created",
            "student_profile_id",
            "created_at",
        ),
        Index("ix_schedule_runs_term_status", "term_id", "status"),
    )

    student_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    term_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    academic_plan_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    planning_mode: Mapped[SchedulePlanningMode] = mapped_column(
        schedule_planning_mode_enum,
        nullable=False,
    )
    status: Mapped[ScheduleRunStatus] = mapped_column(
        schedule_run_status_enum,
        nullable=False,
    )
    engine_version: Mapped[str] = mapped_column(String(80), nullable=False)
    minimum_credits: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    maximum_credits: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    preferred_credits: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    requested_option_count: Mapped[int] = mapped_column(nullable=False, default=3)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScheduleConstraintSet(UuidPrimaryKeyMixin, Base):
    __tablename__ = "schedule_constraint_sets"
    __table_args__ = (
        ForeignKeyConstraint(
            ["schedule_optimization_run_id"],
            ["schedule_optimization_runs.id"],
            name="fk_schedule_constraints_run",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "earliest_start_time IS NULL OR latest_end_time IS NULL "
            "OR earliest_start_time < latest_end_time",
            name="ck_schedule_constraints_time_window",
        ),
        CheckConstraint(
            "minimum_gap_minutes IS NULL OR minimum_gap_minutes >= 0",
            name="ck_schedule_constraints_min_gap",
        ),
        CheckConstraint(
            "maximum_gap_minutes IS NULL OR maximum_gap_minutes >= 0",
            name="ck_schedule_constraints_max_gap",
        ),
        CheckConstraint(
            "minimum_gap_minutes IS NULL OR maximum_gap_minutes IS NULL "
            "OR maximum_gap_minutes >= minimum_gap_minutes",
            name="ck_schedule_constraints_gap_order",
        ),
        UniqueConstraint(
            "schedule_optimization_run_id",
            name="uq_schedule_constraints_run",
        ),
    )

    schedule_optimization_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    excluded_days: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    unavailable_time_blocks: Mapped[list[dict[str, str]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    earliest_start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    latest_end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    minimum_gap_minutes: Mapped[int | None] = mapped_column(nullable=True)
    maximum_gap_minutes: Mapped[int | None] = mapped_column(nullable=True)
    candidate_course_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_modalities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    excluded_modalities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    required_course_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    excluded_course_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    required_section_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    excluded_section_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    prefer_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prefer_compact_schedule: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prefer_fewer_days: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prefer_in_person: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    avoid_early_start: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    avoid_late_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_permission_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    preference_weights: Mapped[dict[str, str]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    course_priority_weights: Mapped[dict[str, str]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    section_priority_weights: Mapped[dict[str, str]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    prefer_no_gaps: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prefer_morning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prefer_afternoon: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    diversity_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="STANDARD")
    allow_partial_options: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_combinations: Mapped[int] = mapped_column(nullable=False, default=500)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ScheduleOption(UuidPrimaryKeyMixin, Base):
    __tablename__ = "schedule_options"
    __table_args__ = (
        ForeignKeyConstraint(
            ["schedule_optimization_run_id"],
            ["schedule_optimization_runs.id"],
            name="fk_schedule_options_run",
            ondelete="CASCADE",
        ),
        CheckConstraint("option_rank > 0", name="ck_schedule_options_rank_positive"),
        CheckConstraint("total_credits >= 0", name="ck_schedule_options_credits"),
        CheckConstraint("class_days_count >= 0", name="ck_schedule_options_days"),
        CheckConstraint("total_gap_minutes >= 0", name="ck_schedule_options_gap"),
        CheckConstraint("total_score >= 0", name="ck_schedule_options_total_score"),
        CheckConstraint("credit_score >= 0", name="ck_schedule_options_credit_score"),
        CheckConstraint("compactness_score >= 0", name="ck_schedule_options_compact_score"),
        CheckConstraint("days_score >= 0", name="ck_schedule_options_days_score"),
        CheckConstraint("gap_score >= 0", name="ck_schedule_options_gap_score"),
        CheckConstraint("modality_score >= 0", name="ck_schedule_options_modality_score"),
        CheckConstraint("time_preference_score >= 0", name="ck_schedule_options_time_score"),
        CheckConstraint("priority_score >= 0", name="ck_schedule_options_priority_score"),
        CheckConstraint("penalty_score <= 0", name="ck_schedule_options_penalty_score"),
        CheckConstraint("diversity_rank > 0", name="ck_schedule_options_diversity_rank"),
        CheckConstraint(
            "shared_section_count_with_previous_option >= 0",
            name="ck_schedule_options_shared_sections",
        ),
        CheckConstraint("length(explanation) > 0", name="ck_schedule_options_explained"),
        UniqueConstraint(
            "schedule_optimization_run_id",
            "option_rank",
            name="uq_schedule_options_run_rank",
        ),
        Index(
            "ix_schedule_options_run_rank",
            "schedule_optimization_run_id",
            "option_rank",
        ),
    )

    schedule_optimization_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    option_rank: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[ScheduleOptionStatus] = mapped_column(
        schedule_option_status_enum,
        nullable=False,
    )
    total_credits: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    class_days_count: Mapped[int] = mapped_column(nullable=False)
    earliest_start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    latest_end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    total_gap_minutes: Mapped[int] = mapped_column(nullable=False, default=0)
    score: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    total_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    credit_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    compactness_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    days_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    gap_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    modality_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    time_preference_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    priority_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    penalty_score: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    score_explanation: Mapped[list[dict[str, str]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    diversity_rank: Mapped[int] = mapped_column(nullable=False, default=1)
    difference_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="Top ranked option.",
    )
    shared_section_count_with_previous_option: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ScheduleOptionSection(UuidPrimaryKeyMixin, Base):
    __tablename__ = "schedule_option_sections"
    __table_args__ = (
        ForeignKeyConstraint(
            ["schedule_option_id"],
            ["schedule_options.id"],
            name="fk_schedule_option_sections_option",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
            name="fk_schedule_option_sections_section",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_schedule_option_sections_course",
            ondelete="RESTRICT",
        ),
        CheckConstraint("credits >= 0", name="ck_schedule_option_sections_credits"),
        CheckConstraint(
            "length(selection_reason) > 0",
            name="ck_schedule_option_sections_reason",
        ),
        UniqueConstraint(
            "schedule_option_id",
            "course_id",
            name="uq_schedule_option_sections_course",
        ),
        UniqueConstraint(
            "schedule_option_id",
            "section_id",
            name="uq_schedule_option_sections_section",
        ),
        Index(
            "ix_schedule_option_sections_option",
            "schedule_option_id",
            "course_id",
        ),
    )

    schedule_option_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    section_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    credits: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    eligibility_result: Mapped[EligibilityOverallResult] = mapped_column(
        eligibility_overall_result_enum,
        nullable=False,
    )
    selection_reason: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ScheduleRepairSuggestion(UuidPrimaryKeyMixin, Base):
    __tablename__ = "schedule_repair_suggestions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["schedule_optimization_run_id"],
            ["schedule_optimization_runs.id"],
            name="fk_schedule_repair_suggestions_run",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["affected_course_id"],
            ["courses.id"],
            name="fk_schedule_repair_suggestions_course",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["affected_section_id"],
            ["sections.id"],
            name="fk_schedule_repair_suggestions_section",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "length(suggestion_type) > 0",
            name="ck_schedule_repair_suggestions_type",
        ),
        CheckConstraint(
            "length(estimated_impact) > 0",
            name="ck_schedule_repair_suggestions_impact",
        ),
        CheckConstraint(
            "length(message) > 0",
            name="ck_schedule_repair_suggestions_message",
        ),
        Index(
            "ix_schedule_repair_suggestions_run",
            "schedule_optimization_run_id",
            "suggestion_type",
        ),
    )

    schedule_optimization_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    suggestion_type: Mapped[str] = mapped_column(String(80), nullable=False)
    affected_constraint: Mapped[str | None] = mapped_column(String(120), nullable=True)
    affected_course_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    affected_section_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    estimated_impact: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    requires_advisor_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ScheduleConflict(UuidPrimaryKeyMixin, Base):
    __tablename__ = "schedule_conflicts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["schedule_optimization_run_id"],
            ["schedule_optimization_runs.id"],
            name="fk_schedule_conflicts_run",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["schedule_option_id"],
            ["schedule_options.id"],
            name="fk_schedule_conflicts_option",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
            name="fk_schedule_conflicts_section",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["other_section_id"],
            ["sections.id"],
            name="fk_schedule_conflicts_other_section",
            ondelete="RESTRICT",
        ),
        CheckConstraint("length(message) > 0", name="ck_schedule_conflicts_message"),
        Index(
            "ix_schedule_conflicts_run_type",
            "schedule_optimization_run_id",
            "conflict_type",
        ),
    )

    schedule_optimization_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    schedule_option_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    conflict_type: Mapped[ScheduleConflictType] = mapped_column(
        schedule_conflict_type_enum,
        nullable=False,
    )
    section_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    other_section_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    day_of_week: Mapped[DayOfWeek | None] = mapped_column(day_of_week_enum, nullable=True)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ScheduleWarning(UuidPrimaryKeyMixin, Base):
    __tablename__ = "schedule_warnings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["schedule_optimization_run_id"],
            ["schedule_optimization_runs.id"],
            name="fk_schedule_warnings_run",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["schedule_option_id"],
            ["schedule_options.id"],
            name="fk_schedule_warnings_option",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(warning_code) > 0", name="ck_schedule_warnings_code"),
        CheckConstraint("length(message) > 0", name="ck_schedule_warnings_message"),
        Index(
            "ix_schedule_warnings_run_severity",
            "schedule_optimization_run_id",
            "severity",
        ),
    )

    schedule_optimization_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    schedule_option_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    warning_code: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[AuditWarningSeverity] = mapped_column(
        audit_warning_severity_enum,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    requires_advisor_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class SectionMonitorTarget(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "section_monitor_targets"
    __table_args__ = (
        ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_section_monitor_targets_student",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(course_code) > 0", name="ck_section_monitor_targets_course"),
        CheckConstraint("length(section_code) > 0", name="ck_section_monitor_targets_section"),
        CheckConstraint("length(term) > 0", name="ck_section_monitor_targets_term"),
        CheckConstraint("is_official = false", name="ck_section_monitor_targets_never_official"),
        CheckConstraint(
            "source_type != 'OFFICIAL'",
            name="ck_section_monitor_targets_no_official_source",
        ),
        CheckConstraint("is_advisory = true", name="ck_section_monitor_targets_advisory"),
        UniqueConstraint(
            "student_profile_id",
            "course_code",
            "section_code",
            "term",
            name="uq_section_monitor_targets_student_section_term",
        ),
        Index(
            "ix_section_monitor_targets_student_active",
            "student_profile_id",
            "is_active",
            "created_at",
        ),
    )

    student_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_code: Mapped[str] = mapped_column(String(40), nullable=False)
    section_code: Mapped[str] = mapped_column(String(40), nullable=False)
    term: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    instructor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_advisory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class SectionMonitorSnapshot(UuidPrimaryKeyMixin, SourceMetadataMixin, Base):
    __tablename__ = "section_monitor_snapshots"
    __table_args__ = (
        ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_section_monitor_snapshots_student",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["target_id"],
            ["section_monitor_targets.id"],
            name="fk_section_monitor_snapshots_target",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["data_import_id"],
            ["data_import_runs.id"],
            name="fk_section_monitor_snapshots_data_import",
            ondelete="SET NULL",
        ),
        CheckConstraint("length(course_code) > 0", name="ck_section_monitor_snapshots_course"),
        CheckConstraint("length(section_code) > 0", name="ck_section_monitor_snapshots_section"),
        CheckConstraint("length(term) > 0", name="ck_section_monitor_snapshots_term"),
        CheckConstraint("length(snapshot_hash) > 0", name="ck_section_monitor_snapshots_hash"),
        CheckConstraint(
            "seats_available IS NULL OR seats_available >= 0",
            name="ck_section_monitor_snapshots_seats_available",
        ),
        CheckConstraint(
            "seats_capacity IS NULL OR seats_capacity >= 0",
            name="ck_section_monitor_snapshots_seats_capacity",
        ),
        CheckConstraint(
            "waitlist_available IS NULL OR waitlist_available >= 0",
            name="ck_section_monitor_snapshots_waitlist_available",
        ),
        CheckConstraint(
            "waitlist_capacity IS NULL OR waitlist_capacity >= 0",
            name="ck_section_monitor_snapshots_waitlist_capacity",
        ),
        CheckConstraint("is_official = false", name="ck_section_monitor_snapshots_never_official"),
        CheckConstraint(
            "source_type != 'OFFICIAL'",
            name="ck_section_monitor_snapshots_no_official_source",
        ),
        UniqueConstraint(
            "student_profile_id",
            "course_code",
            "section_code",
            "term",
            "snapshot_hash",
            name="uq_section_monitor_snapshots_student_section_hash",
        ),
        Index(
            "ix_section_monitor_snapshots_lookup",
            "student_profile_id",
            "course_code",
            "section_code",
            "term",
            "created_at",
        ),
        Index("ix_section_monitor_snapshots_target_created", "target_id", "created_at"),
    )

    student_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    target_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    data_import_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    course_code: Mapped[str] = mapped_column(String(40), nullable=False)
    section_code: Mapped[str] = mapped_column(String(40), nullable=False)
    term: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    seats_available: Mapped[int | None] = mapped_column(nullable=True)
    seats_capacity: Mapped[int | None] = mapped_column(nullable=True)
    waitlist_available: Mapped[int | None] = mapped_column(nullable=True)
    waitlist_capacity: Mapped[int | None] = mapped_column(nullable=True)
    meeting_days: Mapped[str | None] = mapped_column(String(80), nullable=True)
    meeting_time: Mapped[str | None] = mapped_column(String(120), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    instructor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class SectionMonitorAlert(UuidPrimaryKeyMixin, Base):
    __tablename__ = "section_monitor_alerts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["target_id"],
            ["section_monitor_targets.id"],
            name="fk_section_monitor_alerts_target",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["previous_snapshot_id"],
            ["section_monitor_snapshots.id"],
            name="fk_section_monitor_alerts_previous_snapshot",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["current_snapshot_id"],
            ["section_monitor_snapshots.id"],
            name="fk_section_monitor_alerts_current_snapshot",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(field_name) > 0", name="ck_section_monitor_alerts_field_name"),
        CheckConstraint("length(message) > 0", name="ck_section_monitor_alerts_message"),
        CheckConstraint("is_advisory = true", name="ck_section_monitor_alerts_advisory"),
        CheckConstraint(
            "requires_manual_review = true",
            name="ck_section_monitor_alerts_manual_review",
        ),
        UniqueConstraint(
            "previous_snapshot_id",
            "current_snapshot_id",
            "alert_type",
            "field_name",
            name="uq_section_monitor_alerts_snapshot_type_field",
        ),
        Index("ix_section_monitor_alerts_target_ack", "target_id", "is_acknowledged"),
        Index("ix_section_monitor_alerts_created", "created_at"),
    )

    target_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    previous_snapshot_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    current_snapshot_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    alert_type: Mapped[SectionMonitorAlertType] = mapped_column(
        section_monitor_alert_type_enum,
        nullable=False,
    )
    severity: Mapped[AuditWarningSeverity] = mapped_column(
        audit_warning_severity_enum,
        nullable=False,
    )
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)
    previous_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_advisory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DataImportRun(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "data_import_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_data_import_runs_student",
            ondelete="CASCADE",
        ),
        CheckConstraint("is_official = false", name="ck_data_import_runs_never_official"),
        CheckConstraint(
            "source_type != 'OFFICIAL'",
            name="ck_data_import_runs_no_official_source",
        ),
        CheckConstraint(
            "official_application_ready = false",
            name="ck_data_import_runs_preview_only",
        ),
        CheckConstraint("length(file_name) > 0", name="ck_data_import_runs_file_name"),
        CheckConstraint("length(file_mime_type) > 0", name="ck_data_import_runs_mime"),
        CheckConstraint("file_size_bytes >= 0", name="ck_data_import_runs_file_size"),
        CheckConstraint("length(file_sha256) = 64", name="ck_data_import_runs_sha256"),
        CheckConstraint("length(parser_version) > 0", name="ck_data_import_runs_parser"),
        CheckConstraint("record_count >= 0", name="ck_data_import_runs_record_count"),
        CheckConstraint("valid_record_count >= 0", name="ck_data_import_runs_valid_count"),
        CheckConstraint("warning_count >= 0", name="ck_data_import_runs_warning_count"),
        CheckConstraint("error_count >= 0", name="ck_data_import_runs_error_count"),
        Index("ix_data_import_runs_student_created", "student_profile_id", "created_at"),
        Index("ix_data_import_runs_status_type", "status", "import_type"),
    )

    student_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    import_type: Mapped[DataImportType] = mapped_column(data_import_type_enum, nullable=False)
    status: Mapped[DataImportStatus] = mapped_column(data_import_status_enum, nullable=False)
    storage_strategy: Mapped[DataImportStorageStrategy] = mapped_column(
        data_import_storage_strategy_enum,
        nullable=False,
        default=DataImportStorageStrategy.METADATA_ONLY,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(nullable=False, default=0)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(80), nullable=False)
    record_count: Mapped[int] = mapped_column(nullable=False, default=0)
    valid_record_count: Mapped[int] = mapped_column(nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(nullable=False, default=0)
    official_application_ready: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DataImportFile(UuidPrimaryKeyMixin, Base):
    __tablename__ = "data_import_files"
    __table_args__ = (
        ForeignKeyConstraint(
            ["data_import_run_id"],
            ["data_import_runs.id"],
            name="fk_data_import_files_run",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(file_name) > 0", name="ck_data_import_files_file_name"),
        CheckConstraint("length(file_mime_type) > 0", name="ck_data_import_files_mime"),
        CheckConstraint("file_size_bytes >= 0", name="ck_data_import_files_file_size"),
        CheckConstraint("length(file_sha256) = 64", name="ck_data_import_files_sha256"),
        CheckConstraint(
            "content_preview IS NULL OR length(content_preview) <= 500",
            name="ck_data_import_files_preview_length",
        ),
        UniqueConstraint("data_import_run_id", name="uq_data_import_files_run"),
    )

    data_import_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    storage_strategy: Mapped[DataImportStorageStrategy] = mapped_column(
        data_import_storage_strategy_enum,
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_preview: Mapped[str | None] = mapped_column(String(500), nullable=True)
    external_object_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ImportedRecord(UuidPrimaryKeyMixin, Base):
    __tablename__ = "imported_records"
    __table_args__ = (
        ForeignKeyConstraint(
            ["data_import_run_id"],
            ["data_import_runs.id"],
            name="fk_imported_records_run",
            ondelete="CASCADE",
        ),
        CheckConstraint("row_number > 0", name="ck_imported_records_row_number"),
        CheckConstraint("length(raw_label) > 0", name="ck_imported_records_raw_label"),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_imported_records_confidence",
        ),
        UniqueConstraint(
            "data_import_run_id",
            "row_number",
            name="uq_imported_records_run_row",
        ),
        Index("ix_imported_records_run_status", "data_import_run_id", "status"),
    )

    data_import_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    record_type: Mapped[ImportedRecordType] = mapped_column(
        imported_record_type_enum,
        nullable=False,
    )
    row_number: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[ImportedRecordStatus] = mapped_column(
        imported_record_status_enum,
        nullable=False,
    )
    external_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_label: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ImportMappingCandidate(UuidPrimaryKeyMixin, Base):
    __tablename__ = "import_mapping_candidates"
    __table_args__ = (
        ForeignKeyConstraint(
            ["imported_record_id"],
            ["imported_records.id"],
            name="fk_import_mapping_candidates_record",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_import_mapping_candidates_confidence",
        ),
        CheckConstraint("length(reason_code) > 0", name="ck_import_mapping_candidates_reason"),
        CheckConstraint(
            "length(explanation) > 0",
            name="ck_import_mapping_candidates_explained",
        ),
        Index(
            "ix_import_mapping_candidates_record_score",
            "imported_record_id",
            "confidence_score",
        ),
    )

    imported_record_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    target_entity_type: Mapped[ImportTargetEntityType] = mapped_column(
        import_target_entity_type_enum,
        nullable=False,
    )
    target_entity_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    match_type: Mapped[ImportMatchType] = mapped_column(import_match_type_enum, nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(4, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ImportValidationWarning(UuidPrimaryKeyMixin, Base):
    __tablename__ = "import_validation_warnings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["data_import_run_id"],
            ["data_import_runs.id"],
            name="fk_import_validation_warnings_run",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["imported_record_id"],
            ["imported_records.id"],
            name="fk_import_validation_warnings_record",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(warning_code) > 0", name="ck_import_warnings_code"),
        CheckConstraint("length(message) > 0", name="ck_import_warnings_message"),
        Index("ix_import_warnings_run_severity", "data_import_run_id", "severity"),
    )

    data_import_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    imported_record_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    warning_code: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[AuditWarningSeverity] = mapped_column(
        audit_warning_severity_enum,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    requires_advisor_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ImportPreviewSummary(UuidPrimaryKeyMixin, Base):
    __tablename__ = "import_preview_summaries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["data_import_run_id"],
            ["data_import_runs.id"],
            name="fk_import_preview_summaries_run",
            ondelete="CASCADE",
        ),
        CheckConstraint("record_count >= 0", name="ck_import_previews_record_count"),
        CheckConstraint("valid_record_count >= 0", name="ck_import_previews_valid_count"),
        CheckConstraint("warning_count >= 0", name="ck_import_previews_warning_count"),
        CheckConstraint("error_count >= 0", name="ck_import_previews_error_count"),
        CheckConstraint(
            "official_application_ready = false",
            name="ck_import_previews_preview_only",
        ),
        UniqueConstraint("data_import_run_id", name="uq_import_previews_run"),
    )

    data_import_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    record_count: Mapped[int] = mapped_column(nullable=False, default=0)
    valid_record_count: Mapped[int] = mapped_column(nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(nullable=False, default=0)
    official_application_ready: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    summary_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DataImportReviewSession(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_import_review_sessions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["data_import_run_id"],
            ["data_import_runs.id"],
            name="fk_data_import_review_sessions_run",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_data_import_review_sessions_student",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(reviewer_label) > 0", name="ck_data_import_reviews_reviewer"),
        Index(
            "ix_data_import_reviews_run_status",
            "data_import_run_id",
            "status",
        ),
        Index(
            "ix_data_import_reviews_student_created",
            "student_profile_id",
            "created_at",
        ),
    )

    data_import_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    student_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[DataImportReviewStatus] = mapped_column(
        data_import_review_status_enum,
        nullable=False,
    )
    reviewer_label: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ImportedRecordReview(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "imported_record_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["review_session_id"],
            ["data_import_review_sessions.id"],
            name="fk_imported_record_reviews_session",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["imported_record_id"],
            ["imported_records.id"],
            name="fk_imported_record_reviews_record",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["selected_mapping_candidate_id"],
            ["import_mapping_candidates.id"],
            name="fk_imported_record_reviews_candidate",
            ondelete="SET NULL",
        ),
        UniqueConstraint(
            "review_session_id",
            "imported_record_id",
            name="uq_imported_record_reviews_session_record",
        ),
        Index(
            "ix_imported_record_reviews_session_decision",
            "review_session_id",
            "decision",
        ),
    )

    review_session_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    imported_record_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    selected_mapping_candidate_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    decision: Mapped[ImportedRecordReviewDecision] = mapped_column(
        imported_record_review_decision_enum,
        nullable=False,
        default=ImportedRecordReviewDecision.UNREVIEWED,
    )
    edited_normalized_payload: Mapped[dict[str, object] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_advisor_confirmation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )


class DataApplicationRun(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_application_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["review_session_id"],
            ["data_import_review_sessions.id"],
            name="fk_data_application_runs_review",
            ondelete="CASCADE",
        ),
        CheckConstraint("applied_count >= 0", name="ck_data_applications_applied_count"),
        CheckConstraint("skipped_count >= 0", name="ck_data_applications_skipped_count"),
        CheckConstraint("warning_count >= 0", name="ck_data_applications_warning_count"),
        CheckConstraint("error_count >= 0", name="ck_data_applications_error_count"),
        Index(
            "ix_data_applications_review_created",
            "review_session_id",
            "created_at",
        ),
    )

    review_session_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[DataApplicationStatus] = mapped_column(
        data_application_status_enum,
        nullable=False,
    )
    applied_count: Mapped[int] = mapped_column(nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AppliedImportedRecord(UuidPrimaryKeyMixin, Base):
    __tablename__ = "applied_imported_records"
    __table_args__ = (
        ForeignKeyConstraint(
            ["data_application_run_id"],
            ["data_application_runs.id"],
            name="fk_applied_imported_records_application",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["imported_record_review_id"],
            ["imported_record_reviews.id"],
            name="fk_applied_imported_records_review",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["imported_record_id"],
            ["imported_records.id"],
            name="fk_applied_imported_records_record",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "length(reason_code) > 0",
            name="ck_applied_imported_records_reason_code",
        ),
        CheckConstraint("length(message) > 0", name="ck_applied_imported_records_message"),
        UniqueConstraint(
            "data_application_run_id",
            "imported_record_id",
            name="uq_applied_imported_records_application_record",
        ),
        Index(
            "ix_applied_imported_records_target",
            "target_entity_type",
            "target_entity_id",
        ),
    )

    data_application_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    imported_record_review_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    imported_record_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    target_entity_type: Mapped[AppliedImportTargetEntityType] = mapped_column(
        applied_import_target_entity_type_enum,
        nullable=False,
    )
    target_entity_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    action: Mapped[AppliedImportAction] = mapped_column(applied_import_action_enum, nullable=False)
    status: Mapped[AppliedImportStatus] = mapped_column(applied_import_status_enum, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DataReviewWarning(UuidPrimaryKeyMixin, Base):
    __tablename__ = "data_review_warnings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["review_session_id"],
            ["data_import_review_sessions.id"],
            name="fk_data_review_warnings_session",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["imported_record_review_id"],
            ["imported_record_reviews.id"],
            name="fk_data_review_warnings_record_review",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["data_application_run_id"],
            ["data_application_runs.id"],
            name="fk_data_review_warnings_application",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(warning_code) > 0", name="ck_data_review_warnings_code"),
        CheckConstraint("length(message) > 0", name="ck_data_review_warnings_message"),
        Index(
            "ix_data_review_warnings_session_severity",
            "review_session_id",
            "severity",
        ),
    )

    review_session_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    imported_record_review_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    data_application_run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    warning_code: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[AuditWarningSeverity] = mapped_column(
        audit_warning_severity_enum,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    requires_advisor_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class CourseStateSnapshot(UuidPrimaryKeyMixin, SourceMetadataMixin, TimestampMixin, Base):
    __tablename__ = "course_state_snapshots"
    __table_args__ = (
        ForeignKeyConstraint(
            ["student_profile_id"],
            ["student_profiles.id"],
            name="fk_course_state_snapshots_student",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["data_import_run_id"],
            ["data_import_runs.id"],
            name="fk_course_state_snapshots_import",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["review_session_id"],
            ["data_import_review_sessions.id"],
            name="fk_course_state_snapshots_review",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["data_application_run_id"],
            ["data_application_runs.id"],
            name="fk_course_state_snapshots_application",
            ondelete="CASCADE",
        ),
        CheckConstraint("is_official = false", name="ck_course_state_snapshots_unofficial"),
        CheckConstraint(
            "official_application_ready = false",
            name="ck_course_state_snapshots_not_official_ready",
        ),
        CheckConstraint("is_advisory = true", name="ck_course_state_snapshots_advisory"),
        CheckConstraint("completed_count >= 0", name="ck_course_state_snapshots_completed"),
        CheckConstraint(
            "in_progress_count >= 0",
            name="ck_course_state_snapshots_in_progress",
        ),
        CheckConstraint("planned_count >= 0", name="ck_course_state_snapshots_planned"),
        CheckConstraint(
            "not_started_count >= 0",
            name="ck_course_state_snapshots_not_started",
        ),
        CheckConstraint("matched_count >= 0", name="ck_course_state_snapshots_matched"),
        CheckConstraint("unmatched_count >= 0", name="ck_course_state_snapshots_unmatched"),
        CheckConstraint("exception_count >= 0", name="ck_course_state_snapshots_exception"),
        UniqueConstraint("data_import_run_id", name="uq_course_state_snapshots_import"),
        UniqueConstraint(
            "data_application_run_id",
            name="uq_course_state_snapshots_application",
        ),
        Index(
            "uq_course_state_snapshots_active_student",
            "student_profile_id",
            unique=True,
            sqlite_where=text("is_active = true"),
            postgresql_where=text("is_active = true"),
        ),
        Index(
            "ix_course_state_snapshots_student_applied",
            "student_profile_id",
            "applied_at",
        ),
    )

    student_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    data_import_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    review_session_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    data_application_run_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    source_page_type: Mapped[str] = mapped_column(String(120), nullable=False)
    source_validation_state: Mapped[str] = mapped_column(String(80), nullable=False)
    program_mapping_state: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_advisory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    official_application_ready: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    extraction_bounded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    extraction_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_count: Mapped[int] = mapped_column(nullable=False, default=0)
    in_progress_count: Mapped[int] = mapped_column(nullable=False, default=0)
    planned_count: Mapped[int] = mapped_column(nullable=False, default=0)
    not_started_count: Mapped[int] = mapped_column(nullable=False, default=0)
    matched_count: Mapped[int] = mapped_column(nullable=False, default=0)
    unmatched_count: Mapped[int] = mapped_column(nullable=False, default=0)
    exception_count: Mapped[int] = mapped_column(nullable=False, default=0)
    program_summary: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    credit_summary: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    requirement_summary: Mapped[list[object]] = mapped_column(JSON, nullable=False, default=list)
    readiness_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class CourseStateRecord(UuidPrimaryKeyMixin, Base):
    __tablename__ = "course_state_records"
    __table_args__ = (
        ForeignKeyConstraint(
            ["snapshot_id"],
            ["course_state_snapshots.id"],
            name="fk_course_state_records_snapshot",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["imported_record_id"],
            ["imported_records.id"],
            name="fk_course_state_records_imported_record",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["imported_record_review_id"],
            ["imported_record_reviews.id"],
            name="fk_course_state_records_record_review",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["matched_course_id"],
            ["courses.id"],
            name="fk_course_state_records_course",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["student_course_attempt_id"],
            ["student_course_attempts.id"],
            name="fk_course_state_records_attempt",
            ondelete="SET NULL",
        ),
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_course_state_records_confidence",
        ),
        CheckConstraint(
            "credits IS NULL OR credits >= 0",
            name="ck_course_state_records_credits",
        ),
        UniqueConstraint(
            "snapshot_id",
            "imported_record_id",
            name="uq_course_state_records_snapshot_imported_record",
        ),
        Index("ix_course_state_records_snapshot_status", "snapshot_id", "status"),
        Index("ix_course_state_records_matched_course", "matched_course_id"),
    )

    snapshot_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    imported_record_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    imported_record_review_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    matched_course_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    student_course_attempt_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    normalized_course_code: Mapped[str] = mapped_column(String(80), nullable=False)
    source_course_code: Mapped[str] = mapped_column(String(80), nullable=False)
    source_course_title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[CourseStateStatus] = mapped_column(course_state_status_enum, nullable=False)
    term: Mapped[str | None] = mapped_column(String(80), nullable=True)
    credits: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(16), nullable=True)
    requirement_context: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_page_type: Mapped[str] = mapped_column(String(120), nullable=False)
    source_table_index: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_row_index: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provenance: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    validation_state: Mapped[CourseStateValidationState] = mapped_column(
        course_state_validation_state_enum,
        nullable=False,
    )
    review_decision: Mapped[ImportedRecordReviewDecision] = mapped_column(
        imported_record_review_decision_enum,
        nullable=False,
    )
    application_reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    reason_codes: Mapped[list[object]] = mapped_column(JSON, nullable=False, default=list)
    warnings: Mapped[list[object]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
