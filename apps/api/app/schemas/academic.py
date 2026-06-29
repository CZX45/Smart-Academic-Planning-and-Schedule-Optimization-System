from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SourceMetadataResponse(BaseModel):
    source_type: str
    is_official: bool
    source_reference: str | None = None
    source_retrieved_at: datetime | None = None
    source_confidence: str | None = None


class InstitutionResponse(BaseModel):
    id: UUID
    code: str
    name: str
    country: str
    timezone: str
    source: SourceMetadataResponse


class CampusResponse(BaseModel):
    id: UUID
    institution_id: UUID
    code: str
    name: str
    location: str | None = None
    source: SourceMetadataResponse


class AcademicProgramResponse(BaseModel):
    id: UUID
    institution_id: UUID
    code: str
    name: str
    program_type: str
    degree_level: str
    source: SourceMetadataResponse


class ProgramVersionSummaryResponse(BaseModel):
    program_version_id: UUID
    program_id: UUID
    program_code: str
    program_name: str
    program_type: str
    degree_level: str
    campus_id: UUID
    campus_code: str
    campus_name: str
    catalog_year: str
    version_label: str
    total_credits_required: Decimal
    source: SourceMetadataResponse


class ProgramVersionDetailResponse(BaseModel):
    id: UUID
    institution_id: UUID
    catalog_year: str
    version_label: str
    total_credits_required: Decimal
    effective_term_id: UUID
    program: AcademicProgramResponse
    campus: CampusResponse
    source: SourceMetadataResponse


class CourseResponse(BaseModel):
    id: UUID
    institution_id: UUID
    subject_code: str
    course_number: str
    title: str
    description: str | None = None
    credits_min: Decimal
    credits_max: Decimal
    course_level: int
    repeatable: bool
    source: SourceMetadataResponse


class RequirementCourseOptionResponse(BaseModel):
    id: UUID
    course_id: UUID
    subject_code: str
    course_number: str
    title: str
    display_order: int
    minimum_grade: str | None = None
    credits_override: Decimal | None = None
    source: SourceMetadataResponse


class RequirementNodeResponse(BaseModel):
    id: UUID
    parent_id: UUID | None = None
    code: str
    name: str
    requirement_type: str
    display_order: int
    minimum_credits: Decimal | None = None
    minimum_courses: int | None = None
    choose_n: int | None = None
    minimum_grade: str | None = None
    minimum_course_level: int | None = None
    minimum_residency_credits: Decimal | None = None
    allows_overlap: bool
    is_required: bool
    course_options: list[RequirementCourseOptionResponse]
    source: SourceMetadataResponse


class RequirementTreeResponse(BaseModel):
    program_version_id: UUID
    nodes: list[RequirementNodeResponse]


class StudentAcademicProgramResponse(BaseModel):
    id: UUID
    program_version_id: UUID
    program_code: str
    program_name: str
    program_type: str
    status: str
    declared_on: date | None = None
    source: SourceMetadataResponse


class StudentProfileResponse(BaseModel):
    id: UUID
    home_institution_id: UUID
    home_campus_id: UUID
    expected_graduation_term_id: UUID | None = None
    external_ref: str | None = None
    display_name: str
    class_standing: str | None = None
    programs: list[StudentAcademicProgramResponse]
    source: SourceMetadataResponse


class StudentCourseAttemptResponse(BaseModel):
    id: UUID
    student_profile_id: UUID
    course_id: UUID
    course_code: str
    course_title: str
    term_id: UUID
    term_code: str
    attempt_number: int
    status: str
    grade: str | None = None
    credits_attempted: Decimal
    credits_earned: Decimal
    is_repeat: bool
    source: SourceMetadataResponse


class CourseOfferingPatternResponse(BaseModel):
    id: UUID
    institution_id: UUID
    course_id: UUID
    campus_id: UUID
    term_type: str
    frequency_type: str
    effective_term_id: UUID
    expiration_term_id: UUID | None = None
    confidence_level: Decimal
    notes: str | None = None
    source: SourceMetadataResponse


