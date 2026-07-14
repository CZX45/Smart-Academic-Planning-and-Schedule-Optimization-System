from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.academic import (
    AcademicPlanCourse,
    AcademicPlanningMode,
    AcademicPlanRequirementCoverage,
    AcademicPlanRun,
    AcademicPlanScenario,
    AcademicPlanTerm,
    AcademicPlanWarning,
    AcademicProgram,
    AcademicTerm,
    AppliedImportAction,
    AppliedImportedRecord,
    AppliedImportStatus,
    AuditCourseApplication,
    AuditMode,
    Campus,
    Course,
    CourseOfferingPattern,
    CourseRule,
    CourseRuleExpression,
    CourseStateRecord,
    CourseStateSnapshot,
    DataApplicationRun,
    DataImportReviewSession,
    DataImportRun,
    DataImportType,
    DataReviewWarning,
    DayOfWeek,
    DegreeAuditRun,
    DegreeAuditWarning,
    EligibilityCheckRun,
    EligibilityMode,
    EligibilityWarning,
    ImportedRecord,
    ImportedRecordReview,
    ImportedRecordReviewDecision,
    ImportMappingCandidate,
    ImportPreviewSummary,
    ImportValidationWarning,
    Institution,
    ProgramVersion,
    RequirementCourseOption,
    RequirementEvaluation,
    RequirementNode,
    RuleEvaluation,
    RuleExpressionEvaluation,
    ScenarioComparisonSnapshot,
    ScenarioCourseAllocation,
    ScenarioProgram,
    ScenarioProgramAudit,
    ScenarioRelationshipType,
    ScenarioType,
    ScenarioWarning,
    ScheduleConflict,
    ScheduleConstraintSet,
    ScheduleOptimizationRun,
    ScheduleOption,
    ScheduleOptionSection,
    SchedulePlanningMode,
    ScheduleRepairSuggestion,
    ScheduleWarning,
    Section,
    SectionMeeting,
    SectionModality,
    SectionMonitorAlert,
    SectionMonitorSnapshot,
    SectionMonitorTarget,
    SectionStatus,
    SourceType,
    StudentAcademicProgram,
    StudentProfile,
)
from app.models.reviewed_rules import ReviewedRuleSetRecord
from app.schemas.academic import (
    AcademicPlanCompareRequest,
    AcademicPlanComparisonResponse,
    AcademicPlanCourseResponse,
    AcademicPlanCreateRequest,
    AcademicPlanDetailResponse,
    AcademicPlanRequirementCoverageResponse,
    AcademicPlanRunResponse,
    AcademicPlanTermResponse,
    AcademicPlanWarningResponse,
    AcademicProgramResponse,
    AcademicScenarioCompareRequest,
    AcademicScenarioCreateRequest,
    AcademicScenarioResponse,
    AppliedImportedRecordResponse,
    AuditCourseApplicationResponse,
    CampusResponse,
    CorequisiteSummaryResponse,
    CourseEligibilityBatchRequest,
    CourseEligibilityBatchResponse,
    CourseEligibilityCheckResponse,
    CourseEligibilityCreateRequest,
    CourseOfferingPatternResponse,
    CourseResponse,
    CourseRuleExpressionNodeResponse,
    CourseRuleExpressionTreeResponse,
    CourseRuleResponse,
    CourseStateRecordResponse,
    CourseStateSnapshotDetailResponse,
    CourseStateSnapshotResponse,
    DataApplicationRunResponse,
    DataImportCreateRequest,
    DataImportReviewApplyRequest,
    DataImportReviewCreateRequest,
    DataImportReviewSessionResponse,
    DataImportRunResponse,
    DataReviewApplicationResultResponse,
    DataReviewApplicationSummaryResponse,
    DataReviewWarningResponse,
    DegreeAuditCreateRequest,
    DegreeAuditRunResponse,
    DegreeAuditWarningResponse,
    EligibilityReasonResponse,
    EligibilityWarningResponse,
    ErrorResponse,
    ImportedRecordResponse,
    ImportedRecordReviewResponse,
    ImportedRecordReviewUpdateRequest,
    ImportMappingCandidateResponse,
    ImportPreviewSummaryResponse,
    ImportValidationWarningResponse,
    InstitutionResponse,
    ProgramVersionDetailResponse,
    ProgramVersionSummaryResponse,
    RegistrationAvailabilityResponse,
    RequirementCourseOptionResponse,
    RequirementEvaluationResponse,
    RequirementNodeResponse,
    RequirementTreeResponse,
    RuleEvaluationResponse,
    RuleExpressionEvaluationResponse,
    ScenarioComparisonSnapshotResponse,
    ScenarioCourseAllocationResponse,
    ScenarioProgramAuditResponse,
    ScenarioProgramResponse,
    ScenarioWarningResponse,
    ScheduleConflictResponse,
    ScheduleConstraintSetResponse,
    ScheduleOptimizationCompareRequest,
    ScheduleOptimizationComparisonResponse,
    ScheduleOptimizationCreateRequest,
    ScheduleOptimizationDetailResponse,
    ScheduleOptimizationRunResponse,
    ScheduleOptionResponse,
    ScheduleOptionSectionResponse,
    ScheduleRepairSuggestionResponse,
    ScheduleScoreBreakdownResponse,
    ScheduleWarningResponse,
    SectionMeetingResponse,
    SectionMonitorAlertResponse,
    SectionMonitorAlertUpdateRequest,
    SectionMonitorSnapshotCompareRequest,
    SectionMonitorSnapshotCompareResponse,
    SectionMonitorSnapshotResponse,
    SectionMonitorTargetCreateRequest,
    SectionMonitorTargetResponse,
    SectionMonitorTargetUpdateRequest,
    SectionResponse,
    SourceMetadataResponse,
    StudentAcademicProgramResponse,
    StudentCourseAttemptResponse,
    StudentProfileResponse,
)
from app.schemas.reviewed_rules import (
    ReviewedRuleSetRecordResponse,
    ReviewedRuleSetResponse,
    RuleValidationResponse,
)
from app.security.auth import enforce_api_authorization
from app.services.academic_planner.engine import AcademicPlannerApplicationService
from app.services.academic_planner.exceptions import AcademicPlannerValidationError
from app.services.academic_scenarios.engine import AcademicScenarioApplicationService
from app.services.academic_scenarios.exceptions import AcademicScenarioValidationError
from app.services.academic_scenarios.result import ScenarioProgramInput
from app.services.course_eligibility.engine import CourseEligibilityApplicationService
from app.services.course_eligibility.exceptions import CourseEligibilityValidationError
from app.services.course_state.engine import effective_student_course_attempts
from app.services.data_imports.engine import STAGING_DISCLAIMERS, DataImportApplicationService
from app.services.data_imports.exceptions import DataImportValidationError
from app.services.data_review.engine import DataReviewApplicationService
from app.services.data_review.exceptions import DataReviewValidationError
from app.services.data_review.result import AppliedImportedRecordResult, DataReviewApplicationResult
from app.services.degree_audit.exceptions import DegreeAuditValidationError
from app.services.degree_audit.persistence import DegreeAuditApplicationService
from app.services.reviewed_rules.contracts import CatalogRuleSet, RuleLifecycle
from app.services.reviewed_rules.engine import ReviewedRuleService, validate_rule_set
from app.services.schedule_optimizer.engine import ScheduleOptimizerApplicationService
from app.services.schedule_optimizer.exceptions import ScheduleOptimizerValidationError
from app.services.section_monitoring.engine import (
    SectionMonitoringApplicationService,
    SnapshotCompareResult,
)
from app.services.section_monitoring.exceptions import SectionMonitoringValidationError

router = APIRouter(
    prefix="/api/v1",
    tags=["academic"],
    dependencies=[Depends(enforce_api_authorization)],
)
not_found_response = {"model": ErrorResponse}
DatabaseSession = Annotated[Session, Depends(get_db)]


def reviewed_rule_set_record_response(
    record: ReviewedRuleSetRecord,
) -> ReviewedRuleSetRecordResponse:
    return ReviewedRuleSetRecordResponse(
        rule_set=CatalogRuleSet.model_validate(record.payload),
        validation_state=record.validation_state,
        validation_errors=record.validation_errors,
        validation_warnings=record.validation_warnings,
    )


@router.post(
    "/reviewed-rule-sets",
    response_model=ReviewedRuleSetRecordResponse,
    status_code=201,
    summary="Stage a Program/Catalog rule set",
)
def stage_reviewed_rule_set(
    rule_set: ReviewedRuleSetResponse,
    db: DatabaseSession,
) -> ReviewedRuleSetRecordResponse:
    """Persist a draft only; imports never become reviewed or active implicitly."""

    result = validate_rule_set(rule_set)
    record = ReviewedRuleSetRecord(
        id=rule_set.rule_set_id,
        institution_identifier=rule_set.source.institution_id,
        program_identifier=rule_set.source.program_id,
        catalog_year=rule_set.source.catalog_year,
        version=rule_set.version,
        lifecycle=RuleLifecycle.DRAFT,
        source_title=rule_set.source.source_title,
        source_location=rule_set.source.source_location,
        source_evidence=rule_set.source.source_evidence,
        source_fingerprint=rule_set.source.checksum,
        payload=rule_set.model_copy(update={"lifecycle": RuleLifecycle.DRAFT}).model_dump(
            mode="json"
        ),
        validation_state=result.state.value,
        validation_errors=list(result.errors),
        validation_warnings=list(result.warnings),
        reviewer_confirmed=False,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return reviewed_rule_set_record_response(record)


@router.post(
    "/reviewed-rule-sets/{rule_set_id}/review",
    response_model=ReviewedRuleSetRecordResponse,
    summary="Explicitly review a staged rule set",
)
def review_staged_rule_set(
    rule_set_id: UUID,
    db: DatabaseSession,
) -> ReviewedRuleSetRecordResponse:
    record = db.get(ReviewedRuleSetRecord, rule_set_id)
    if record is None:
        raise not_found("ReviewedRuleSet", rule_set_id)
    reviewed = ReviewedRuleService().review(
        CatalogRuleSet.model_validate(record.payload), reviewer_confirmed=True
    )
    result = validate_rule_set(reviewed)
    record.payload = reviewed.model_dump(mode="json")
    record.lifecycle = RuleLifecycle.REVIEWED
    record.reviewer_confirmed = True
    record.reviewed_at = datetime.now(UTC)
    record.validation_state = result.state.value
    record.validation_errors = list(result.errors)
    record.validation_warnings = list(result.warnings)
    db.commit()
    db.refresh(record)
    return reviewed_rule_set_record_response(record)


@router.post(
    "/reviewed-rule-sets/{rule_set_id}/activate",
    response_model=ReviewedRuleSetRecordResponse,
    summary="Explicitly activate a reviewed rule set",
)
def activate_reviewed_rule_set(
    rule_set_id: UUID,
    db: DatabaseSession,
) -> ReviewedRuleSetRecordResponse:
    record = db.get(ReviewedRuleSetRecord, rule_set_id)
    if record is None:
        raise not_found("ReviewedRuleSet", rule_set_id)
    if record.lifecycle is not RuleLifecycle.REVIEWED or not record.reviewer_confirmed:
        raise HTTPException(
            status_code=409,
            detail="Only explicitly reviewed rules can be activated.",
        )
    rule_set = CatalogRuleSet.model_validate(record.payload)
    active_records = db.scalars(
        select(ReviewedRuleSetRecord).where(
            ReviewedRuleSetRecord.institution_identifier == record.institution_identifier,
            ReviewedRuleSetRecord.program_identifier == record.program_identifier,
            ReviewedRuleSetRecord.catalog_year == record.catalog_year,
            ReviewedRuleSetRecord.lifecycle == RuleLifecycle.ACTIVE,
        )
    ).all()
    if active_records:
        supersedes = rule_set.supersedes_rule_set_id
        if supersedes is None or all(active.id != supersedes for active in active_records):
            raise HTTPException(
                status_code=409,
                detail="An active version exists; provide its ID as supersedes_rule_set_id.",
            )
        for active in active_records:
            active.lifecycle = RuleLifecycle.SUPERSEDED
    activated = ReviewedRuleService().activate(rule_set)
    record.payload = activated.model_dump(mode="json")
    record.lifecycle = RuleLifecycle.ACTIVE
    record.activated_at = datetime.now(UTC)
    db.commit()
    db.refresh(record)
    return reviewed_rule_set_record_response(record)


@router.post(
    "/reviewed-rule-sets/validate",
    response_model=RuleValidationResponse,
    summary="Validate a staged Program/Catalog rule set",
)
def validate_reviewed_rule_set(rule_set: ReviewedRuleSetResponse) -> RuleValidationResponse:
    """Validate staged rules without persisting, reviewing, or activating them."""

    result = validate_rule_set(rule_set)
    return RuleValidationResponse(
        rule_set_id=str(rule_set.rule_set_id),
        state=result.state.value,
        errors=list(result.errors),
        warnings=list(result.warnings),
    )


class SourceRecord(Protocol):
    source_type: SourceType
    is_official: bool
    source_reference: str | None
    source_retrieved_at: datetime | None
    source_confidence: str | None


def source_response(record: SourceRecord) -> SourceMetadataResponse:
    return SourceMetadataResponse(
        source_type=record.source_type.value,
        is_official=record.is_official,
        source_reference=record.source_reference,
        source_retrieved_at=record.source_retrieved_at,
        source_confidence=record.source_confidence,
    )


def not_found(resource: str, resource_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "code": "not_found",
            "message": f"{resource} {resource_id} was not found.",
        },
    )


def institution_response(institution: Institution) -> InstitutionResponse:
    return InstitutionResponse(
        id=institution.id,
        code=institution.code,
        name=institution.name,
        country=institution.country,
        timezone=institution.timezone,
        source=source_response(institution),
    )


def campus_response(campus: Campus) -> CampusResponse:
    return CampusResponse(
        id=campus.id,
        institution_id=campus.institution_id,
        code=campus.code,
        name=campus.name,
        location=campus.location,
        source=source_response(campus),
    )


def academic_program_response(program: AcademicProgram) -> AcademicProgramResponse:
    return AcademicProgramResponse(
        id=program.id,
        institution_id=program.institution_id,
        code=program.code,
        name=program.name,
        program_type=program.program_type.value,
        degree_level=program.degree_level.value,
        source=source_response(program),
    )


def course_response(course: Course) -> CourseResponse:
    return CourseResponse(
        id=course.id,
        institution_id=course.institution_id,
        subject_code=course.subject_code,
        course_number=course.course_number,
        title=course.title,
        description=course.description,
        credits_min=course.credits_min,
        credits_max=course.credits_max,
        course_level=course.course_level,
        repeatable=course.repeatable,
        source=source_response(course),
    )


def section_response(section: Section) -> SectionResponse:
    return SectionResponse(
        id=section.id,
        institution_id=section.institution_id,
        course_id=section.course_id,
        term_id=section.term_id,
        campus_id=section.campus_id,
        section_code=section.section_code,
        external_reference=section.external_reference,
        title_override=section.title_override,
        credits=section.credits,
        status=section.status.value,
        modality=section.modality.value,
        capacity=section.capacity,
        available_seats=section.available_seats,
        waitlist_capacity=section.waitlist_capacity,
        waitlist_available=section.waitlist_available,
        instructor_display=section.instructor_display,
        last_synced_at=section.last_synced_at,
        source=source_response(section),
    )


def section_meeting_response(meeting: SectionMeeting) -> SectionMeetingResponse:
    return SectionMeetingResponse(
        id=meeting.id,
        section_id=meeting.section_id,
        meeting_type=meeting.meeting_type.value,
        day_of_week=meeting.day_of_week.value if meeting.day_of_week else None,
        start_time=meeting.start_time.isoformat(timespec="minutes") if meeting.start_time else None,
        end_time=meeting.end_time.isoformat(timespec="minutes") if meeting.end_time else None,
        start_date=meeting.start_date,
        end_date=meeting.end_date,
        building=meeting.building,
        room=meeting.room,
        timezone=meeting.timezone,
        is_arranged=meeting.is_arranged,
        is_online=meeting.is_online,
        display_order=meeting.display_order,
        source=source_response(meeting),
    )