class SectionResponse(BaseModel):
    id: UUID
    institution_id: UUID
    course_id: UUID
    term_id: UUID
    campus_id: UUID
    section_code: str
    external_reference: str | None = None
    title_override: str | None = None
    credits: Decimal | None = None
    status: str
    modality: str
    capacity: int | None = None
    available_seats: int | None = None
    waitlist_capacity: int | None = None
    waitlist_available: int | None = None
    instructor_display: str | None = None
    last_synced_at: datetime | None = None
    source: SourceMetadataResponse


class SectionMeetingResponse(BaseModel):
    id: UUID
    section_id: UUID
    meeting_type: str
    day_of_week: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    building: str | None = None
    room: str | None = None
    timezone: str
    is_arranged: bool
    is_online: bool
    display_order: int
    source: SourceMetadataResponse


class CourseRuleResponse(BaseModel):
    id: UUID
    institution_id: UUID
    course_id: UUID
    section_id: UUID | None = None
    rule_type: str
    name: str
    description: str | None = None
    effective_term_id: UUID
    expiration_term_id: UUID | None = None
    requires_manual_confirmation: bool
    source: SourceMetadataResponse


class CourseRuleExpressionNodeResponse(BaseModel):
    id: UUID
    parent_id: UUID | None = None
    node_type: str
    display_order: int
    referenced_course_id: UUID | None = None
    minimum_grade: str | None = None
    minimum_completed_credits: Decimal | None = None
    class_standing: str | None = None
    referenced_program_id: UUID | None = None
    referenced_campus_id: UUID | None = None
    permission_type: str | None = None
    text_value: str | None = None
    children: list["CourseRuleExpressionNodeResponse"] = Field(default_factory=list)
    source: SourceMetadataResponse


class CourseRuleExpressionTreeResponse(BaseModel):
    course_rule_id: UUID
    root: CourseRuleExpressionNodeResponse | None = None


AuditModeValue = Literal["CURRENT", "PROJECTED"]
AuditRunStatusValue = Literal[
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "COMPLETED_WITH_WARNINGS",
]
RequirementEvaluationStatusValue = Literal[
    "SATISFIED",
    "IN_PROGRESS",
    "PLANNED",
    "PARTIALLY_SATISFIED",
    "NOT_SATISFIED",
    "WAIVED",
    "MANUAL_REVIEW_REQUIRED",
    "NOT_APPLICABLE",
]
AuditApplicationTypeValue = Literal[
    "COURSE_ATTEMPT",
    "TRANSFER_CREDIT",
    "WAIVER",
    "SUBSTITUTION",
    "EQUIVALENCY",
]
AuditWarningSeverityValue = Literal["INFO", "WARNING", "ERROR"]
ScenarioTypeValue = Literal[
    "ADD_MINOR",
    "ADD_SECOND_MAJOR",
    "ADD_CERTIFICATE",
    "ADD_CONCENTRATION",
    "CHANGE_PRIMARY_MAJOR",
    "CUSTOM_COMBINATION",
]
AcademicPlanScenarioStatusValue = Literal[
    "DRAFT",
    "RUNNING",
    "COMPLETED",
    "COMPLETED_WITH_WARNINGS",
    "FAILED",
    "ARCHIVED",
]
ScenarioRelationshipTypeValue = Literal[
    "PRIMARY_MAJOR",
    "MINOR",
    "SECOND_MAJOR",
    "CERTIFICATE",
    "CONCENTRATION",
]
ScenarioAllocationTypeValue = Literal[
    "PRIMARY",
    "SHARED",
    "UNIQUE_SECONDARY",
    "TOTAL_CREDIT_ONLY",
    "UNALLOCATED",
]
AcademicPlanningModeValue = Literal["CURRENT_PROGRAM", "WHAT_IF_SCENARIO"]
AcademicPlanRunStatusValue = Literal[
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "COMPLETED_WITH_WARNINGS",
    "FAILED",
]
AcademicPlanTermStatusValue = Literal[
    "PLANNED",
    "PARTIAL",
    "BLOCKED",
    "MANUAL_REVIEW_REQUIRED",
]
AcademicPlanCourseSourceValue = Literal[
    "DEGREE_AUDIT_REMAINING",
    "WHAT_IF_REMAINING",
    "PREREQUISITE_UNLOCK",
    "COREQUISITE_PAIR",
    "MANUAL_PLACEHOLDER",
]
AcademicPlanCourseStatusValue = Literal[
    "PLANNED",
    "CONDITIONALLY_PLANNED",
    "BLOCKED",
    "ALTERNATIVE",
    "MANUAL_REVIEW_REQUIRED",
]
AcademicPlanCoverageTypeValue = Literal[
    "DIRECT_REQUIREMENT",
    "ELECTIVE_POOL",
    "TOTAL_CREDITS",
    "PREREQUISITE_ONLY",
    "WHAT_IF_REQUIREMENT",
]
SchedulePlanningModeValue = Literal[
    "FROM_DEGREE_AUDIT",
    "FROM_LONG_TERM_PLAN",
    "CUSTOM_COURSE_SET",
]
ScheduleRunStatusValue = Literal[
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "COMPLETED_WITH_WARNINGS",
    "FAILED",
]
ScheduleOptionStatusValue = Literal[
    "FEASIBLE",
    "FEASIBLE_WITH_WARNINGS",
    "PARTIAL",
    "INFEASIBLE",
]
ScheduleConflictTypeValue = Literal[
    "TIME_OVERLAP",
    "UNAVAILABLE_TIME",
    "EXCLUDED_DAY",
    "CREDIT_LIMIT",
    "DUPLICATE_COURSE",
    "ELIGIBILITY_BLOCKED",
    "COREQUISITE_MISSING",
    "NO_SECTION_AVAILABLE",
    "MANUAL_REVIEW_REQUIRED",
]
DayOfWeekValue = Literal[
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
    "SUNDAY",
]
SectionModalityValue = Literal[
    "IN_PERSON",
    "ONLINE_SYNCHRONOUS",
    "ONLINE_ASYNCHRONOUS",
    "HYBRID",
    "ARRANGED",
    "UNKNOWN",
]
EligibilityModeValue = Literal["CURRENT", "PROJECTED", "REGISTRATION"]
EligibilityCheckStatusValue = Literal[
    "PENDING",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "COMPLETED_WITH_WARNINGS",
]
EligibilityOverallResultValue = Literal[
    "ELIGIBLE",
    "CONDITIONALLY_ELIGIBLE",
    "NOT_ELIGIBLE",
    "PERMISSION_REQUIRED",
    "MANUAL_REVIEW_REQUIRED",
]
EligibilityRuleResultValue = Literal[
    "SATISFIED",
    "CONDITIONALLY_SATISFIED",
    "NOT_SATISFIED",
    "PERMISSION_REQUIRED",
    "MANUAL_REVIEW_REQUIRED",
    "NOT_APPLICABLE",
]


class DegreeAuditCreateRequest(BaseModel):
    student_profile_id: UUID
    program_version_id: UUID
    calculation_mode: AuditModeValue


class DegreeAuditRunResponse(BaseModel):
    id: UUID
    student_profile_id: UUID
    program_version_id: UUID
    status: AuditRunStatusValue
    engine_version: str
    calculation_mode: AuditModeValue
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_required_credits: Decimal
    completed_credits: Decimal
    in_progress_credits: Decimal
    planned_credits: Decimal
    remaining_credits: Decimal
    completion_percentage: Decimal
    source_snapshot_hash: str
    created_at: datetime
    updated_at: datetime


class DegreeAuditWarningResponse(BaseModel):
    id: UUID
    degree_audit_run_id: UUID
    requirement_evaluation_id: UUID | None = None
    warning_code: str
    severity: AuditWarningSeverityValue
    message: str
    requires_advisor_confirmation: bool
    created_at: datetime