def course_rule_response(rule: CourseRule) -> CourseRuleResponse:
    return CourseRuleResponse(
        id=rule.id,
        institution_id=rule.institution_id,
        course_id=rule.course_id,
        section_id=rule.section_id,
        rule_type=rule.rule_type.value,
        name=rule.name,
        description=rule.description,
        effective_term_id=rule.effective_term_id,
        expiration_term_id=rule.expiration_term_id,
        requires_manual_confirmation=rule.requires_manual_confirmation,
        source=source_response(rule),
    )


def offering_pattern_response(pattern: CourseOfferingPattern) -> CourseOfferingPatternResponse:
    return CourseOfferingPatternResponse(
        id=pattern.id,
        institution_id=pattern.institution_id,
        course_id=pattern.course_id,
        campus_id=pattern.campus_id,
        term_type=pattern.term_type.value,
        frequency_type=pattern.frequency_type.value,
        effective_term_id=pattern.effective_term_id,
        expiration_term_id=pattern.expiration_term_id,
        confidence_level=pattern.confidence_level,
        notes=pattern.notes,
        source=source_response(pattern),
    )


def expression_node_response(
    node: CourseRuleExpression,
    children_by_parent: dict[UUID, list[CourseRuleExpression]],
) -> CourseRuleExpressionNodeResponse:
    children = sorted(
        children_by_parent[node.id],
        key=lambda child: (child.display_order, child.node_type.value, str(child.id)),
    )
    return CourseRuleExpressionNodeResponse(
        id=node.id,
        parent_id=node.parent_id,
        node_type=node.node_type.value,
        display_order=node.display_order,
        referenced_course_id=node.referenced_course_id,
        minimum_grade=node.minimum_grade,
        minimum_completed_credits=node.minimum_completed_credits,
        class_standing=node.class_standing,
        referenced_program_id=node.referenced_program_id,
        referenced_campus_id=node.referenced_campus_id,
        permission_type=node.permission_type,
        text_value=node.text_value,
        children=[expression_node_response(child, children_by_parent) for child in children],
        source=source_response(node),
    )