class AuditCourseApplicationResponse(BaseModel):
    id: UUID
    course_id: UUID | None = None
    course_code: str | None = None
    course_title: str | None = None
    student_course_attempt_id: UUID | None = None
    transfer_credit_id: UUID | None = None
    course_waiver_id: UUID | None = None
    course_substitution_id: UUID | None = None
    application_type: AuditApplicationTypeValue
    credit_amount: Decimal
    grade: str | None = None
    is_completed: bool
    is_in_progress: bool
    is_planned: bool
    is_shared: bool
    explanation: str


class RequirementEvaluationResponse(BaseModel):
    id: UUID
    degree_audit_run_id: UUID
    requirement_node_id: UUID
    requirement_code: str
    requirement_name: str
    requirement_type: str
    status: RequirementEvaluationStatusValue
    required_credits: Decimal | None = None
    satisfied_credits: Decimal
    remaining_credits: Decimal
    required_courses: int | None = None
    satisfied_courses: int
    remaining_courses: int
    minimum_grade: str | None = None
    explanation: str
    display_order: int
    applications: list[AuditCourseApplicationResponse]
    warnings: list[DegreeAuditWarningResponse]


class ScenarioProgramInputRequest(BaseModel):
    program_version_id: UUID
    relationship_type: ScenarioRelationshipTypeValue
    priority: int = Field(ge=0)


class AcademicScenarioCreateRequest(BaseModel):
    student_profile_id: UUID
    scenario_name: str = Field(min_length=1)
    scenario_type: ScenarioTypeValue
    calculation_mode: AuditModeValue
    programs: list[ScenarioProgramInputRequest] = Field(min_length=1)


class AcademicScenarioCompareRequest(BaseModel):
    scenario_ids: list[UUID] = Field(min_length=2)


class AcademicScenarioResponse(BaseModel):
    id: UUID
    student_profile_id: UUID
    name: str
    scenario_type: ScenarioTypeValue
    status: AcademicPlanScenarioStatusValue
    base_program_version_id: UUID
    engine_version: str
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class ScenarioProgramResponse(BaseModel):
    id: UUID
    academic_plan_scenario_id: UUID
    program_version_id: UUID
    relationship_type: ScenarioRelationshipTypeValue
    is_existing_program: bool
    is_hypothetical: bool
    priority: int
    program_code: str
    program_name: str
    source: SourceMetadataResponse
    created_at: datetime


class ScenarioProgramAuditResponse(BaseModel):
    scenario_program: ScenarioProgramResponse
    degree_audit_run: DegreeAuditRunResponse


class ScenarioCourseAllocationResponse(BaseModel):
    id: UUID
    academic_plan_scenario_id: UUID
    student_course_attempt_id: UUID | None = None
    transfer_credit_id: UUID | None = None
    course_waiver_id: UUID | None = None
    course_substitution_id: UUID | None = None
    course_id: UUID | None = None
    course_code: str | None = None
    course_title: str | None = None
    program_version_id: UUID | None = None
    requirement_node_id: UUID | None = None
    requirement_code: str | None = None
    allocation_type: ScenarioAllocationTypeValue
    credit_amount: Decimal
    is_shared: bool
    is_unique_to_program: bool
    allocation_rank: int
    reason_code: str
    explanation: str
    created_at: datetime


class ScenarioWarningResponse(BaseModel):
    id: UUID
    academic_plan_scenario_id: UUID
    scenario_program_id: UUID | None = None
    warning_code: str
    severity: AuditWarningSeverityValue
    message: str
    requires_advisor_confirmation: bool
    created_at: datetime


class ScenarioComparisonSnapshotResponse(BaseModel):
    academic_plan_scenario_id: UUID
    completed_credits: Decimal
    in_progress_credits: Decimal
    planned_credits: Decimal
    remaining_requirement_credits: Decimal
    shared_credits: Decimal
    unique_secondary_credits: Decimal
    estimated_additional_credits: Decimal
    unresolved_requirements: int
    manual_review_count: int
    completion_percentage: Decimal
    is_estimate: bool
    created_at: datetime


class CourseEligibilityCreateRequest(BaseModel):
    student_profile_id: UUID
    course_id: UUID
    section_id: UUID | None = None
    target_term_id: UUID
    mode: EligibilityModeValue
    planned_corequisite_course_ids: list[UUID] = Field(default_factory=list)


class CourseEligibilityBatchRequest(BaseModel):
    checks: list[CourseEligibilityCreateRequest] = Field(min_length=1, max_length=50)


class EligibilityReasonResponse(BaseModel):
    reason_code: str
    explanation: str
    course_rule_id: UUID | None = None
    course_rule_expression_id: UUID | None = None
    referenced_entity_type: str | None = None
    referenced_entity_id: UUID | None = None
    expected_value: str | None = None
    actual_value: str | None = None


class CorequisiteSummaryResponse(BaseModel):
    required_corequisite_courses: list[UUID]
    already_completed: list[UUID]
    currently_in_progress: list[UUID]
    must_enroll_concurrently: list[UUID]


class RegistrationAvailabilityResponse(BaseModel):
    section_status: str
    available_seats: int | None = None
    waitlist_available: int | None = None
    availability_note: str | None = None


class RuleExpressionEvaluationResponse(BaseModel):
    id: UUID
    rule_evaluation_id: UUID
    course_rule_expression_id: UUID
    node_type: str
    result: EligibilityRuleResultValue
    actual_value: str | None = None
    expected_value: str | None = None
    matched_course_id: UUID | None = None
    matched_attempt_id: UUID | None = None
    reason_code: str
    explanation: str
    created_at: datetime


class RuleEvaluationResponse(BaseModel):
    id: UUID
    eligibility_check_run_id: UUID
    course_rule_id: UUID
    result: EligibilityRuleResultValue
    rule_type: str
    explanation: str
    display_order: int
    expressions: list[RuleExpressionEvaluationResponse]
    created_at: datetime


class EligibilityWarningResponse(BaseModel):
    id: UUID
    eligibility_check_run_id: UUID
    rule_evaluation_id: UUID | None = None
    warning_code: str
    severity: AuditWarningSeverityValue
    message: str
    requires_advisor_confirmation: bool
    created_at: datetime


class CourseEligibilityCheckResponse(BaseModel):
    id: UUID
    institution_id: UUID
    student_profile_id: UUID
    course_id: UUID
    section_id: UUID | None = None
    target_term_id: UUID
    mode: EligibilityModeValue
    status: EligibilityCheckStatusValue
    engine_version: str
    overall_result: EligibilityOverallResultValue
    academic_eligibility_result: EligibilityOverallResultValue
    started_at: datetime | None = None
    completed_at: datetime | None = None
    source_snapshot_hash: str
    rule_evaluations: list[RuleEvaluationResponse]
    blocking_reasons: list[EligibilityReasonResponse]
    conditional_reasons: list[EligibilityReasonResponse]
    permissions_required: list[EligibilityReasonResponse]
    manual_review_reasons: list[EligibilityReasonResponse]
    corequisites_to_add: list[UUID]
    corequisite_summary: CorequisiteSummaryResponse | None = None
    registration_availability: RegistrationAvailabilityResponse | None = None
    warnings: list[EligibilityWarningResponse]
    created_at: datetime
    updated_at: datetime


class CourseEligibilityBatchResponse(BaseModel):
    results: list[CourseEligibilityCheckResponse]


class AcademicPlanCreateRequest(BaseModel):
    student_profile_id: UUID
    program_version_id: UUID
    academic_plan_scenario_id: UUID | None = None
    planning_mode: AcademicPlanningModeValue
    start_term_id: UUID
    terms_to_plan: int = Field(gt=0, le=16)
    minimum_credits_per_term: Decimal = Field(ge=0)
    maximum_credits_per_term: Decimal = Field(ge=0)
    preferred_credits_per_term: Decimal = Field(ge=0)


class AcademicPlanCompareRequest(BaseModel):
    academic_plan_ids: list[UUID] = Field(min_length=2)