def degree_audit_run_response(run: DegreeAuditRun) -> DegreeAuditRunResponse:
    return DegreeAuditRunResponse(
        id=run.id,
        student_profile_id=run.student_profile_id,
        program_version_id=run.program_version_id,
        status=run.status.value,
        engine_version=run.engine_version,
        calculation_mode=run.calculation_mode.value,
        started_at=run.started_at,
        completed_at=run.completed_at,
        total_required_credits=run.total_required_credits,
        completed_credits=run.completed_credits,
        in_progress_credits=run.in_progress_credits,
        planned_credits=run.planned_credits,
        remaining_credits=run.remaining_credits,
        completion_percentage=run.completion_percentage,
        source_snapshot_hash=run.source_snapshot_hash,
        reviewed_rule_set_id=run.reviewed_rule_set_id,
        rule_resolution_state=run.rule_resolution_state,
        rule_source_reference=run.rule_source_reference,
        rule_catalog_year=run.rule_catalog_year,
        rule_resolution_explanation=run.rule_resolution_explanation,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def degree_audit_warning_response(warning: DegreeAuditWarning) -> DegreeAuditWarningResponse:
    return DegreeAuditWarningResponse(
        id=warning.id,
        degree_audit_run_id=warning.degree_audit_run_id,
        requirement_evaluation_id=warning.requirement_evaluation_id,
        warning_code=warning.warning_code,
        severity=warning.severity.value,
        message=warning.message,
        requires_advisor_confirmation=warning.requires_advisor_confirmation,
        created_at=warning.created_at,
    )


def audit_course_application_response(
    application: AuditCourseApplication,
    course: Course | None,
) -> AuditCourseApplicationResponse:
    return AuditCourseApplicationResponse(
        id=application.id,
        course_id=application.course_id,
        course_code=f"{course.subject_code} {course.course_number}" if course else None,
        course_title=course.title if course else None,
        student_course_attempt_id=application.student_course_attempt_id,
        transfer_credit_id=application.transfer_credit_id,
        course_waiver_id=application.course_waiver_id,
        course_substitution_id=application.course_substitution_id,
        application_type=application.application_type.value,
        credit_amount=application.credit_amount,
        grade=application.grade,
        is_completed=application.is_completed,
        is_in_progress=application.is_in_progress,
        is_planned=application.is_planned,
        is_shared=application.is_shared,
        explanation=application.explanation,
    )


def requirement_evaluation_response(
    evaluation: RequirementEvaluation,
    requirement: RequirementNode,
    applications: list[AuditCourseApplicationResponse],
    warnings: list[DegreeAuditWarningResponse],
) -> RequirementEvaluationResponse:
    return RequirementEvaluationResponse(
        id=evaluation.id,
        degree_audit_run_id=evaluation.degree_audit_run_id,
        requirement_node_id=evaluation.requirement_node_id,
        requirement_code=requirement.code,
        requirement_name=requirement.name,
        requirement_type=requirement.requirement_type.value,
        status=evaluation.status.value,
        required_credits=evaluation.required_credits,
        satisfied_credits=evaluation.satisfied_credits,
        remaining_credits=evaluation.remaining_credits,
        required_courses=evaluation.required_courses,
        satisfied_courses=evaluation.satisfied_courses,
        remaining_courses=evaluation.remaining_courses,
        minimum_grade=evaluation.minimum_grade,
        explanation=evaluation.explanation,
        display_order=evaluation.display_order,
        applications=applications,
        warnings=warnings,
    )


def academic_scenario_response(scenario: AcademicPlanScenario) -> AcademicScenarioResponse:
    return AcademicScenarioResponse(
        id=scenario.id,
        student_profile_id=scenario.student_profile_id,
        name=scenario.name,
        scenario_type=scenario.scenario_type.value,
        status=scenario.status.value,
        base_program_version_id=scenario.base_program_version_id,
        engine_version=scenario.engine_version,
        created_at=scenario.created_at,
        updated_at=scenario.updated_at,
        completed_at=scenario.completed_at,
    )


def scenario_program_response(
    scenario_program: ScenarioProgram,
    version: ProgramVersion,
    program: AcademicProgram,
) -> ScenarioProgramResponse:
    return ScenarioProgramResponse(
        id=scenario_program.id,
        academic_plan_scenario_id=scenario_program.academic_plan_scenario_id,
        program_version_id=scenario_program.program_version_id,
        relationship_type=scenario_program.relationship_type.value,
        is_existing_program=scenario_program.is_existing_program,
        is_hypothetical=scenario_program.is_hypothetical,
        priority=scenario_program.priority,
        program_code=program.code,
        program_name=program.name,
        source=source_response(version),
        created_at=scenario_program.created_at,
    )


def scenario_course_allocation_response(
    allocation: ScenarioCourseAllocation,
    course: Course | None,
    requirement: RequirementNode | None,
) -> ScenarioCourseAllocationResponse:
    return ScenarioCourseAllocationResponse(
        id=allocation.id,
        academic_plan_scenario_id=allocation.academic_plan_scenario_id,
        student_course_attempt_id=allocation.student_course_attempt_id,
        transfer_credit_id=allocation.transfer_credit_id,
        course_waiver_id=allocation.course_waiver_id,
        course_substitution_id=allocation.course_substitution_id,
        course_id=allocation.course_id,
        course_code=f"{course.subject_code} {course.course_number}" if course else None,
        course_title=course.title if course else None,
        program_version_id=allocation.program_version_id,
        requirement_node_id=allocation.requirement_node_id,
        requirement_code=requirement.code if requirement else None,
        allocation_type=allocation.allocation_type.value,
        credit_amount=allocation.credit_amount,
        is_shared=allocation.is_shared,
        is_unique_to_program=allocation.is_unique_to_program,
        allocation_rank=allocation.allocation_rank,
        reason_code=allocation.reason_code,
        explanation=allocation.explanation,
        created_at=allocation.created_at,
    )


def scenario_warning_response(warning: ScenarioWarning) -> ScenarioWarningResponse:
    return ScenarioWarningResponse(
        id=warning.id,
        academic_plan_scenario_id=warning.academic_plan_scenario_id,
        scenario_program_id=warning.scenario_program_id,
        warning_code=warning.warning_code,
        severity=warning.severity.value,
        message=warning.message,
        requires_advisor_confirmation=warning.requires_advisor_confirmation,
        created_at=warning.created_at,
    )


def scenario_comparison_response(
    snapshot: ScenarioComparisonSnapshot,
) -> ScenarioComparisonSnapshotResponse:
    return ScenarioComparisonSnapshotResponse(
        academic_plan_scenario_id=snapshot.academic_plan_scenario_id,
        completed_credits=snapshot.completed_credits,
        in_progress_credits=snapshot.in_progress_credits,
        planned_credits=snapshot.planned_credits,
        remaining_requirement_credits=snapshot.remaining_requirement_credits,
        shared_credits=snapshot.shared_credits,
        unique_secondary_credits=snapshot.unique_secondary_credits,
        estimated_additional_credits=snapshot.estimated_additional_credits,
        unresolved_requirements=snapshot.unresolved_requirements,
        manual_review_count=snapshot.manual_review_count,
        completion_percentage=snapshot.completion_percentage,
        is_estimate=snapshot.is_estimate,
        created_at=snapshot.created_at,
    )


def eligibility_expression_response(
    evaluation: RuleExpressionEvaluation,
    expression: CourseRuleExpression,
) -> RuleExpressionEvaluationResponse:
    return RuleExpressionEvaluationResponse(
        id=evaluation.id,
        rule_evaluation_id=evaluation.rule_evaluation_id,
        course_rule_expression_id=evaluation.course_rule_expression_id,
        node_type=expression.node_type.value,
        result=evaluation.result.value,
        actual_value=evaluation.actual_value,
        expected_value=evaluation.expected_value,
        matched_course_id=evaluation.matched_course_id,
        matched_attempt_id=evaluation.matched_attempt_id,
        reason_code=evaluation.reason_code,
        explanation=evaluation.explanation,
        created_at=evaluation.created_at,
    )


def eligibility_rule_response(
    evaluation: RuleEvaluation,
    expressions: list[RuleExpressionEvaluationResponse],
) -> RuleEvaluationResponse:
    return RuleEvaluationResponse(
        id=evaluation.id,
        eligibility_check_run_id=evaluation.eligibility_check_run_id,
        course_rule_id=evaluation.course_rule_id,
        result=evaluation.result.value,
        rule_type=evaluation.rule_type.value,
        explanation=evaluation.explanation,
        display_order=evaluation.display_order,
        expressions=expressions,
        created_at=evaluation.created_at,
    )


def eligibility_warning_response(warning: EligibilityWarning) -> EligibilityWarningResponse:
    return EligibilityWarningResponse(
        id=warning.id,
        eligibility_check_run_id=warning.eligibility_check_run_id,
        rule_evaluation_id=warning.rule_evaluation_id,
        warning_code=warning.warning_code,
        severity=warning.severity.value,
        message=warning.message,
        requires_advisor_confirmation=warning.requires_advisor_confirmation,
        created_at=warning.created_at,
    )


def eligibility_reason_response(
    expression: RuleExpressionEvaluationResponse,
    course_rule_id: UUID | None,
) -> EligibilityReasonResponse:
    return EligibilityReasonResponse(
        reason_code=expression.reason_code,
        explanation=expression.explanation,
        course_rule_id=course_rule_id,
        course_rule_expression_id=expression.course_rule_expression_id,
        referenced_entity_type="course" if expression.matched_course_id else None,
        referenced_entity_id=expression.matched_course_id,
        expected_value=expression.expected_value,
        actual_value=expression.actual_value,
    )


def reviewed_rule_reason_response(reason: dict[str, object]) -> EligibilityReasonResponse:
    return EligibilityReasonResponse.model_validate(reason)


def registration_availability_response(
    section: Section | None,
) -> RegistrationAvailabilityResponse | None:
    if section is None:
        return None
    return RegistrationAvailabilityResponse(
        section_status=section.status.value,
        available_seats=section.available_seats,
        waitlist_available=section.waitlist_available,
        availability_note="Section availability is reported separately from academic eligibility.",
    )


def eligibility_check_response(
    run: EligibilityCheckRun,
    db: Session,
) -> CourseEligibilityCheckResponse:
    rule_evaluations = db.scalars(
        select(RuleEvaluation)
        .where(RuleEvaluation.eligibility_check_run_id == run.id)
        .order_by(RuleEvaluation.display_order, RuleEvaluation.id)
    ).all()
    rule_ids = [evaluation.id for evaluation in rule_evaluations]
    expression_responses_by_rule: dict[UUID, list[RuleExpressionEvaluationResponse]] = defaultdict(
        list
    )
    if rule_ids:
        rows = db.execute(
            select(RuleExpressionEvaluation, CourseRuleExpression)
            .join(
                CourseRuleExpression,
                RuleExpressionEvaluation.course_rule_expression_id == CourseRuleExpression.id,
            )
            .where(RuleExpressionEvaluation.rule_evaluation_id.in_(rule_ids))
            .order_by(
                RuleExpressionEvaluation.rule_evaluation_id,
                CourseRuleExpression.display_order,
                CourseRuleExpression.node_type,
                RuleExpressionEvaluation.id,
            )
        ).all()
        for expression_evaluation, expression in rows:
            expression_responses_by_rule[expression_evaluation.rule_evaluation_id].append(
                eligibility_expression_response(expression_evaluation, expression)
            )

    rule_responses = [
        eligibility_rule_response(evaluation, expression_responses_by_rule[evaluation.id])
        for evaluation in rule_evaluations
    ]
    course_rule_by_rule_eval = {rule.id: rule.course_rule_id for rule in rule_evaluations}
    expression_responses = [
        expression for rule in rule_responses for expression in rule.expressions
    ]
    blocking_reasons = [
        eligibility_reason_response(
            expression,
            course_rule_by_rule_eval.get(expression.rule_evaluation_id),
        )
        for expression in expression_responses
        if expression.result == "NOT_SATISFIED"
    ]
    conditional_reasons = [
        eligibility_reason_response(
            expression,
            course_rule_by_rule_eval.get(expression.rule_evaluation_id),
        )
        for expression in expression_responses
        if expression.result == "CONDITIONALLY_SATISFIED"
    ]
    permissions_required = [
        eligibility_reason_response(
            expression,
            course_rule_by_rule_eval.get(expression.rule_evaluation_id),
        )
        for expression in expression_responses
        if expression.result == "PERMISSION_REQUIRED"
    ]
    manual_review_reasons = [
        eligibility_reason_response(
            expression,
            course_rule_by_rule_eval.get(expression.rule_evaluation_id),
        )
        for expression in expression_responses
        if expression.result == "MANUAL_REVIEW_REQUIRED"
    ]
    reviewed_rule_reasons = [
        reviewed_rule_reason_response(reason) for reason in (run.reviewed_rule_reasons or [])
    ]
    corequisites_to_add = [
        expression.matched_course_id
        for expression in expression_responses
        if expression.matched_course_id is not None
        and expression.reason_code in {"COREQUISITE_MUST_ENROLL", "COREQUISITE_CONCURRENT_PLAN"}
    ]
    unique_corequisites_to_add = list(dict.fromkeys(corequisites_to_add))
    corequisite_summary = (
        CorequisiteSummaryResponse(
            required_corequisite_courses=unique_corequisites_to_add,
            already_completed=[],
            currently_in_progress=[],
            must_enroll_concurrently=unique_corequisites_to_add,
        )
        if unique_corequisites_to_add
        else None
    )
    warnings = db.scalars(
        select(EligibilityWarning)
        .where(EligibilityWarning.eligibility_check_run_id == run.id)
        .order_by(EligibilityWarning.severity, EligibilityWarning.created_at, EligibilityWarning.id)
    ).all()
    section = db.get(Section, run.section_id) if run.section_id is not None else None
    return CourseEligibilityCheckResponse(
        id=run.id,
        institution_id=run.institution_id,
        student_profile_id=run.student_profile_id,
        course_id=run.course_id,
        section_id=run.section_id,
        target_term_id=run.target_term_id,
        mode=run.mode.value,
        status=run.status.value,
        engine_version=run.engine_version,
        overall_result=run.overall_result.value,
        academic_eligibility_result=run.academic_eligibility_result.value,
        started_at=run.started_at,
        completed_at=run.completed_at,
        source_snapshot_hash=run.source_snapshot_hash,
        reviewed_rule_set_id=run.reviewed_rule_set_id,
        rule_resolution_state=run.rule_resolution_state,
        rule_source_reference=run.rule_source_reference,
        rule_catalog_year=run.rule_catalog_year,
        rule_resolution_explanation=run.rule_resolution_explanation,
        rule_evaluations=rule_responses,
        blocking_reasons=blocking_reasons,
        conditional_reasons=conditional_reasons,
        permissions_required=permissions_required,
        manual_review_reasons=manual_review_reasons,
        reviewed_rule_reasons=reviewed_rule_reasons,
        corequisites_to_add=unique_corequisites_to_add,
        corequisite_summary=corequisite_summary,
        registration_availability=registration_availability_response(section),
        warnings=[eligibility_warning_response(warning) for warning in warnings],
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def academic_plan_run_response(run: AcademicPlanRun) -> AcademicPlanRunResponse:
    return AcademicPlanRunResponse(
        id=run.id,
        student_profile_id=run.student_profile_id,
        program_version_id=run.program_version_id,
        academic_plan_scenario_id=run.academic_plan_scenario_id,
        planning_mode=run.planning_mode.value,
        status=run.status.value,
        engine_version=run.engine_version,
        start_term_id=run.start_term_id,
        target_completion_term_id=run.target_completion_term_id,
        minimum_credits_per_term=run.minimum_credits_per_term,
        maximum_credits_per_term=run.maximum_credits_per_term,
        preferred_credits_per_term=run.preferred_credits_per_term,
        completed_at=run.completed_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def academic_plan_term_response(
    plan_term: AcademicPlanTerm,
    term: AcademicTerm,
) -> AcademicPlanTermResponse:
    return AcademicPlanTermResponse(
        id=plan_term.id,
        academic_plan_run_id=plan_term.academic_plan_run_id,
        term_id=plan_term.term_id,
        term_code=term.term_code,
        sequence_index=plan_term.sequence_index,
        planned_credits=plan_term.planned_credits,
        status=plan_term.status.value,
        explanation=plan_term.explanation,
        created_at=plan_term.created_at,
    )


def academic_plan_course_response(
    plan_course: AcademicPlanCourse,
    plan_term: AcademicPlanTerm,
    term: AcademicTerm,
    course: Course,
    requirement: RequirementNode | None,
) -> AcademicPlanCourseResponse:
    return AcademicPlanCourseResponse(
        id=plan_course.id,
        academic_plan_term_id=plan_course.academic_plan_term_id,
        term_id=plan_term.term_id,
        term_code=term.term_code,
        course_id=plan_course.course_id,
        course_code=f"{course.subject_code} {course.course_number}",
        course_title=course.title,
        requirement_node_id=plan_course.requirement_node_id,
        requirement_code=requirement.code if requirement is not None else None,
        source=plan_course.source.value,
        priority_rank=plan_course.priority_rank,
        credits=plan_course.credits,
        eligibility_result=plan_course.eligibility_result.value,
        planning_status=plan_course.planning_status.value,
        reason_code=plan_course.reason_code,
        explanation=plan_course.explanation,
        created_at=plan_course.created_at,
    )


def academic_plan_coverage_response(
    coverage: AcademicPlanRequirementCoverage,
    requirement: RequirementNode,
) -> AcademicPlanRequirementCoverageResponse:
    return AcademicPlanRequirementCoverageResponse(
        id=coverage.id,
        academic_plan_run_id=coverage.academic_plan_run_id,
        academic_plan_course_id=coverage.academic_plan_course_id,
        requirement_node_id=coverage.requirement_node_id,
        requirement_code=requirement.code,
        coverage_type=coverage.coverage_type.value,
        credits=coverage.credits,
        created_at=coverage.created_at,
    )


def academic_plan_warning_response(
    warning: AcademicPlanWarning,
) -> AcademicPlanWarningResponse:
    return AcademicPlanWarningResponse(
        id=warning.id,
        academic_plan_run_id=warning.academic_plan_run_id,
        academic_plan_term_id=warning.academic_plan_term_id,
        academic_plan_course_id=warning.academic_plan_course_id,
        warning_code=warning.warning_code,
        severity=warning.severity.value,
        message=warning.message,
        requires_advisor_confirmation=warning.requires_advisor_confirmation,
        created_at=warning.created_at,
    )


def academic_plan_terms_response(
    plan_id: UUID,
    db: Session,
) -> list[AcademicPlanTermResponse]:
    rows = db.execute(
        select(AcademicPlanTerm, AcademicTerm)
        .join(AcademicTerm, AcademicPlanTerm.term_id == AcademicTerm.id)
        .where(AcademicPlanTerm.academic_plan_run_id == plan_id)
        .order_by(AcademicPlanTerm.sequence_index, AcademicTerm.term_code)
    ).all()
    return [academic_plan_term_response(plan_term, term) for plan_term, term in rows]


def academic_plan_courses_response(
    plan_id: UUID,
    db: Session,
) -> list[AcademicPlanCourseResponse]:
    rows = db.execute(
        select(AcademicPlanCourse, AcademicPlanTerm, AcademicTerm, Course, RequirementNode)
        .join(AcademicPlanTerm, AcademicPlanCourse.academic_plan_term_id == AcademicPlanTerm.id)
        .join(AcademicTerm, AcademicPlanTerm.term_id == AcademicTerm.id)
        .join(Course, AcademicPlanCourse.course_id == Course.id)
        .outerjoin(RequirementNode, AcademicPlanCourse.requirement_node_id == RequirementNode.id)
        .where(AcademicPlanTerm.academic_plan_run_id == plan_id)
        .order_by(
            AcademicPlanTerm.sequence_index,
            AcademicPlanCourse.priority_rank,
            Course.subject_code,
            Course.course_number,
        )
    ).all()
    return [
        academic_plan_course_response(plan_course, plan_term, term, course, requirement)
        for plan_course, plan_term, term, course, requirement in rows
    ]


def academic_plan_coverage_responses(
    plan_id: UUID,
    db: Session,
) -> list[AcademicPlanRequirementCoverageResponse]:
    rows = db.execute(
        select(AcademicPlanRequirementCoverage, RequirementNode)
        .join(
            RequirementNode,
            AcademicPlanRequirementCoverage.requirement_node_id == RequirementNode.id,
        )
        .where(AcademicPlanRequirementCoverage.academic_plan_run_id == plan_id)
        .order_by(
            AcademicPlanRequirementCoverage.created_at,
            AcademicPlanRequirementCoverage.id,
        )
    ).all()
    return [
        academic_plan_coverage_response(coverage, requirement) for coverage, requirement in rows
    ]


def academic_plan_warnings_response(
    plan_id: UUID,
    db: Session,
) -> list[AcademicPlanWarningResponse]:
    warnings = db.scalars(
        select(AcademicPlanWarning)
        .where(AcademicPlanWarning.academic_plan_run_id == plan_id)
        .order_by(
            AcademicPlanWarning.severity,
            AcademicPlanWarning.created_at,
            AcademicPlanWarning.id,
        )
    ).all()
    return [academic_plan_warning_response(warning) for warning in warnings]


def academic_plan_detail_response(
    run: AcademicPlanRun,
    db: Session,
) -> AcademicPlanDetailResponse:
    base = academic_plan_run_response(run).model_dump()
    return AcademicPlanDetailResponse(
        **base,
        terms=academic_plan_terms_response(run.id, db),
        planned_courses=academic_plan_courses_response(run.id, db),
        requirement_coverage=academic_plan_coverage_responses(run.id, db),
        warnings=academic_plan_warnings_response(run.id, db),
    )


def schedule_run_response(run: ScheduleOptimizationRun) -> ScheduleOptimizationRunResponse:
    return ScheduleOptimizationRunResponse(
        id=run.id,
        student_profile_id=run.student_profile_id,
        term_id=run.term_id,
        academic_plan_run_id=run.academic_plan_run_id,
        planning_mode=run.planning_mode.value,
        status=run.status.value,
        engine_version=run.engine_version,
        minimum_credits=run.minimum_credits,
        maximum_credits=run.maximum_credits,
        preferred_credits=run.preferred_credits,
        requested_option_count=run.requested_option_count,
        completed_at=run.completed_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def schedule_constraint_response(
    constraint_set: ScheduleConstraintSet,
) -> ScheduleConstraintSetResponse:
    return ScheduleConstraintSetResponse(
        id=constraint_set.id,
        schedule_optimization_run_id=constraint_set.schedule_optimization_run_id,
        excluded_days=constraint_set.excluded_days,
        unavailable_time_blocks=constraint_set.unavailable_time_blocks,
        earliest_start_time=(
            constraint_set.earliest_start_time.isoformat(timespec="minutes")
            if constraint_set.earliest_start_time
            else None
        ),
        latest_end_time=(
            constraint_set.latest_end_time.isoformat(timespec="minutes")
            if constraint_set.latest_end_time
            else None
        ),
        minimum_gap_minutes=constraint_set.minimum_gap_minutes,
        maximum_gap_minutes=constraint_set.maximum_gap_minutes,
        candidate_course_ids=constraint_set.candidate_course_ids,
        allowed_modalities=constraint_set.allowed_modalities,
        excluded_modalities=constraint_set.excluded_modalities,
        required_course_ids=constraint_set.required_course_ids,
        excluded_course_ids=constraint_set.excluded_course_ids,
        required_section_ids=constraint_set.required_section_ids,
        excluded_section_ids=constraint_set.excluded_section_ids,
        prefer_online=constraint_set.prefer_online,
        prefer_compact_schedule=constraint_set.prefer_compact_schedule,
        prefer_fewer_days=constraint_set.prefer_fewer_days,
        prefer_in_person=constraint_set.prefer_in_person,
        avoid_early_start=constraint_set.avoid_early_start,
        avoid_late_end=constraint_set.avoid_late_end,
        allow_permission_required=constraint_set.allow_permission_required,
        preference_weights=constraint_set.preference_weights,
        course_priority_weights=constraint_set.course_priority_weights,
        section_priority_weights=constraint_set.section_priority_weights,
        prefer_no_gaps=constraint_set.prefer_no_gaps,
        prefer_morning=constraint_set.prefer_morning,
        prefer_afternoon=constraint_set.prefer_afternoon,
        diversity_mode=constraint_set.diversity_mode,
        allow_partial_options=constraint_set.allow_partial_options,
        max_combinations=constraint_set.max_combinations,
        created_at=constraint_set.created_at,
    )


def schedule_option_section_response(
    selected: ScheduleOptionSection,
    section: Section,
    course: Course,
    meetings: list[SectionMeeting],
) -> ScheduleOptionSectionResponse:
    return ScheduleOptionSectionResponse(
        id=selected.id,
        schedule_option_id=selected.schedule_option_id,
        section_id=selected.section_id,
        course_id=selected.course_id,
        course_code=f"{course.subject_code} {course.course_number}",
        course_title=course.title,
        section_code=section.section_code,
        section_status=section.status.value,
        modality=section.modality.value,
        credits=selected.credits,
        eligibility_result=selected.eligibility_result.value,
        selection_reason=selected.selection_reason,
        meetings=[section_meeting_response(meeting) for meeting in meetings],
        created_at=selected.created_at,
    )


def schedule_option_response(
    option: ScheduleOption,
    selected_sections: list[ScheduleOptionSectionResponse],
) -> ScheduleOptionResponse:
    score_breakdown = ScheduleScoreBreakdownResponse(
        total_score=option.total_score,
        credit_score=option.credit_score,
        compactness_score=option.compactness_score,
        days_score=option.days_score,
        gap_score=option.gap_score,
        modality_score=option.modality_score,
        time_preference_score=option.time_preference_score,
        priority_score=option.priority_score,
        penalty_score=option.penalty_score,
        score_explanation=option.score_explanation,
    )
    return ScheduleOptionResponse(
        id=option.id,
        schedule_optimization_run_id=option.schedule_optimization_run_id,
        option_rank=option.option_rank,
        status=option.status.value,
        total_credits=option.total_credits,
        class_days_count=option.class_days_count,
        earliest_start_time=(
            option.earliest_start_time.isoformat(timespec="minutes")
            if option.earliest_start_time
            else None
        ),
        latest_end_time=(
            option.latest_end_time.isoformat(timespec="minutes") if option.latest_end_time else None
        ),
        total_gap_minutes=option.total_gap_minutes,
        score=option.score,
        total_score=option.total_score,
        credit_score=option.credit_score,
        compactness_score=option.compactness_score,
        days_score=option.days_score,
        gap_score=option.gap_score,
        modality_score=option.modality_score,
        time_preference_score=option.time_preference_score,
        priority_score=option.priority_score,
        penalty_score=option.penalty_score,
        score_explanation=option.score_explanation,
        score_breakdown=score_breakdown,
        diversity_rank=option.diversity_rank,
        difference_summary=option.difference_summary,
        shared_section_count_with_previous_option=(
            option.shared_section_count_with_previous_option
        ),
        explanation=option.explanation,
        selected_sections=selected_sections,
        created_at=option.created_at,
    )


def schedule_conflict_response(conflict: ScheduleConflict) -> ScheduleConflictResponse:
    return ScheduleConflictResponse(
        id=conflict.id,
        schedule_optimization_run_id=conflict.schedule_optimization_run_id,
        schedule_option_id=conflict.schedule_option_id,
        conflict_type=conflict.conflict_type.value,
        section_id=conflict.section_id,
        other_section_id=conflict.other_section_id,
        day_of_week=conflict.day_of_week.value if conflict.day_of_week else None,
        start_time=(
            conflict.start_time.isoformat(timespec="minutes") if conflict.start_time else None
        ),
        end_time=conflict.end_time.isoformat(timespec="minutes") if conflict.end_time else None,
        message=conflict.message,
        created_at=conflict.created_at,
    )


def schedule_warning_response(warning: ScheduleWarning) -> ScheduleWarningResponse:
    return ScheduleWarningResponse(
        id=warning.id,
        schedule_optimization_run_id=warning.schedule_optimization_run_id,
        schedule_option_id=warning.schedule_option_id,
        warning_code=warning.warning_code,
        severity=warning.severity.value,
        message=warning.message,
        requires_advisor_confirmation=warning.requires_advisor_confirmation,
        created_at=warning.created_at,
    )


def schedule_repair_suggestion_response(
    suggestion: ScheduleRepairSuggestion,
) -> ScheduleRepairSuggestionResponse:
    return ScheduleRepairSuggestionResponse(
        id=suggestion.id,
        schedule_optimization_run_id=suggestion.schedule_optimization_run_id,
        suggestion_type=suggestion.suggestion_type,
        affected_constraint=suggestion.affected_constraint,
        affected_course_id=suggestion.affected_course_id,
        affected_section_id=suggestion.affected_section_id,
        estimated_impact=suggestion.estimated_impact,
        message=suggestion.message,
        requires_advisor_confirmation=suggestion.requires_advisor_confirmation,
        created_at=suggestion.created_at,
    )


def schedule_options_response(
    run_id: UUID,
    db: Session,
) -> list[ScheduleOptionResponse]:
    options = db.scalars(
        select(ScheduleOption)
        .where(ScheduleOption.schedule_optimization_run_id == run_id)
        .order_by(ScheduleOption.option_rank, ScheduleOption.id)
    ).all()
    responses: list[ScheduleOptionResponse] = []
    for option in options:
        rows = db.execute(
            select(ScheduleOptionSection, Section, Course)
            .join(Section, ScheduleOptionSection.section_id == Section.id)
            .join(Course, ScheduleOptionSection.course_id == Course.id)
            .where(ScheduleOptionSection.schedule_option_id == option.id)
            .order_by(Course.subject_code, Course.course_number, Section.section_code)
        ).all()
        section_ids = [selected.section_id for selected, _section, _course in rows]
        meeting_rows: Sequence[SectionMeeting] = []
        if section_ids:
            meeting_rows = db.scalars(
                select(SectionMeeting)
                .where(SectionMeeting.section_id.in_(section_ids))
                .order_by(
                    SectionMeeting.section_id,
                    SectionMeeting.display_order,
                    SectionMeeting.id,
                )
            ).all()
        meetings_by_section: dict[UUID, list[SectionMeeting]] = defaultdict(list)
        for meeting in meeting_rows:
            meetings_by_section[meeting.section_id].append(meeting)
        selected_responses = [
            schedule_option_section_response(
                selected,
                section,
                course,
                meetings_by_section[selected.section_id],
            )
            for selected, section, course in rows
        ]
        responses.append(schedule_option_response(option, selected_responses))
    return responses


def schedule_conflicts_response(
    run_id: UUID,
    db: Session,
) -> list[ScheduleConflictResponse]:
    conflicts = db.scalars(
        select(ScheduleConflict)
        .where(ScheduleConflict.schedule_optimization_run_id == run_id)
        .order_by(ScheduleConflict.conflict_type, ScheduleConflict.created_at, ScheduleConflict.id)
    ).all()
    return [schedule_conflict_response(conflict) for conflict in conflicts]


def schedule_warnings_response(
    run_id: UUID,
    db: Session,
) -> list[ScheduleWarningResponse]:
    warnings = db.scalars(
        select(ScheduleWarning)
        .where(ScheduleWarning.schedule_optimization_run_id == run_id)
        .order_by(ScheduleWarning.severity, ScheduleWarning.created_at, ScheduleWarning.id)
    ).all()
    return [schedule_warning_response(warning) for warning in warnings]


def schedule_repair_suggestions_response(
    run_id: UUID,
    db: Session,
) -> list[ScheduleRepairSuggestionResponse]:
    suggestions = db.scalars(
        select(ScheduleRepairSuggestion)
        .where(ScheduleRepairSuggestion.schedule_optimization_run_id == run_id)
        .order_by(
            ScheduleRepairSuggestion.suggestion_type,
            ScheduleRepairSuggestion.created_at,
            ScheduleRepairSuggestion.id,
        )
    ).all()
    return [schedule_repair_suggestion_response(suggestion) for suggestion in suggestions]


def schedule_hard_constraint_results(
    constraint_set: ScheduleConstraintSet | None,
) -> list[dict[str, object]]:
    if constraint_set is None:
        return []
    return [
        {"constraint": "excluded_days", "result": "APPLIED", "value": constraint_set.excluded_days},
        {
            "constraint": "unavailable_time_blocks",
            "result": "APPLIED",
            "value": constraint_set.unavailable_time_blocks,
        },
        {
            "constraint": "required_section_ids",
            "result": "APPLIED",
            "value": constraint_set.required_section_ids,
        },
        {
            "constraint": "excluded_section_ids",
            "result": "APPLIED",
            "value": constraint_set.excluded_section_ids,
        },
        {
            "constraint": "allowed_modalities",
            "result": "APPLIED",
            "value": constraint_set.allowed_modalities,
        },
        {
            "constraint": "excluded_modalities",
            "result": "APPLIED",
            "value": constraint_set.excluded_modalities,
        },
    ]


def schedule_soft_preference_results(
    constraint_set: ScheduleConstraintSet | None,
) -> list[dict[str, object]]:
    if constraint_set is None:
        return []
    return [
        {"preference": "preference_weights", "value": constraint_set.preference_weights},
        {"preference": "course_priority_weights", "value": constraint_set.course_priority_weights},
        {
            "preference": "section_priority_weights",
            "value": constraint_set.section_priority_weights,
        },
        {"preference": "prefer_no_gaps", "value": constraint_set.prefer_no_gaps},
        {"preference": "prefer_morning", "value": constraint_set.prefer_morning},
        {"preference": "prefer_afternoon", "value": constraint_set.prefer_afternoon},
        {"preference": "diversity_mode", "value": constraint_set.diversity_mode},
    ]


def schedule_detail_response(
    run: ScheduleOptimizationRun,
    db: Session,
) -> ScheduleOptimizationDetailResponse:
    base = schedule_run_response(run).model_dump()
    constraint_set = db.scalar(
        select(ScheduleConstraintSet).where(
            ScheduleConstraintSet.schedule_optimization_run_id == run.id
        )
    )
    return ScheduleOptimizationDetailResponse(
        **base,
        constraint_set=(
            schedule_constraint_response(constraint_set) if constraint_set is not None else None
        ),
        options=schedule_options_response(run.id, db),
        conflicts=schedule_conflicts_response(run.id, db),
        warnings=schedule_warnings_response(run.id, db),
        repair_suggestions=schedule_repair_suggestions_response(run.id, db),
        hard_constraint_results=schedule_hard_constraint_results(constraint_set),
        soft_preference_results=schedule_soft_preference_results(constraint_set),
    )


def data_import_run_response(run: DataImportRun) -> DataImportRunResponse:
    return DataImportRunResponse(
        id=run.id,
        student_profile_id=run.student_profile_id,
        import_type=run.import_type.value,
        status=run.status.value,
        storage_strategy=run.storage_strategy.value,
        file_name=run.file_name,
        file_mime_type=run.file_mime_type,
        file_size_bytes=run.file_size_bytes,
        file_sha256=run.file_sha256,
        parser_version=run.parser_version,
        record_count=run.record_count,
        valid_record_count=run.valid_record_count,
        warning_count=run.warning_count,
        error_count=run.error_count,
        official_application_ready=run.official_application_ready,
        started_at=run.started_at,
        completed_at=run.completed_at,
        source=source_response(run),
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def section_monitor_target_response(
    target: SectionMonitorTarget,
    db: Session,
) -> SectionMonitorTargetResponse:
    latest_snapshot_created_at = db.scalar(
        select(func.max(SectionMonitorSnapshot.created_at)).where(
            SectionMonitorSnapshot.target_id == target.id
        )
    )
    return SectionMonitorTargetResponse(
        id=target.id,
        student_profile_id=target.student_profile_id,
        course_code=target.course_code,
        section_code=target.section_code,
        term=target.term,
        title=target.title,
        instructor=target.instructor,
        status=target.status,
        is_active=target.is_active,
        is_advisory=target.is_advisory,
        is_official=target.is_official,
        latest_snapshot_created_at=latest_snapshot_created_at,
        created_at=target.created_at,
        updated_at=target.updated_at,
    )


def section_monitor_snapshot_response(
    snapshot: SectionMonitorSnapshot,
) -> SectionMonitorSnapshotResponse:
    return SectionMonitorSnapshotResponse(
        id=snapshot.id,
        target_id=snapshot.target_id,
        data_import_id=snapshot.data_import_id,
        course_code=snapshot.course_code,
        section_code=snapshot.section_code,
        term=snapshot.term,
        status=snapshot.status,
        seats_available=snapshot.seats_available,
        seats_capacity=snapshot.seats_capacity,
        waitlist_available=snapshot.waitlist_available,
        waitlist_capacity=snapshot.waitlist_capacity,
        meeting_days=snapshot.meeting_days,
        meeting_time=snapshot.meeting_time,
        location=snapshot.location,
        instructor=snapshot.instructor,
        raw_payload=snapshot.raw_payload,
        source_type=snapshot.source_type.value,
        is_official=snapshot.is_official,
        source_reference=snapshot.source_reference,
        source_confidence=snapshot.source_confidence,
        created_at=snapshot.created_at,
    )


def section_monitor_alert_response(alert: SectionMonitorAlert) -> SectionMonitorAlertResponse:
    return SectionMonitorAlertResponse(
        id=alert.id,
        target_id=alert.target_id,
        previous_snapshot_id=alert.previous_snapshot_id,
        current_snapshot_id=alert.current_snapshot_id,
        alert_type=alert.alert_type.value,
        severity=alert.severity.value,
        field_name=alert.field_name,
        previous_value=alert.previous_value,
        current_value=alert.current_value,
        message=alert.message,
        is_acknowledged=alert.is_acknowledged,
        acknowledged_at=alert.acknowledged_at,
        is_advisory=alert.is_advisory,
        requires_manual_review=alert.requires_manual_review,
        created_at=alert.created_at,
    )


def section_monitor_compare_response(
    result: SnapshotCompareResult,
) -> SectionMonitorSnapshotCompareResponse:
    return SectionMonitorSnapshotCompareResponse(
        snapshots=[section_monitor_snapshot_response(snapshot) for snapshot in result.snapshots],
        alerts=[section_monitor_alert_response(alert) for alert in result.alerts],
        disclaimers=result.disclaimers,
    )


def imported_record_response(record: ImportedRecord) -> ImportedRecordResponse:
    return ImportedRecordResponse(
        id=record.id,
        data_import_run_id=record.data_import_run_id,
        record_type=record.record_type.value,
        row_number=record.row_number,
        status=record.status.value,
        external_identifier=record.external_identifier,
        raw_label=record.raw_label,
        normalized_payload=record.normalized_payload,
        confidence_score=record.confidence_score,
        created_at=record.created_at,
    )


def import_mapping_candidate_response(
    candidate: ImportMappingCandidate,
) -> ImportMappingCandidateResponse:
    return ImportMappingCandidateResponse(
        id=candidate.id,
        imported_record_id=candidate.imported_record_id,
        target_entity_type=candidate.target_entity_type.value,
        target_entity_id=candidate.target_entity_id,
        match_type=candidate.match_type.value,
        confidence_score=candidate.confidence_score,
        is_selected=candidate.is_selected,
        reason_code=candidate.reason_code,
        explanation=candidate.explanation,
        created_at=candidate.created_at,
    )


def import_validation_warning_response(
    warning: ImportValidationWarning,
) -> ImportValidationWarningResponse:
    return ImportValidationWarningResponse(
        id=warning.id,
        data_import_run_id=warning.data_import_run_id,
        imported_record_id=warning.imported_record_id,
        warning_code=warning.warning_code,
        severity=warning.severity.value,
        message=warning.message,
        requires_advisor_confirmation=warning.requires_advisor_confirmation,
        created_at=warning.created_at,
    )


def import_preview_summary_response(
    summary: ImportPreviewSummary,
) -> ImportPreviewSummaryResponse:
    disclaimers = summary.summary_payload.get("disclaimers")
    disclaimer_values = (
        [str(disclaimer) for disclaimer in disclaimers]
        if isinstance(disclaimers, list)
        else STAGING_DISCLAIMERS
    )
    return ImportPreviewSummaryResponse(
        id=summary.id,
        data_import_run_id=summary.data_import_run_id,
        record_count=summary.record_count,
        valid_record_count=summary.valid_record_count,
        warning_count=summary.warning_count,
        error_count=summary.error_count,
        official_application_ready=summary.official_application_ready,
        disclaimers=disclaimer_values,
        summary_payload=summary.summary_payload,
        created_at=summary.created_at,
    )


def data_import_review_session_response(
    review: DataImportReviewSession,
) -> DataImportReviewSessionResponse:
    return DataImportReviewSessionResponse(
        id=review.id,
        data_import_run_id=review.data_import_run_id,
        student_profile_id=review.student_profile_id,
        status=review.status.value,
        reviewer_label=review.reviewer_label,
        started_at=review.started_at,
        completed_at=review.completed_at,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def imported_record_review_response(
    record_review: ImportedRecordReview,
    db: Session,
) -> ImportedRecordReviewResponse:
    record = db.get(ImportedRecord, record_review.imported_record_id)
    if record is None:
        raise not_found("ImportedRecord", record_review.imported_record_id)
    candidate = (
        db.get(ImportMappingCandidate, record_review.selected_mapping_candidate_id)
        if record_review.selected_mapping_candidate_id is not None
        else None
    )
    return ImportedRecordReviewResponse(
        id=record_review.id,
        review_session_id=record_review.review_session_id,
        imported_record_id=record_review.imported_record_id,
        selected_mapping_candidate_id=record_review.selected_mapping_candidate_id,
        decision=record_review.decision.value,
        edited_normalized_payload=record_review.edited_normalized_payload,
        review_note=record_review.review_note,
        requires_advisor_confirmation=record_review.requires_advisor_confirmation,
        imported_record=imported_record_response(record),
        selected_mapping_candidate=(
            import_mapping_candidate_response(candidate) if candidate is not None else None
        ),
        created_at=record_review.created_at,
        updated_at=record_review.updated_at,
    )


def data_application_run_response(application: DataApplicationRun) -> DataApplicationRunResponse:
    return DataApplicationRunResponse(
        id=application.id,
        review_session_id=application.review_session_id,
        status=application.status.value,
        applied_count=application.applied_count,
        skipped_count=application.skipped_count,
        warning_count=application.warning_count,
        error_count=application.error_count,
        started_at=application.started_at,
        completed_at=application.completed_at,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


def course_state_snapshot_response(
    snapshot: CourseStateSnapshot,
) -> CourseStateSnapshotResponse:
    return CourseStateSnapshotResponse(
        id=snapshot.id,
        student_profile_id=snapshot.student_profile_id,
        data_import_run_id=snapshot.data_import_run_id,
        review_session_id=snapshot.review_session_id,
        data_application_run_id=snapshot.data_application_run_id,
        source_page_type=snapshot.source_page_type,
        source_validation_state=snapshot.source_validation_state,
        program_mapping_state=snapshot.program_mapping_state,
        is_active=snapshot.is_active,
        is_advisory=snapshot.is_advisory,
        official_application_ready=snapshot.official_application_ready,
        extraction_bounded=snapshot.extraction_bounded,
        extraction_truncated=snapshot.extraction_truncated,
        completed_count=snapshot.completed_count,
        in_progress_count=snapshot.in_progress_count,
        planned_count=snapshot.planned_count,
        not_started_count=snapshot.not_started_count,
        matched_count=snapshot.matched_count,
        unmatched_count=snapshot.unmatched_count,
        exception_count=snapshot.exception_count,
        program_summary=snapshot.program_summary,
        credit_summary=snapshot.credit_summary,
        requirement_summary=snapshot.requirement_summary,
        readiness=snapshot.readiness_payload,
        applied_at=snapshot.applied_at,
        source=source_response(snapshot),
        created_at=snapshot.created_at,
        updated_at=snapshot.updated_at,
    )


def course_state_record_response(state: CourseStateRecord) -> CourseStateRecordResponse:
    return CourseStateRecordResponse(
        id=state.id,
        snapshot_id=state.snapshot_id,
        imported_record_id=state.imported_record_id,
        imported_record_review_id=state.imported_record_review_id,
        matched_course_id=state.matched_course_id,
        student_course_attempt_id=state.student_course_attempt_id,
        normalized_course_code=state.normalized_course_code,
        source_course_code=state.source_course_code,
        source_course_title=state.source_course_title,
        status=state.status.value,
        term=state.term,
        credits=state.credits,
        grade=state.grade,
        requirement_context=state.requirement_context,
        source_page_type=state.source_page_type,
        source_table_index=state.source_table_index,
        source_row_index=state.source_row_index,
        provenance=state.provenance,
        confidence_score=state.confidence_score,
        validation_state=state.validation_state.value,
        review_decision=state.review_decision.value,
        application_reason_code=state.application_reason_code,
        reason_codes=[str(code) for code in state.reason_codes],
        warnings=[str(warning) for warning in state.warnings],
        created_at=state.created_at,
    )


def course_state_snapshot_detail_response(
    snapshot: CourseStateSnapshot,
    db: Session,
) -> CourseStateSnapshotDetailResponse:
    states = db.scalars(
        select(CourseStateRecord)
        .join(ImportedRecord, ImportedRecord.id == CourseStateRecord.imported_record_id)
        .where(CourseStateRecord.snapshot_id == snapshot.id)
        .order_by(ImportedRecord.row_number, CourseStateRecord.id)
    ).all()
    return CourseStateSnapshotDetailResponse(
        snapshot=course_state_snapshot_response(snapshot),
        course_states=[course_state_record_response(state) for state in states],
    )


def applied_imported_record_response(
    applied: AppliedImportedRecord | AppliedImportedRecordResult,
) -> AppliedImportedRecordResponse:
    return AppliedImportedRecordResponse(
        id=applied.id,
        data_application_run_id=applied.data_application_run_id,
        imported_record_review_id=applied.imported_record_review_id,
        imported_record_id=applied.imported_record_id,
        target_entity_type=applied.target_entity_type.value,
        target_entity_id=applied.target_entity_id,
        action=applied.action.value,
        status=applied.status.value,
        reason_code=applied.reason_code,
        message=applied.message,
        created_at=applied.created_at,
    )


def data_review_warning_response(warning: DataReviewWarning) -> DataReviewWarningResponse:
    return DataReviewWarningResponse(
        id=warning.id,
        review_session_id=warning.review_session_id,
        imported_record_review_id=warning.imported_record_review_id,
        data_application_run_id=warning.data_application_run_id,
        warning_code=warning.warning_code,
        severity=warning.severity.value,
        message=warning.message,
        requires_advisor_confirmation=warning.requires_advisor_confirmation,
        created_at=warning.created_at,
    )


def data_review_application_summary_response(
    review: DataImportReviewSession,
    applied_records: Sequence[AppliedImportedRecord | AppliedImportedRecordResult],
    snapshot: CourseStateSnapshot | None,
) -> DataReviewApplicationSummaryResponse:
    return DataReviewApplicationSummaryResponse(
        source_import_id=review.data_import_run_id,
        snapshot_id=snapshot.id if snapshot is not None else None,
        applied_count=sum(
            record.action in {AppliedImportAction.CREATED, AppliedImportAction.UPDATED}
            for record in applied_records
        ),
        warning_count=sum(
            record.status is AppliedImportStatus.WARNING for record in applied_records
        ),
        exception_count=sum(
            record.reason_code in {"COURSE_STATE_EXCEPTION", "IMPORT_VALIDATION_FAILED"}
            for record in applied_records
        ),
        rejected_count=sum(
            record.action is AppliedImportAction.SKIPPED_REJECTED for record in applied_records
        ),
        deferred_count=sum(
            record.action is AppliedImportAction.SKIPPED_DEFERRED for record in applied_records
        ),
        duplicate_count=sum(
            record.action is AppliedImportAction.SKIPPED_DUPLICATE for record in applied_records
        ),
    )


def data_review_application_result_response(
    result: DataReviewApplicationResult,
) -> DataReviewApplicationResultResponse:
    return DataReviewApplicationResultResponse(
        review_session=data_import_review_session_response(result.review_session),
        dry_run=result.dry_run,
        application=(
            data_application_run_response(result.application)
            if result.application is not None
            else None
        ),
        applied_records=[
            applied_imported_record_response(applied) for applied in result.applied_records
        ],
        warnings=[data_review_warning_response(warning) for warning in result.warnings],
        course_state_snapshot=(
            course_state_snapshot_response(result.course_state_snapshot)
            if result.course_state_snapshot is not None
            else None
        ),
        summary=data_review_application_summary_response(
            result.review_session,
            result.applied_records,
            result.course_state_snapshot,
        ),
    )


def data_application_detail_response(
    application: DataApplicationRun,
    db: Session,
) -> DataReviewApplicationResultResponse:
    review = db.get(DataImportReviewSession, application.review_session_id)
    if review is None:
        raise not_found("DataImportReviewSession", application.review_session_id)
    applied_records = db.scalars(
        select(AppliedImportedRecord)
        .where(AppliedImportedRecord.data_application_run_id == application.id)
        .order_by(AppliedImportedRecord.created_at, AppliedImportedRecord.id)
    ).all()
    warnings = db.scalars(
        select(DataReviewWarning)
        .where(
            DataReviewWarning.review_session_id == review.id,
            (
                (DataReviewWarning.data_application_run_id == application.id)
                | (DataReviewWarning.data_application_run_id.is_(None))
            ),
        )
        .order_by(DataReviewWarning.created_at, DataReviewWarning.id)
    ).all()
    snapshot = db.scalar(
        select(CourseStateSnapshot).where(
            CourseStateSnapshot.data_application_run_id == application.id
        )
    )
    if snapshot is None:
        snapshot = db.scalar(
            select(CourseStateSnapshot).where(CourseStateSnapshot.review_session_id == review.id)
        )
    return DataReviewApplicationResultResponse(
        review_session=data_import_review_session_response(review),
        dry_run=False,
        application=data_application_run_response(application),
        applied_records=[applied_imported_record_response(applied) for applied in applied_records],
        warnings=[data_review_warning_response(warning) for warning in warnings],
        course_state_snapshot=(
            course_state_snapshot_response(snapshot) if snapshot is not None else None
        ),
        summary=data_review_application_summary_response(review, applied_records, snapshot),
    )


def program_summary_response(
    version: ProgramVersion,
    program: AcademicProgram,
    campus: Campus,
) -> ProgramVersionSummaryResponse:
    return ProgramVersionSummaryResponse(
        program_version_id=version.id,
        program_id=program.id,
        program_code=program.code,
        program_name=program.name,
        program_type=program.program_type.value,
        degree_level=program.degree_level.value,
        campus_id=campus.id,
        campus_code=campus.code,
        campus_name=campus.name,
        catalog_year=version.catalog_year,
        version_label=version.version_label,
        total_credits_required=version.total_credits_required,
        source=source_response(version),
    )


def program_detail_response(
    version: ProgramVersion,
    program: AcademicProgram,
    campus: Campus,
) -> ProgramVersionDetailResponse:
    return ProgramVersionDetailResponse(
        id=version.id,
        institution_id=version.institution_id,
        catalog_year=version.catalog_year,
        version_label=version.version_label,
        total_credits_required=version.total_credits_required,
        effective_term_id=version.effective_term_id,
        program=academic_program_response(program),
        campus=campus_response(campus),
        source=source_response(version),
    )


def program_version_query() -> Select[tuple[ProgramVersion, AcademicProgram, Campus]]:
    return (
        select(ProgramVersion, AcademicProgram, Campus)
        .join(AcademicProgram, ProgramVersion.program_id == AcademicProgram.id)
        .join(Campus, ProgramVersion.campus_id == Campus.id)
    )


@router.get("/institutions", response_model=list[InstitutionResponse])
def list_institutions(db: DatabaseSession) -> list[InstitutionResponse]:
    institutions = db.scalars(select(Institution).order_by(Institution.code)).all()
    return [institution_response(institution) for institution in institutions]


@router.get("/programs", response_model=list[ProgramVersionSummaryResponse])
def list_programs(db: DatabaseSession) -> list[ProgramVersionSummaryResponse]:
    rows = db.execute(
        program_version_query().order_by(AcademicProgram.code, ProgramVersion.catalog_year)
    ).all()
    return [program_summary_response(version, program, campus) for version, program, campus in rows]


@router.get(
    "/programs/{program_version_id}",
    response_model=ProgramVersionDetailResponse,
    responses={404: not_found_response},
)
def get_program(
    program_version_id: UUID,
    db: DatabaseSession,
) -> ProgramVersionDetailResponse:
    row = db.execute(
        program_version_query().where(ProgramVersion.id == program_version_id)
    ).one_or_none()
    if row is None:
        raise not_found("ProgramVersion", program_version_id)
    version, program, campus = row
    return program_detail_response(version, program, campus)


@router.get(
    "/programs/{program_version_id}/requirements",
    response_model=RequirementTreeResponse,
    responses={404: not_found_response},
)
def get_program_requirements(
    program_version_id: UUID,
    db: DatabaseSession,
) -> RequirementTreeResponse:
    version = db.get(ProgramVersion, program_version_id)
    if version is None:
        raise not_found("ProgramVersion", program_version_id)

    nodes = db.scalars(
        select(RequirementNode)
        .where(RequirementNode.program_version_id == program_version_id)
        .order_by(RequirementNode.display_order, RequirementNode.code)
    ).all()
    option_rows = db.execute(
        select(RequirementCourseOption, Course)
        .join(Course, RequirementCourseOption.course_id == Course.id)
        .where(RequirementCourseOption.program_version_id == program_version_id)
        .order_by(RequirementCourseOption.display_order)
    ).all()
    options_by_node: dict[UUID, list[RequirementCourseOptionResponse]] = defaultdict(list)
    for option, course in option_rows:
        options_by_node[option.requirement_node_id].append(
            RequirementCourseOptionResponse(
                id=option.id,
                course_id=course.id,
                subject_code=course.subject_code,
                course_number=course.course_number,
                title=course.title,
                display_order=option.display_order,
                minimum_grade=option.minimum_grade,
                credits_override=option.credits_override,
                source=source_response(option),
            )
        )

    return RequirementTreeResponse(
        program_version_id=program_version_id,
        nodes=[
            RequirementNodeResponse(
                id=node.id,
                parent_id=node.parent_id,
                code=node.code,
                name=node.name,
                requirement_type=node.requirement_type.value,
                display_order=node.display_order,
                minimum_credits=node.minimum_credits,
                minimum_courses=node.minimum_courses,
                choose_n=node.choose_n,
                minimum_grade=node.minimum_grade,
                minimum_course_level=node.minimum_course_level,
                minimum_residency_credits=node.minimum_residency_credits,
                allows_overlap=node.allows_overlap,
                is_required=node.is_required,
                course_options=options_by_node[node.id],
                source=source_response(node),
            )
            for node in nodes
        ],
    )


@router.get("/courses", response_model=list[CourseResponse])
def list_courses(db: DatabaseSession) -> list[CourseResponse]:
    courses = db.scalars(select(Course).order_by(Course.subject_code, Course.course_number)).all()
    return [course_response(course) for course in courses]


@router.get(
    "/courses/{course_id}",
    response_model=CourseResponse,
    responses={404: not_found_response},
)
def get_course(course_id: UUID, db: DatabaseSession) -> CourseResponse:
    course = db.get(Course, course_id)
    if course is None:
        raise not_found("Course", course_id)
    return course_response(course)


def section_rows(
    db: Session,
    *,
    term_id: UUID | None = None,
    course_id: UUID | None = None,
    campus_id: UUID | None = None,
    status: SectionStatus | None = None,
    modality: SectionModality | None = None,
) -> list[Section]:
    stmt = select(Section)
    if term_id is not None:
        stmt = stmt.where(Section.term_id == term_id)
    if course_id is not None:
        stmt = stmt.where(Section.course_id == course_id)
    if campus_id is not None:
        stmt = stmt.where(Section.campus_id == campus_id)
    if status is not None:
        stmt = stmt.where(Section.status == status)
    if modality is not None:
        stmt = stmt.where(Section.modality == modality)
    return list(db.scalars(stmt.order_by(Section.section_code, Section.id)).all())


@router.get(
    "/terms/{term_id}/sections",
    response_model=list[SectionResponse],
    responses={404: not_found_response},
)
def list_term_sections(
    term_id: UUID,
    db: DatabaseSession,
    course_id: UUID | None = None,
    campus_id: UUID | None = None,
    status: Annotated[SectionStatus | None, Query()] = None,
    modality: Annotated[SectionModality | None, Query()] = None,
) -> list[SectionResponse]:
    if db.get(AcademicTerm, term_id) is None:
        raise not_found("AcademicTerm", term_id)
    return [
        section_response(section)
        for section in section_rows(
            db,
            term_id=term_id,
            course_id=course_id,
            campus_id=campus_id,
            status=status,
            modality=modality,
        )
    ]


@router.get(
    "/courses/{course_id}/sections",
    response_model=list[SectionResponse],
    responses={404: not_found_response},
)
def list_course_sections(
    course_id: UUID,
    db: DatabaseSession,
    term_id: UUID | None = None,
    campus_id: UUID | None = None,
    status: Annotated[SectionStatus | None, Query()] = None,
    modality: Annotated[SectionModality | None, Query()] = None,
) -> list[SectionResponse]:
    if db.get(Course, course_id) is None:
        raise not_found("Course", course_id)
    return [
        section_response(section)
        for section in section_rows(
            db,
            term_id=term_id,
            course_id=course_id,
            campus_id=campus_id,
            status=status,
            modality=modality,
        )
    ]


@router.get(
    "/sections/{section_id}",
    response_model=SectionResponse,
    responses={404: not_found_response},
)
def get_section(section_id: UUID, db: DatabaseSession) -> SectionResponse:
    section = db.get(Section, section_id)
    if section is None:
        raise not_found("Section", section_id)
    return section_response(section)


@router.get(
    "/sections/{section_id}/meetings",
    response_model=list[SectionMeetingResponse],
    responses={404: not_found_response},
)
def get_section_meetings(
    section_id: UUID,
    db: DatabaseSession,
) -> list[SectionMeetingResponse]:
    if db.get(Section, section_id) is None:
        raise not_found("Section", section_id)
    meetings = db.scalars(
        select(SectionMeeting)
        .where(SectionMeeting.section_id == section_id)
        .order_by(SectionMeeting.display_order, SectionMeeting.meeting_type, SectionMeeting.id)
    ).all()
    return [section_meeting_response(meeting) for meeting in meetings]


@router.get(
    "/courses/{course_id}/rules",
    response_model=list[CourseRuleResponse],
    responses={404: not_found_response},
)
def get_course_rules(course_id: UUID, db: DatabaseSession) -> list[CourseRuleResponse]:
    if db.get(Course, course_id) is None:
        raise not_found("Course", course_id)
    rules = db.scalars(
        select(CourseRule)
        .where(CourseRule.course_id == course_id, CourseRule.section_id.is_(None))
        .order_by(CourseRule.rule_type, CourseRule.name, CourseRule.id)
    ).all()
    return [course_rule_response(rule) for rule in rules]


@router.get(
    "/sections/{section_id}/rules",
    response_model=list[CourseRuleResponse],
    responses={404: not_found_response},
)
def get_section_rules(section_id: UUID, db: DatabaseSession) -> list[CourseRuleResponse]:
    if db.get(Section, section_id) is None:
        raise not_found("Section", section_id)
    rules = db.scalars(
        select(CourseRule)
        .where(CourseRule.section_id == section_id)
        .order_by(CourseRule.rule_type, CourseRule.name, CourseRule.id)
    ).all()
    return [course_rule_response(rule) for rule in rules]


@router.get(
    "/rules/{rule_id}",
    response_model=CourseRuleResponse,
    responses={404: not_found_response},
)
def get_rule(rule_id: UUID, db: DatabaseSession) -> CourseRuleResponse:
    rule = db.get(CourseRule, rule_id)
    if rule is None:
        raise not_found("CourseRule", rule_id)
    return course_rule_response(rule)


@router.get(
    "/rules/{rule_id}/expression",
    response_model=CourseRuleExpressionTreeResponse,
    responses={404: not_found_response},
)
def get_rule_expression(
    rule_id: UUID,
    db: DatabaseSession,
) -> CourseRuleExpressionTreeResponse:
    if db.get(CourseRule, rule_id) is None:
        raise not_found("CourseRule", rule_id)
    nodes = db.scalars(
        select(CourseRuleExpression)
        .where(CourseRuleExpression.course_rule_id == rule_id)
        .order_by(CourseRuleExpression.display_order, CourseRuleExpression.node_type)
    ).all()
    children_by_parent: dict[UUID, list[CourseRuleExpression]] = defaultdict(list)
    root: CourseRuleExpression | None = None
    for node in nodes:
        if node.parent_id is None:
            root = node
        else:
            children_by_parent[node.parent_id].append(node)
    return CourseRuleExpressionTreeResponse(
        course_rule_id=rule_id,
        root=expression_node_response(root, children_by_parent) if root else None,
    )


@router.get(
    "/courses/{course_id}/offering-patterns",
    response_model=list[CourseOfferingPatternResponse],
    responses={404: not_found_response},
)
def get_course_offering_patterns(
    course_id: UUID,
    db: DatabaseSession,
) -> list[CourseOfferingPatternResponse]:
    if db.get(Course, course_id) is None:
        raise not_found("Course", course_id)
    patterns = db.scalars(
        select(CourseOfferingPattern)
        .where(CourseOfferingPattern.course_id == course_id)
        .order_by(
            CourseOfferingPattern.term_type,
            CourseOfferingPattern.effective_term_id,
            CourseOfferingPattern.id,
        )
    ).all()
    return [offering_pattern_response(pattern) for pattern in patterns]


@router.post(
    "/degree-audits",
    response_model=DegreeAuditRunResponse,
    status_code=201,
    responses={404: not_found_response, 400: not_found_response},
)
def create_degree_audit(
    request: DegreeAuditCreateRequest,
    db: DatabaseSession,
) -> DegreeAuditRunResponse:
    try:
        run = DegreeAuditApplicationService(db).create_audit(
            request.student_profile_id,
            request.program_version_id,
            AuditMode(request.calculation_mode),
        )
    except DegreeAuditValidationError as error:
        status_code = 404 if error.code == "not_found" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
    return degree_audit_run_response(run)


@router.get(
    "/degree-audits/{audit_id}",
    response_model=DegreeAuditRunResponse,
    responses={404: not_found_response},
)
def get_degree_audit(audit_id: UUID, db: DatabaseSession) -> DegreeAuditRunResponse:
    run = db.get(DegreeAuditRun, audit_id)
    if run is None:
        raise not_found("DegreeAuditRun", audit_id)
    return degree_audit_run_response(run)


@router.get(
    "/degree-audits/{audit_id}/requirements",
    response_model=list[RequirementEvaluationResponse],
    responses={404: not_found_response},
)
def get_degree_audit_requirements(
    audit_id: UUID,
    db: DatabaseSession,
) -> list[RequirementEvaluationResponse]:
    if db.get(DegreeAuditRun, audit_id) is None:
        raise not_found("DegreeAuditRun", audit_id)

    rows = db.execute(
        select(RequirementEvaluation, RequirementNode)
        .join(RequirementNode, RequirementEvaluation.requirement_node_id == RequirementNode.id)
        .where(RequirementEvaluation.degree_audit_run_id == audit_id)
        .order_by(RequirementEvaluation.display_order, RequirementNode.code)
    ).all()
    evaluation_ids = [evaluation.id for evaluation, _ in rows]
    applications_by_evaluation: dict[UUID, list[AuditCourseApplicationResponse]] = defaultdict(list)
    if evaluation_ids:
        application_rows = db.execute(
            select(AuditCourseApplication, Course)
            .outerjoin(Course, AuditCourseApplication.course_id == Course.id)
            .where(AuditCourseApplication.requirement_evaluation_id.in_(evaluation_ids))
            .order_by(AuditCourseApplication.created_at, AuditCourseApplication.id)
        ).all()
        for application, course in application_rows:
            applications_by_evaluation[application.requirement_evaluation_id].append(
                audit_course_application_response(application, course)
            )

    warnings_by_evaluation: dict[UUID, list[DegreeAuditWarningResponse]] = defaultdict(list)
    if evaluation_ids:
        warning_rows = db.scalars(
            select(DegreeAuditWarning)
            .where(DegreeAuditWarning.requirement_evaluation_id.in_(evaluation_ids))
            .order_by(DegreeAuditWarning.created_at, DegreeAuditWarning.id)
        ).all()
        for warning in warning_rows:
            if warning.requirement_evaluation_id is not None:
                warnings_by_evaluation[warning.requirement_evaluation_id].append(
                    degree_audit_warning_response(warning)
                )

    return [
        requirement_evaluation_response(
            evaluation,
            requirement,
            applications_by_evaluation[evaluation.id],
            warnings_by_evaluation[evaluation.id],
        )
        for evaluation, requirement in rows
    ]


@router.get(
    "/degree-audits/{audit_id}/warnings",
    response_model=list[DegreeAuditWarningResponse],
    responses={404: not_found_response},
)
def get_degree_audit_warnings(
    audit_id: UUID,
    db: DatabaseSession,
) -> list[DegreeAuditWarningResponse]:
    if db.get(DegreeAuditRun, audit_id) is None:
        raise not_found("DegreeAuditRun", audit_id)
    warnings = db.scalars(
        select(DegreeAuditWarning)
        .where(DegreeAuditWarning.degree_audit_run_id == audit_id)
        .order_by(DegreeAuditWarning.severity, DegreeAuditWarning.created_at, DegreeAuditWarning.id)
    ).all()
    return [degree_audit_warning_response(warning) for warning in warnings]


@router.get(
    "/students/{student_id}/degree-audits",
    response_model=list[DegreeAuditRunResponse],
    responses={404: not_found_response},
)
def list_student_degree_audits(
    student_id: UUID,
    db: DatabaseSession,
) -> list[DegreeAuditRunResponse]:
    if db.get(StudentProfile, student_id) is None:
        raise not_found("StudentProfile", student_id)
    runs = db.scalars(
        select(DegreeAuditRun)
        .where(DegreeAuditRun.student_profile_id == student_id)
        .order_by(DegreeAuditRun.created_at.desc(), DegreeAuditRun.id.desc())
    ).all()
    return [degree_audit_run_response(run) for run in runs]


@router.get(
    "/students/{student_id}/degree-audits/latest",
    response_model=DegreeAuditRunResponse,
    responses={404: not_found_response},
)
def get_latest_student_degree_audit(
    student_id: UUID,
    db: DatabaseSession,
) -> DegreeAuditRunResponse:
    if db.get(StudentProfile, student_id) is None:
        raise not_found("StudentProfile", student_id)
    run = db.scalar(
        select(DegreeAuditRun)
        .where(DegreeAuditRun.student_profile_id == student_id)
        .order_by(DegreeAuditRun.created_at.desc(), DegreeAuditRun.id.desc())
        .limit(1)
    )
    if run is None:
        raise not_found("DegreeAuditRun", student_id)
    return degree_audit_run_response(run)


@router.post(
    "/eligibility-checks",
    response_model=CourseEligibilityCheckResponse,
    status_code=201,
    responses={404: not_found_response, 400: not_found_response},
)
def create_course_eligibility_check(
    request: CourseEligibilityCreateRequest,
    db: DatabaseSession,
) -> CourseEligibilityCheckResponse:
    try:
        run = CourseEligibilityApplicationService(db).create_check(
            student_profile_id=request.student_profile_id,
            course_id=request.course_id,
            section_id=request.section_id,
            target_term_id=request.target_term_id,
            mode=EligibilityMode(request.mode),
            planned_corequisite_course_ids=request.planned_corequisite_course_ids,
        )
    except CourseEligibilityValidationError as error:
        status_code = 404 if error.code == "not_found" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
    return eligibility_check_response(run, db)


@router.post(
    "/eligibility-checks/batch",
    response_model=CourseEligibilityBatchResponse,
    status_code=201,
    responses={404: not_found_response, 400: not_found_response},
)
def create_course_eligibility_batch(
    request: CourseEligibilityBatchRequest,
    db: DatabaseSession,
) -> CourseEligibilityBatchResponse:
    results: list[CourseEligibilityCheckResponse] = []
    service = CourseEligibilityApplicationService(db)
    for check in request.checks:
        try:
            run = service.create_check(
                student_profile_id=check.student_profile_id,
                course_id=check.course_id,
                section_id=check.section_id,
                target_term_id=check.target_term_id,
                mode=EligibilityMode(check.mode),
                planned_corequisite_course_ids=check.planned_corequisite_course_ids,
            )
        except CourseEligibilityValidationError as error:
            status_code = 404 if error.code == "not_found" else 400
            raise HTTPException(
                status_code=status_code,
                detail={"code": error.code, "message": error.message},
            ) from error
        results.append(eligibility_check_response(run, db))
    return CourseEligibilityBatchResponse(results=results)


@router.get(
    "/eligibility-checks/{eligibility_check_id}",
    response_model=CourseEligibilityCheckResponse,
    responses={404: not_found_response},
)
def get_course_eligibility_check(
    eligibility_check_id: UUID,
    db: DatabaseSession,
) -> CourseEligibilityCheckResponse:
    run = db.get(EligibilityCheckRun, eligibility_check_id)
    if run is None:
        raise not_found("EligibilityCheckRun", eligibility_check_id)
    return eligibility_check_response(run, db)


@router.get(
    "/eligibility-checks/{eligibility_check_id}/rules",
    response_model=list[RuleEvaluationResponse],
    responses={404: not_found_response},
)
def get_course_eligibility_rules(
    eligibility_check_id: UUID,
    db: DatabaseSession,
) -> list[RuleEvaluationResponse]:
    run = db.get(EligibilityCheckRun, eligibility_check_id)
    if run is None:
        raise not_found("EligibilityCheckRun", eligibility_check_id)
    return eligibility_check_response(run, db).rule_evaluations


@router.get(
    "/eligibility-checks/{eligibility_check_id}/warnings",
    response_model=list[EligibilityWarningResponse],
    responses={404: not_found_response},
)
def get_course_eligibility_warnings(
    eligibility_check_id: UUID,
    db: DatabaseSession,
) -> list[EligibilityWarningResponse]:
    run = db.get(EligibilityCheckRun, eligibility_check_id)
    if run is None:
        raise not_found("EligibilityCheckRun", eligibility_check_id)
    return eligibility_check_response(run, db).warnings


@router.get(
    "/students/{student_id}/eligibility-checks",
    response_model=list[CourseEligibilityCheckResponse],
    responses={404: not_found_response},
)
def list_student_eligibility_checks(
    student_id: UUID,
    db: DatabaseSession,
) -> list[CourseEligibilityCheckResponse]:
    if db.get(StudentProfile, student_id) is None:
        raise not_found("StudentProfile", student_id)
    runs = db.scalars(
        select(EligibilityCheckRun)
        .where(EligibilityCheckRun.student_profile_id == student_id)
        .order_by(EligibilityCheckRun.created_at.desc(), EligibilityCheckRun.id.desc())
    ).all()
    return [eligibility_check_response(run, db) for run in runs]


@router.post(
    "/academic-plans",
    response_model=AcademicPlanDetailResponse,
    status_code=201,
    responses={404: not_found_response, 400: not_found_response},
)
def create_academic_plan(
    request: AcademicPlanCreateRequest,
    db: DatabaseSession,
) -> AcademicPlanDetailResponse:
    try:
        run = AcademicPlannerApplicationService(db).create_plan(
            student_profile_id=request.student_profile_id,
            program_version_id=request.program_version_id,
            academic_plan_scenario_id=request.academic_plan_scenario_id,
            planning_mode=AcademicPlanningMode(request.planning_mode),
            start_term_id=request.start_term_id,
            terms_to_plan=request.terms_to_plan,
            minimum_credits_per_term=request.minimum_credits_per_term,
            maximum_credits_per_term=request.maximum_credits_per_term,
            preferred_credits_per_term=request.preferred_credits_per_term,
        )
    except AcademicPlannerValidationError as error:
        status_code = 404 if error.code == "not_found" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
    return academic_plan_detail_response(run, db)


@router.post(
    "/academic-plans/compare",
    response_model=list[AcademicPlanComparisonResponse],
    responses={404: not_found_response},
)
def compare_academic_plans(
    request: AcademicPlanCompareRequest,
    db: DatabaseSession,
) -> list[AcademicPlanComparisonResponse]:
    runs = {
        run.id: run
        for run in db.scalars(
            select(AcademicPlanRun).where(AcademicPlanRun.id.in_(request.academic_plan_ids))
        ).all()
    }
    missing = [plan_id for plan_id in request.academic_plan_ids if plan_id not in runs]
    if missing:
        raise not_found("AcademicPlanRun", missing[0])
    comparisons: list[AcademicPlanComparisonResponse] = []
    for plan_id in request.academic_plan_ids:
        term_count = (
            db.scalar(
                select(func.count())
                .select_from(AcademicPlanTerm)
                .where(AcademicPlanTerm.academic_plan_run_id == plan_id)
            )
            or 0
        )
        course_count = (
            db.scalar(
                select(func.count())
                .select_from(AcademicPlanCourse)
                .join(
                    AcademicPlanTerm,
                    AcademicPlanCourse.academic_plan_term_id == AcademicPlanTerm.id,
                )
                .where(AcademicPlanTerm.academic_plan_run_id == plan_id)
            )
            or 0
        )
        warning_count = (
            db.scalar(
                select(func.count())
                .select_from(AcademicPlanWarning)
                .where(AcademicPlanWarning.academic_plan_run_id == plan_id)
            )
            or 0
        )
        total_credits = (
            db.scalar(
                select(func.coalesce(func.sum(AcademicPlanTerm.planned_credits), 0)).where(
                    AcademicPlanTerm.academic_plan_run_id == plan_id
                )
            )
            or 0
        )
        run = runs[plan_id]
        comparisons.append(
            AcademicPlanComparisonResponse(
                academic_plan_run_id=run.id,
                status=run.status.value,
                total_planned_credits=total_credits,
                term_count=term_count,
                planned_course_count=course_count,
                warning_count=warning_count,
                completed_at=run.completed_at,
            )
        )
    return comparisons


@router.get(
    "/academic-plans/{plan_id}",
    response_model=AcademicPlanDetailResponse,
    responses={404: not_found_response},
)
def get_academic_plan(
    plan_id: UUID,
    db: DatabaseSession,
) -> AcademicPlanDetailResponse:
    run = db.get(AcademicPlanRun, plan_id)
    if run is None:
        raise not_found("AcademicPlanRun", plan_id)
    return academic_plan_detail_response(run, db)


@router.get(
    "/academic-plans/{plan_id}/terms",
    response_model=list[AcademicPlanTermResponse],
    responses={404: not_found_response},
)
def get_academic_plan_terms(
    plan_id: UUID,
    db: DatabaseSession,
) -> list[AcademicPlanTermResponse]:
    if db.get(AcademicPlanRun, plan_id) is None:
        raise not_found("AcademicPlanRun", plan_id)
    return academic_plan_terms_response(plan_id, db)


@router.get(
    "/academic-plans/{plan_id}/courses",
    response_model=list[AcademicPlanCourseResponse],
    responses={404: not_found_response},
)
def get_academic_plan_courses(
    plan_id: UUID,
    db: DatabaseSession,
) -> list[AcademicPlanCourseResponse]:
    if db.get(AcademicPlanRun, plan_id) is None:
        raise not_found("AcademicPlanRun", plan_id)
    return academic_plan_courses_response(plan_id, db)


@router.get(
    "/academic-plans/{plan_id}/warnings",
    response_model=list[AcademicPlanWarningResponse],
    responses={404: not_found_response},
)
def get_academic_plan_warnings(
    plan_id: UUID,
    db: DatabaseSession,
) -> list[AcademicPlanWarningResponse]:
    if db.get(AcademicPlanRun, plan_id) is None:
        raise not_found("AcademicPlanRun", plan_id)
    return academic_plan_warnings_response(plan_id, db)


@router.get(
    "/students/{student_id}/academic-plans",
    response_model=list[AcademicPlanRunResponse],
    responses={404: not_found_response},
)
def list_student_academic_plans(
    student_id: UUID,
    db: DatabaseSession,
) -> list[AcademicPlanRunResponse]:
    if db.get(StudentProfile, student_id) is None:
        raise not_found("StudentProfile", student_id)
    runs = db.scalars(
        select(AcademicPlanRun)
        .where(AcademicPlanRun.student_profile_id == student_id)
        .order_by(AcademicPlanRun.created_at.desc(), AcademicPlanRun.id.desc())
    ).all()
    return [academic_plan_run_response(run) for run in runs]


@router.post(
    "/schedule-optimizations",
    response_model=ScheduleOptimizationDetailResponse,
    status_code=201,
    responses={404: not_found_response, 400: not_found_response},
)
def create_schedule_optimization(
    request: ScheduleOptimizationCreateRequest,
    db: DatabaseSession,
) -> ScheduleOptimizationDetailResponse:
    try:
        run = ScheduleOptimizerApplicationService(db).create_schedule(
            student_profile_id=request.student_profile_id,
            term_id=request.term_id,
            academic_plan_run_id=request.academic_plan_run_id,
            planning_mode=SchedulePlanningMode(request.planning_mode),
            candidate_course_ids=request.candidate_course_ids,
            minimum_credits=request.minimum_credits,
            maximum_credits=request.maximum_credits,
            preferred_credits=request.preferred_credits,
            requested_option_count=request.max_options or request.requested_option_count,
            excluded_days=[DayOfWeek(day) for day in request.excluded_days],
            unavailable_time_blocks=[
                {
                    "day_of_week": block.day_of_week,
                    "start_time": block.start_time.isoformat(timespec="minutes"),
                    "end_time": block.end_time.isoformat(timespec="minutes"),
                }
                for block in request.unavailable_time_blocks
            ],
            earliest_start_time=request.earliest_start_time,
            latest_end_time=request.latest_end_time,
            allowed_modalities=[
                SectionModality(modality) for modality in request.allowed_modalities
            ],
            excluded_modalities=[
                SectionModality(modality) for modality in request.excluded_modalities
            ],
            required_course_ids=request.required_course_ids,
            excluded_course_ids=request.excluded_course_ids,
            required_section_ids=request.required_section_ids,
            excluded_section_ids=request.excluded_section_ids,
            prefer_online=request.prefer_online,
            prefer_compact_schedule=request.prefer_compact_schedule,
            prefer_fewer_days=request.prefer_fewer_days,
            prefer_in_person=request.prefer_in_person,
            avoid_early_start=request.avoid_early_start,
            avoid_late_end=request.avoid_late_end,
            allow_permission_required=request.allow_permission_required,
            minimum_gap_minutes=request.minimum_gap_minutes,
            maximum_gap_minutes=request.maximum_gap_minutes,
            preference_weights=request.preference_weights,
            course_priority_weights=request.course_priority_weights,
            section_priority_weights=request.section_priority_weights,
            prefer_no_gaps=request.prefer_no_gaps,
            prefer_morning=request.prefer_morning,
            prefer_afternoon=request.prefer_afternoon,
            diversity_mode=request.diversity_mode,
            allow_partial_options=request.allow_partial_options,
            max_combinations=request.max_combinations,
        )
    except ScheduleOptimizerValidationError as error:
        status_code = 404 if error.code == "not_found" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
    return schedule_detail_response(run, db)


@router.post(
    "/schedule-optimizations/compare",
    response_model=list[ScheduleOptimizationComparisonResponse],
    responses={404: not_found_response},
)
def compare_schedule_optimizations(
    request: ScheduleOptimizationCompareRequest,
    db: DatabaseSession,
) -> list[ScheduleOptimizationComparisonResponse]:
    runs = {
        run.id: run
        for run in db.scalars(
            select(ScheduleOptimizationRun).where(
                ScheduleOptimizationRun.id.in_(request.schedule_optimization_run_ids)
            )
        ).all()
    }
    missing = [run_id for run_id in request.schedule_optimization_run_ids if run_id not in runs]
    if missing:
        raise not_found("ScheduleOptimizationRun", missing[0])

    comparisons: list[ScheduleOptimizationComparisonResponse] = []
    for run_id in request.schedule_optimization_run_ids:
        option_count = (
            db.scalar(
                select(func.count())
                .select_from(ScheduleOption)
                .where(ScheduleOption.schedule_optimization_run_id == run_id)
            )
            or 0
        )
        warning_count = (
            db.scalar(
                select(func.count())
                .select_from(ScheduleWarning)
                .where(ScheduleWarning.schedule_optimization_run_id == run_id)
            )
            or 0
        )
        best_option = db.scalar(
            select(ScheduleOption)
            .where(ScheduleOption.schedule_optimization_run_id == run_id)
            .order_by(ScheduleOption.option_rank, ScheduleOption.id)
            .limit(1)
        )
        run = runs[run_id]
        comparisons.append(
            ScheduleOptimizationComparisonResponse(
                schedule_optimization_run_id=run.id,
                status=run.status.value,
                option_count=option_count,
                warning_count=warning_count,
                best_score=best_option.score if best_option else None,
                best_total_credits=best_option.total_credits if best_option else None,
                completed_at=run.completed_at,
            )
        )
    return comparisons


@router.get(
    "/schedule-optimizations/{run_id}",
    response_model=ScheduleOptimizationDetailResponse,
    responses={404: not_found_response},
)
def get_schedule_optimization(
    run_id: UUID,
    db: DatabaseSession,
) -> ScheduleOptimizationDetailResponse:
    run = db.get(ScheduleOptimizationRun, run_id)
    if run is None:
        raise not_found("ScheduleOptimizationRun", run_id)
    return schedule_detail_response(run, db)


@router.get(
    "/schedule-optimizations/{run_id}/options",
    response_model=list[ScheduleOptionResponse],
    responses={404: not_found_response},
)
def get_schedule_optimization_options(
    run_id: UUID,
    db: DatabaseSession,
) -> list[ScheduleOptionResponse]:
    if db.get(ScheduleOptimizationRun, run_id) is None:
        raise not_found("ScheduleOptimizationRun", run_id)
    return schedule_options_response(run_id, db)


@router.get(
    "/schedule-optimizations/{run_id}/conflicts",
    response_model=list[ScheduleConflictResponse],
    responses={404: not_found_response},
)
def get_schedule_optimization_conflicts(
    run_id: UUID,
    db: DatabaseSession,
) -> list[ScheduleConflictResponse]:
    if db.get(ScheduleOptimizationRun, run_id) is None:
        raise not_found("ScheduleOptimizationRun", run_id)
    return schedule_conflicts_response(run_id, db)


@router.get(
    "/schedule-optimizations/{run_id}/warnings",
    response_model=list[ScheduleWarningResponse],
    responses={404: not_found_response},
)
def get_schedule_optimization_warnings(
    run_id: UUID,
    db: DatabaseSession,
) -> list[ScheduleWarningResponse]:
    if db.get(ScheduleOptimizationRun, run_id) is None:
        raise not_found("ScheduleOptimizationRun", run_id)
    return schedule_warnings_response(run_id, db)


@router.get(
    "/students/{student_id}/schedule-optimizations",
    response_model=list[ScheduleOptimizationRunResponse],
    responses={404: not_found_response},
)
def list_student_schedule_optimizations(
    student_id: UUID,
    db: DatabaseSession,
) -> list[ScheduleOptimizationRunResponse]:
    if db.get(StudentProfile, student_id) is None:
        raise not_found("StudentProfile", student_id)
    runs = db.scalars(
        select(ScheduleOptimizationRun)
        .where(ScheduleOptimizationRun.student_profile_id == student_id)
        .order_by(
            ScheduleOptimizationRun.created_at.desc(),
            ScheduleOptimizationRun.id.desc(),
        )
    ).all()
    return [schedule_run_response(run) for run in runs]


@router.post(
    "/data-imports",
    response_model=DataImportRunResponse,
    status_code=201,
    responses={404: not_found_response, 400: not_found_response},
)
def create_data_import(
    request: DataImportCreateRequest,
    db: DatabaseSession,
) -> DataImportRunResponse:
    try:
        run = DataImportApplicationService(db).create_import(
            student_profile_id=request.student_profile_id,
            import_type=DataImportType(request.import_type),
            file_name=request.file_name,
            file_mime_type=request.file_mime_type,
            content=request.content,
            source_type=SourceType(request.source_type),
            source_reference=request.source_reference,
        )
    except DataImportValidationError as error:
        status_code = 404 if error.code == "not_found" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
    return data_import_run_response(run)


@router.get(
    "/data-imports/{run_id}",
    response_model=DataImportRunResponse,
    responses={404: not_found_response},
)
def get_data_import(
    run_id: UUID,
    db: DatabaseSession,
) -> DataImportRunResponse:
    run = db.get(DataImportRun, run_id)
    if run is None:
        raise not_found("DataImportRun", run_id)
    return data_import_run_response(run)


@router.get(
    "/data-imports/{run_id}/records",
    response_model=list[ImportedRecordResponse],
    responses={404: not_found_response},
)
def get_data_import_records(
    run_id: UUID,
    db: DatabaseSession,
) -> list[ImportedRecordResponse]:
    if db.get(DataImportRun, run_id) is None:
        raise not_found("DataImportRun", run_id)
    records = db.scalars(
        select(ImportedRecord)
        .where(ImportedRecord.data_import_run_id == run_id)
        .order_by(ImportedRecord.row_number, ImportedRecord.id)
    ).all()
    return [imported_record_response(record) for record in records]


@router.get(
    "/data-imports/{run_id}/mapping-candidates",
    response_model=list[ImportMappingCandidateResponse],
    responses={404: not_found_response},
)
def get_data_import_mapping_candidates(
    run_id: UUID,
    db: DatabaseSession,
) -> list[ImportMappingCandidateResponse]:
    if db.get(DataImportRun, run_id) is None:
        raise not_found("DataImportRun", run_id)
    candidates = db.scalars(
        select(ImportMappingCandidate)
        .join(ImportedRecord, ImportMappingCandidate.imported_record_id == ImportedRecord.id)
        .where(ImportedRecord.data_import_run_id == run_id)
        .order_by(
            ImportedRecord.row_number,
            ImportMappingCandidate.confidence_score.desc(),
            ImportMappingCandidate.id,
        )
    ).all()
    return [import_mapping_candidate_response(candidate) for candidate in candidates]


@router.get(
    "/data-imports/{run_id}/warnings",
    response_model=list[ImportValidationWarningResponse],
    responses={404: not_found_response},
)
def get_data_import_warnings(
    run_id: UUID,
    db: DatabaseSession,
) -> list[ImportValidationWarningResponse]:
    if db.get(DataImportRun, run_id) is None:
        raise not_found("DataImportRun", run_id)
    warnings = db.scalars(
        select(ImportValidationWarning)
        .where(ImportValidationWarning.data_import_run_id == run_id)
        .order_by(
            ImportValidationWarning.severity,
            ImportValidationWarning.created_at,
            ImportValidationWarning.id,
        )
    ).all()
    return [import_validation_warning_response(warning) for warning in warnings]


@router.get(
    "/data-imports/{run_id}/preview",
    response_model=ImportPreviewSummaryResponse,
    responses={404: not_found_response},
)
def get_data_import_preview(
    run_id: UUID,
    db: DatabaseSession,
) -> ImportPreviewSummaryResponse:
    try:
        summary = DataImportApplicationService(db).validate_import(run_id)
    except DataImportValidationError as error:
        raise HTTPException(
            status_code=404,
            detail={"code": error.code, "message": error.message},
        ) from error
    return import_preview_summary_response(summary)


@router.post(
    "/data-imports/{run_id}/validate",
    response_model=ImportPreviewSummaryResponse,
    responses={404: not_found_response},
)
def validate_data_import(
    run_id: UUID,
    db: DatabaseSession,
) -> ImportPreviewSummaryResponse:
    try:
        summary = DataImportApplicationService(db).validate_import(run_id)
    except DataImportValidationError as error:
        raise HTTPException(
            status_code=404,
            detail={"code": error.code, "message": error.message},
        ) from error
    return import_preview_summary_response(summary)


@router.get(
    "/students/{student_id}/data-imports",
    response_model=list[DataImportRunResponse],
    responses={404: not_found_response},
)
def list_student_data_imports(
    student_id: UUID,
    db: DatabaseSession,
) -> list[DataImportRunResponse]:
    if db.get(StudentProfile, student_id) is None:
        raise not_found("StudentProfile", student_id)
    runs = db.scalars(
        select(DataImportRun)
        .where(DataImportRun.student_profile_id == student_id)
        .order_by(DataImportRun.created_at.desc(), DataImportRun.id.desc())
    ).all()
    return [data_import_run_response(run) for run in runs]


@router.get(
    "/section-monitoring/targets",
    response_model=list[SectionMonitorTargetResponse],
    responses={404: not_found_response},
)
def list_section_monitor_targets(
    db: DatabaseSession,
    student_profile_id: Annotated[UUID, Query()],
) -> list[SectionMonitorTargetResponse]:
    try:
        targets = SectionMonitoringApplicationService(db).list_targets(student_profile_id)
    except SectionMonitoringValidationError as error:
        raise HTTPException(
            status_code=404,
            detail={"code": error.code, "message": error.message},
        ) from error
    return [section_monitor_target_response(target, db) for target in targets]


@router.post(
    "/section-monitoring/targets",
    response_model=SectionMonitorTargetResponse,
    status_code=201,
    responses={404: not_found_response, 400: not_found_response},
)
def create_section_monitor_target(
    request: SectionMonitorTargetCreateRequest,
    db: DatabaseSession,
) -> SectionMonitorTargetResponse:
    try:
        target = SectionMonitoringApplicationService(db).create_target(
            student_profile_id=request.student_profile_id,
            course_code=request.course_code,
            section_code=request.section_code,
            term=request.term,
            title=request.title,
            instructor=request.instructor,
            status=request.status,
        )
        db.commit()
    except SectionMonitoringValidationError as error:
        status_code = 404 if error.code == "not_found" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
    return section_monitor_target_response(target, db)


@router.patch(
    "/section-monitoring/targets/{target_id}",
    response_model=SectionMonitorTargetResponse,
    responses={404: not_found_response, 400: not_found_response},
)
def update_section_monitor_target(
    target_id: UUID,
    request: SectionMonitorTargetUpdateRequest,
    db: DatabaseSession,
) -> SectionMonitorTargetResponse:
    try:
        target = SectionMonitoringApplicationService(db).update_target(
            target_id,
            is_active=request.is_active,
            title=request.title,
            instructor=request.instructor,
            status=request.status,
        )
        db.commit()
    except SectionMonitoringValidationError as error:
        status_code = 404 if error.code == "not_found" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
    return section_monitor_target_response(target, db)


@router.get(
    "/section-monitoring/alerts",
    response_model=list[SectionMonitorAlertResponse],
    responses={404: not_found_response},
)
def list_section_monitor_alerts(
    db: DatabaseSession,
    student_profile_id: Annotated[UUID, Query()],
) -> list[SectionMonitorAlertResponse]:
    try:
        alerts = SectionMonitoringApplicationService(db).list_alerts(student_profile_id)
    except SectionMonitoringValidationError as error:
        raise HTTPException(
            status_code=404,
            detail={"code": error.code, "message": error.message},
        ) from error
    return [section_monitor_alert_response(alert) for alert in alerts]


@router.patch(
    "/section-monitoring/alerts/{alert_id}",
    response_model=SectionMonitorAlertResponse,
    responses={404: not_found_response, 400: not_found_response},
)
def update_section_monitor_alert(
    alert_id: UUID,
    request: SectionMonitorAlertUpdateRequest,
    db: DatabaseSession,
) -> SectionMonitorAlertResponse:
    try:
        alert = SectionMonitoringApplicationService(db).acknowledge_alert(
            alert_id,
            is_acknowledged=request.is_acknowledged,
        )
        db.commit()
    except SectionMonitoringValidationError as error:
        status_code = 404 if error.code == "not_found" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
    return section_monitor_alert_response(alert)


@router.post(
    "/section-monitoring/snapshots/compare",
    response_model=SectionMonitorSnapshotCompareResponse,
    status_code=201,
    responses={404: not_found_response, 400: not_found_response},
)
def compare_section_monitor_snapshots(
    request: SectionMonitorSnapshotCompareRequest,
    db: DatabaseSession,
) -> SectionMonitorSnapshotCompareResponse:
    try:
        result = SectionMonitoringApplicationService(db).compare_snapshots(
            student_profile_id=request.student_profile_id,
            snapshots=[snapshot.model_dump() for snapshot in request.snapshots],
            source_type=SourceType(request.source_type),
        )
        db.commit()
    except SectionMonitoringValidationError as error:
        status_code = 404 if error.code == "not_found" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
    return section_monitor_compare_response(result)


@router.post(
    "/data-import-reviews",
    response_model=DataImportReviewSessionResponse,
    status_code=201,
    responses={404: not_found_response, 400: not_found_response},
)
def create_data_import_review(
    request: DataImportReviewCreateRequest,
    db: DatabaseSession,
) -> DataImportReviewSessionResponse:
    try:
        review = DataReviewApplicationService(db).create_review_session(
            data_import_run_id=request.data_import_run_id,
            reviewer_label=request.reviewer_label,
        )
    except DataReviewValidationError as error:
        status_code = 404 if error.code == "not_found" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
    return data_import_review_session_response(review)


@router.get(
    "/data-import-reviews/{review_id}",
    response_model=DataImportReviewSessionResponse,
    responses={404: not_found_response},
)
def get_data_import_review(
    review_id: UUID,
    db: DatabaseSession,
) -> DataImportReviewSessionResponse:
    review = db.get(DataImportReviewSession, review_id)
    if review is None:
        raise not_found("DataImportReviewSession", review_id)
    return data_import_review_session_response(review)


@router.get(
    "/data-import-reviews/{review_id}/records",
    response_model=list[ImportedRecordReviewResponse],
    responses={404: not_found_response},
)
def get_data_import_review_records(
    review_id: UUID,
    db: DatabaseSession,
) -> list[ImportedRecordReviewResponse]:
    if db.get(DataImportReviewSession, review_id) is None:
        raise not_found("DataImportReviewSession", review_id)
    record_reviews = db.scalars(
        select(ImportedRecordReview)
        .join(ImportedRecord, ImportedRecordReview.imported_record_id == ImportedRecord.id)
        .where(ImportedRecordReview.review_session_id == review_id)
        .order_by(ImportedRecord.row_number, ImportedRecordReview.id)
    ).all()
    return [imported_record_review_response(record_review, db) for record_review in record_reviews]


@router.patch(
    "/data-import-reviews/{review_id}/records/{record_review_id}",
    response_model=ImportedRecordReviewResponse,
    responses={404: not_found_response, 400: not_found_response},
)
def update_data_import_review_record(
    review_id: UUID,
    record_review_id: UUID,
    request: ImportedRecordReviewUpdateRequest,
    db: DatabaseSession,
) -> ImportedRecordReviewResponse:
    try:
        record_review = DataReviewApplicationService(db).update_record_review(
            review_session_id=review_id,
            record_review_id=record_review_id,
            decision=ImportedRecordReviewDecision(request.decision),
            selected_mapping_candidate_id=request.selected_mapping_candidate_id,
            edited_normalized_payload=request.edited_normalized_payload,
            review_note=request.review_note,
            requires_advisor_confirmation=request.requires_advisor_confirmation,
        )
    except DataReviewValidationError as error:
        status_code = 404 if error.code == "not_found" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
    return imported_record_review_response(record_review, db)


@router.post(
    "/data-import-reviews/{review_id}/apply",
    response_model=DataReviewApplicationResultResponse,
    responses={404: not_found_response, 400: not_found_response},
)
def apply_data_import_review(
    review_id: UUID,
    request: DataImportReviewApplyRequest,
    db: DatabaseSession,
) -> DataReviewApplicationResultResponse:
    try:
        result = DataReviewApplicationService(db).apply_review_session(
            review_id,
            allow_advisor_review_records=request.allow_advisor_review_records,
            dry_run=request.dry_run,
        )
    except DataReviewValidationError as error:
        status_code = 404 if error.code == "not_found" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
    return data_review_application_result_response(result)


@router.get(
    "/data-import-reviews/{review_id}/applications",
    response_model=list[DataApplicationRunResponse],
    responses={404: not_found_response},
)
def get_data_import_review_applications(
    review_id: UUID,
    db: DatabaseSession,
) -> list[DataApplicationRunResponse]:
    if db.get(DataImportReviewSession, review_id) is None:
        raise not_found("DataImportReviewSession", review_id)
    applications = db.scalars(
        select(DataApplicationRun)
        .where(DataApplicationRun.review_session_id == review_id)
        .order_by(DataApplicationRun.created_at.desc(), DataApplicationRun.id.desc())
    ).all()
    return [data_application_run_response(application) for application in applications]


@router.get(
    "/data-import-reviews/{review_id}/warnings",
    response_model=list[DataReviewWarningResponse],
    responses={404: not_found_response},
)
def get_data_import_review_warnings(
    review_id: UUID,
    db: DatabaseSession,
) -> list[DataReviewWarningResponse]:
    if db.get(DataImportReviewSession, review_id) is None:
        raise not_found("DataImportReviewSession", review_id)
    warnings = db.scalars(
        select(DataReviewWarning)
        .where(DataReviewWarning.review_session_id == review_id)
        .order_by(DataReviewWarning.created_at, DataReviewWarning.id)
    ).all()
    return [data_review_warning_response(warning) for warning in warnings]


@router.get(
    "/data-applications/{application_id}",
    response_model=DataReviewApplicationResultResponse,
    responses={404: not_found_response},
)
def get_data_application(
    application_id: UUID,
    db: DatabaseSession,
) -> DataReviewApplicationResultResponse:
    application = db.get(DataApplicationRun, application_id)
    if application is None:
        raise not_found("DataApplicationRun", application_id)
    return data_application_detail_response(application, db)


@router.get(
    "/students/{student_id}/data-import-reviews",
    response_model=list[DataImportReviewSessionResponse],
    responses={404: not_found_response},
)
def list_student_data_import_reviews(
    student_id: UUID,
    db: DatabaseSession,
) -> list[DataImportReviewSessionResponse]:
    if db.get(StudentProfile, student_id) is None:
        raise not_found("StudentProfile", student_id)
    reviews = db.scalars(
        select(DataImportReviewSession)
        .where(DataImportReviewSession.student_profile_id == student_id)
        .order_by(DataImportReviewSession.created_at.desc(), DataImportReviewSession.id.desc())
    ).all()
    return [data_import_review_session_response(review) for review in reviews]


@router.get(
    "/students/{student_id}/course-state-snapshots/active",
    response_model=CourseStateSnapshotDetailResponse,
    responses={404: not_found_response},
)
def get_active_course_state_snapshot(
    student_id: UUID,
    db: DatabaseSession,
) -> CourseStateSnapshotDetailResponse:
    if db.get(StudentProfile, student_id) is None:
        raise not_found("StudentProfile", student_id)
    snapshot = db.scalar(
        select(CourseStateSnapshot)
        .where(
            CourseStateSnapshot.student_profile_id == student_id,
            CourseStateSnapshot.is_active.is_(True),
        )
        .order_by(CourseStateSnapshot.applied_at.desc(), CourseStateSnapshot.id.desc())
    )
    if snapshot is None:
        raise not_found("ActiveCourseStateSnapshot", student_id)
    return course_state_snapshot_detail_response(snapshot, db)


@router.post(
    "/academic-scenarios",
    response_model=AcademicScenarioResponse,
    status_code=201,
    responses={404: not_found_response, 400: not_found_response},
)
def create_academic_scenario(
    request: AcademicScenarioCreateRequest,
    db: DatabaseSession,
) -> AcademicScenarioResponse:
    try:
        scenario = AcademicScenarioApplicationService(db).create_scenario(
            student_profile_id=request.student_profile_id,
            scenario_name=request.scenario_name,
            scenario_type=ScenarioType(request.scenario_type),
            calculation_mode=AuditMode(request.calculation_mode),
            programs=[
                ScenarioProgramInput(
                    program_version_id=program.program_version_id,
                    relationship_type=ScenarioRelationshipType(program.relationship_type),
                    priority=program.priority,
                )
                for program in request.programs
            ],
        )
    except AcademicScenarioValidationError as error:
        status_code = 404 if error.code == "not_found" else 400
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
    return academic_scenario_response(scenario)


@router.post(
    "/academic-scenarios/compare",
    response_model=list[ScenarioComparisonSnapshotResponse],
    responses={404: not_found_response},
)
def compare_academic_scenarios(
    request: AcademicScenarioCompareRequest,
    db: DatabaseSession,
) -> list[ScenarioComparisonSnapshotResponse]:
    snapshots = {
        snapshot.academic_plan_scenario_id: snapshot
        for snapshot in db.scalars(
            select(ScenarioComparisonSnapshot).where(
                ScenarioComparisonSnapshot.academic_plan_scenario_id.in_(request.scenario_ids)
            )
        ).all()
    }
    missing = [scenario_id for scenario_id in request.scenario_ids if scenario_id not in snapshots]
    if missing:
        raise not_found("AcademicPlanScenario", missing[0])
    return [
        scenario_comparison_response(snapshots[scenario_id]) for scenario_id in request.scenario_ids
    ]


@router.get(
    "/academic-scenarios/{scenario_id}",
    response_model=AcademicScenarioResponse,
    responses={404: not_found_response},
)
def get_academic_scenario(
    scenario_id: UUID,
    db: DatabaseSession,
) -> AcademicScenarioResponse:
    scenario = db.get(AcademicPlanScenario, scenario_id)
    if scenario is None:
        raise not_found("AcademicPlanScenario", scenario_id)
    return academic_scenario_response(scenario)


@router.get(
    "/academic-scenarios/{scenario_id}/programs",
    response_model=list[ScenarioProgramResponse],
    responses={404: not_found_response},
)
def get_academic_scenario_programs(
    scenario_id: UUID,
    db: DatabaseSession,
) -> list[ScenarioProgramResponse]:
    if db.get(AcademicPlanScenario, scenario_id) is None:
        raise not_found("AcademicPlanScenario", scenario_id)
    rows = db.execute(
        select(ScenarioProgram, ProgramVersion, AcademicProgram)
        .join(ProgramVersion, ScenarioProgram.program_version_id == ProgramVersion.id)
        .join(AcademicProgram, ProgramVersion.program_id == AcademicProgram.id)
        .where(ScenarioProgram.academic_plan_scenario_id == scenario_id)
        .order_by(ScenarioProgram.priority, AcademicProgram.code)
    ).all()
    return [
        scenario_program_response(scenario_program, version, program)
        for scenario_program, version, program in rows
    ]


@router.get(
    "/academic-scenarios/{scenario_id}/audits",
    response_model=list[ScenarioProgramAuditResponse],
    responses={404: not_found_response},
)
def get_academic_scenario_audits(
    scenario_id: UUID,
    db: DatabaseSession,
) -> list[ScenarioProgramAuditResponse]:
    if db.get(AcademicPlanScenario, scenario_id) is None:
        raise not_found("AcademicPlanScenario", scenario_id)
    rows = db.execute(
        select(ScenarioProgram, ProgramVersion, AcademicProgram, DegreeAuditRun)
        .join(ScenarioProgramAudit, ScenarioProgramAudit.scenario_program_id == ScenarioProgram.id)
        .join(DegreeAuditRun, ScenarioProgramAudit.degree_audit_run_id == DegreeAuditRun.id)
        .join(ProgramVersion, ScenarioProgram.program_version_id == ProgramVersion.id)
        .join(AcademicProgram, ProgramVersion.program_id == AcademicProgram.id)
        .where(ScenarioProgram.academic_plan_scenario_id == scenario_id)
        .order_by(ScenarioProgram.priority, AcademicProgram.code)
    ).all()
    return [
        ScenarioProgramAuditResponse(
            scenario_program=scenario_program_response(scenario_program, version, program),
            degree_audit_run=degree_audit_run_response(run),
        )
        for scenario_program, version, program, run in rows
    ]


@router.get(
    "/academic-scenarios/{scenario_id}/allocations",
    response_model=list[ScenarioCourseAllocationResponse],
    responses={404: not_found_response},
)
def get_academic_scenario_allocations(
    scenario_id: UUID,
    db: DatabaseSession,
) -> list[ScenarioCourseAllocationResponse]:
    if db.get(AcademicPlanScenario, scenario_id) is None:
        raise not_found("AcademicPlanScenario", scenario_id)
    rows = db.execute(
        select(ScenarioCourseAllocation, Course, RequirementNode)
        .outerjoin(Course, ScenarioCourseAllocation.course_id == Course.id)
        .outerjoin(
            RequirementNode, ScenarioCourseAllocation.requirement_node_id == RequirementNode.id
        )
        .where(ScenarioCourseAllocation.academic_plan_scenario_id == scenario_id)
        .order_by(ScenarioCourseAllocation.allocation_rank, ScenarioCourseAllocation.id)
    ).all()
    return [
        scenario_course_allocation_response(allocation, course, requirement)
        for allocation, course, requirement in rows
    ]


@router.get(
    "/academic-scenarios/{scenario_id}/warnings",
    response_model=list[ScenarioWarningResponse],
    responses={404: not_found_response},
)
def get_academic_scenario_warnings(
    scenario_id: UUID,
    db: DatabaseSession,
) -> list[ScenarioWarningResponse]:
    if db.get(AcademicPlanScenario, scenario_id) is None:
        raise not_found("AcademicPlanScenario", scenario_id)
    warnings = db.scalars(
        select(ScenarioWarning)
        .where(ScenarioWarning.academic_plan_scenario_id == scenario_id)
        .order_by(ScenarioWarning.severity, ScenarioWarning.created_at, ScenarioWarning.id)
    ).all()
    return [scenario_warning_response(warning) for warning in warnings]


@router.get(
    "/academic-scenarios/{scenario_id}/comparison",
    response_model=ScenarioComparisonSnapshotResponse,
    responses={404: not_found_response},
)
def get_academic_scenario_comparison(
    scenario_id: UUID,
    db: DatabaseSession,
) -> ScenarioComparisonSnapshotResponse:
    snapshot = db.get(ScenarioComparisonSnapshot, scenario_id)
    if snapshot is None:
        raise not_found("ScenarioComparisonSnapshot", scenario_id)
    return scenario_comparison_response(snapshot)


@router.get(
    "/students/{student_id}/academic-scenarios",
    response_model=list[AcademicScenarioResponse],
    responses={404: not_found_response},
)
def list_student_academic_scenarios(
    student_id: UUID,
    db: DatabaseSession,
) -> list[AcademicScenarioResponse]:
    if db.get(StudentProfile, student_id) is None:
        raise not_found("StudentProfile", student_id)
    scenarios = db.scalars(
        select(AcademicPlanScenario)
        .where(AcademicPlanScenario.student_profile_id == student_id)
        .order_by(AcademicPlanScenario.created_at.desc(), AcademicPlanScenario.id.desc())
    ).all()
    return [academic_scenario_response(scenario) for scenario in scenarios]


def student_programs_response(
    student_id: UUID,
    db: Session,
) -> list[StudentAcademicProgramResponse]:
    rows = db.execute(
        select(StudentAcademicProgram, ProgramVersion, AcademicProgram)
        .join(ProgramVersion, StudentAcademicProgram.program_version_id == ProgramVersion.id)
        .join(AcademicProgram, ProgramVersion.program_id == AcademicProgram.id)
        .where(StudentAcademicProgram.student_profile_id == student_id)
        .order_by(StudentAcademicProgram.program_type)
    ).all()
    return [
        StudentAcademicProgramResponse(
            id=student_program.id,
            program_version_id=program_version.id,
            program_code=program.code,
            program_name=program.name,
            program_type=student_program.program_type.value,
            status=student_program.status.value,
            declared_on=student_program.declared_on,
            source=source_response(student_program),
        )
        for student_program, program_version, program in rows
    ]


@router.get(
    "/students/{student_id}",
    response_model=StudentProfileResponse,
    responses={404: not_found_response},
)
def get_student(student_id: UUID, db: DatabaseSession) -> StudentProfileResponse:
    student = db.get(StudentProfile, student_id)
    if student is None:
        raise not_found("StudentProfile", student_id)
    return StudentProfileResponse(
        id=student.id,
        home_institution_id=student.home_institution_id,
        home_campus_id=student.home_campus_id,
        expected_graduation_term_id=student.expected_graduation_term_id,
        external_ref=student.external_ref,
        display_name=student.display_name,
        class_standing=student.class_standing,
        programs=student_programs_response(student.id, db),
        source=source_response(student),
    )


@router.get(
    "/students/{student_id}/course-attempts",
    response_model=list[StudentCourseAttemptResponse],
    responses={404: not_found_response},
)
def get_student_course_attempts(
    student_id: UUID,
    db: DatabaseSession,
) -> list[StudentCourseAttemptResponse]:
    if db.get(StudentProfile, student_id) is None:
        raise not_found("StudentProfile", student_id)
    attempts = effective_student_course_attempts(db, student_id)
    responses: list[StudentCourseAttemptResponse] = []
    for attempt in attempts:
        course = db.get(Course, attempt.course_id)
        term = db.get(AcademicTerm, attempt.term_id)
        if course is None or term is None:
            continue
        responses.append(
            StudentCourseAttemptResponse(
                id=attempt.id,
                student_profile_id=attempt.student_profile_id,
                course_id=course.id,
                course_code=f"{course.subject_code} {course.course_number}",
                course_title=course.title,
                term_id=term.id,
                term_code=term.term_code,
                attempt_number=attempt.attempt_number,
                status=attempt.status.value,
                grade=attempt.grade,
                credits_attempted=attempt.credits_attempted,
                credits_earned=attempt.credits_earned,
                is_repeat=attempt.is_repeat,
                source=source_response(attempt),
            )
        )
    return sorted(responses, key=lambda response: (response.term_code, response.attempt_number))