class AcademicPlanRunResponse(BaseModel):
    id: UUID
    student_profile_id: UUID
    program_version_id: UUID
    academic_plan_scenario_id: UUID | None = None
    planning_mode: AcademicPlanningModeValue
    status: AcademicPlanRunStatusValue
    engine_version: str
    start_term_id: UUID
    target_completion_term_id: UUID
    minimum_credits_per_term: Decimal
    maximum_credits_per_term: Decimal
    preferred_credits_per_term: Decimal
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AcademicPlanTermResponse(BaseModel):
    id: UUID
    academic_plan_run_id: UUID
    term_id: UUID
    term_code: str
    sequence_index: int
    planned_credits: Decimal
    status: AcademicPlanTermStatusValue
    explanation: str
    created_at: datetime


class AcademicPlanCourseResponse(BaseModel):
    id: UUID
    academic_plan_term_id: UUID
    term_id: UUID
    term_code: str
    course_id: UUID
    course_code: str
    course_title: str
    requirement_node_id: UUID | None = None
    requirement_code: str | None = None
    source: AcademicPlanCourseSourceValue
    priority_rank: int
    credits: Decimal
    eligibility_result: EligibilityOverallResultValue
    planning_status: AcademicPlanCourseStatusValue
    reason_code: str
    explanation: str
    created_at: datetime


class AcademicPlanRequirementCoverageResponse(BaseModel):
    id: UUID
    academic_plan_run_id: UUID
    academic_plan_course_id: UUID
    requirement_node_id: UUID
    requirement_code: str
    coverage_type: AcademicPlanCoverageTypeValue
    credits: Decimal
    created_at: datetime


class AcademicPlanWarningResponse(BaseModel):
    id: UUID
    academic_plan_run_id: UUID
    academic_plan_term_id: UUID | None = None
    academic_plan_course_id: UUID | None = None
    warning_code: str
    severity: AuditWarningSeverityValue
    message: str
    requires_advisor_confirmation: bool
    created_at: datetime


class AcademicPlanDetailResponse(AcademicPlanRunResponse):
    terms: list[AcademicPlanTermResponse]
    planned_courses: list[AcademicPlanCourseResponse]
    requirement_coverage: list[AcademicPlanRequirementCoverageResponse]
    warnings: list[AcademicPlanWarningResponse]


class AcademicPlanComparisonResponse(BaseModel):
    academic_plan_run_id: UUID
    status: AcademicPlanRunStatusValue
    total_planned_credits: Decimal
    term_count: int
    planned_course_count: int
    warning_count: int
    completed_at: datetime | None = None


class ScheduleUnavailableTimeBlockRequest(BaseModel):
    day_of_week: DayOfWeekValue
    start_time: time
    end_time: time


class ScheduleOptimizationCreateRequest(BaseModel):
    student_profile_id: UUID
    term_id: UUID
    academic_plan_run_id: UUID | None = None
    planning_mode: SchedulePlanningModeValue
    candidate_course_ids: list[UUID] = Field(default_factory=list)
    minimum_credits: Decimal = Field(ge=0)
    maximum_credits: Decimal = Field(ge=0)
    preferred_credits: Decimal = Field(ge=0)
    requested_option_count: int = Field(gt=0, le=20)
    excluded_days: list[DayOfWeekValue] = Field(default_factory=list)
    unavailable_time_blocks: list[ScheduleUnavailableTimeBlockRequest] = Field(default_factory=list)
    earliest_start_time: time | None = None
    latest_end_time: time | None = None
    allowed_modalities: list[SectionModalityValue] = Field(default_factory=list)
    excluded_modalities: list[SectionModalityValue] = Field(default_factory=list)
    required_course_ids: list[UUID] = Field(default_factory=list)
    excluded_course_ids: list[UUID] = Field(default_factory=list)
    required_section_ids: list[UUID] = Field(default_factory=list)
    excluded_section_ids: list[UUID] = Field(default_factory=list)
    prefer_online: bool = False
    prefer_compact_schedule: bool = False
    prefer_fewer_days: bool = False
    prefer_in_person: bool = False
    avoid_early_start: bool = False
    avoid_late_end: bool = False
    allow_permission_required: bool = False
    minimum_gap_minutes: int | None = Field(default=None, ge=0)
    maximum_gap_minutes: int | None = Field(default=None, ge=0)


class ScheduleOptimizationCompareRequest(BaseModel):
    schedule_optimization_run_ids: list[UUID] = Field(min_length=2)


class ScheduleOptimizationRunResponse(BaseModel):
    id: UUID
    student_profile_id: UUID
    term_id: UUID
    academic_plan_run_id: UUID | None = None
    planning_mode: SchedulePlanningModeValue
    status: ScheduleRunStatusValue
    engine_version: str
    minimum_credits: Decimal
    maximum_credits: Decimal
    preferred_credits: Decimal
    requested_option_count: int
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ScheduleConstraintSetResponse(BaseModel):
    id: UUID
    schedule_optimization_run_id: UUID
    excluded_days: list[str]
    unavailable_time_blocks: list[dict[str, str]]
    earliest_start_time: str | None = None
    latest_end_time: str | None = None
    minimum_gap_minutes: int | None = None
    maximum_gap_minutes: int | None = None
    candidate_course_ids: list[str]
    allowed_modalities: list[str]
    excluded_modalities: list[str]
    required_course_ids: list[str]
    excluded_course_ids: list[str]
    required_section_ids: list[str]
    excluded_section_ids: list[str]
    prefer_online: bool
    prefer_compact_schedule: bool
    prefer_fewer_days: bool
    prefer_in_person: bool
    avoid_early_start: bool
    avoid_late_end: bool
    allow_permission_required: bool
    created_at: datetime


class ScheduleOptionSectionResponse(BaseModel):
    id: UUID
    schedule_option_id: UUID
    section_id: UUID
    course_id: UUID
    course_code: str
    course_title: str
    section_code: str
    section_status: str
    modality: str
    credits: Decimal
    eligibility_result: EligibilityOverallResultValue
    selection_reason: str
    meetings: list[SectionMeetingResponse]
    created_at: datetime


class ScheduleOptionResponse(BaseModel):
    id: UUID
    schedule_optimization_run_id: UUID
    option_rank: int
    status: ScheduleOptionStatusValue
    total_credits: Decimal
    class_days_count: int
    earliest_start_time: str | None = None
    latest_end_time: str | None = None
    total_gap_minutes: int
    score: Decimal
    explanation: str
    selected_sections: list[ScheduleOptionSectionResponse]
    created_at: datetime


class ScheduleConflictResponse(BaseModel):
    id: UUID
    schedule_optimization_run_id: UUID
    schedule_option_id: UUID | None = None
    conflict_type: ScheduleConflictTypeValue
    section_id: UUID | None = None
    other_section_id: UUID | None = None
    day_of_week: DayOfWeekValue | None = None
    start_time: str | None = None
    end_time: str | None = None
    message: str
    created_at: datetime


class ScheduleWarningResponse(BaseModel):
    id: UUID
    schedule_optimization_run_id: UUID
    schedule_option_id: UUID | None = None
    warning_code: str
    severity: AuditWarningSeverityValue
    message: str
    requires_advisor_confirmation: bool
    created_at: datetime


class ScheduleOptimizationDetailResponse(ScheduleOptimizationRunResponse):
    constraint_set: ScheduleConstraintSetResponse | None = None
    options: list[ScheduleOptionResponse]
    conflicts: list[ScheduleConflictResponse]
    warnings: list[ScheduleWarningResponse]


class ScheduleOptimizationComparisonResponse(BaseModel):
    schedule_optimization_run_id: UUID
    status: ScheduleRunStatusValue
    option_count: int
    warning_count: int
    best_score: Decimal | None = None
    best_total_credits: Decimal | None = None
    completed_at: datetime | None = None


class ErrorDetailResponse(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    detail: ErrorDetailResponse
