from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.academic import (
    AcademicPlanScenario,
    AcademicPlanScenarioStatus,
    AuditApplicationType,
    AuditCourseApplication,
    AuditMode,
    AuditRunStatus,
    AuditWarningSeverity,
    Course,
    DegreeAuditRun,
    ProgramCombinationRule,
    ProgramVersion,
    RequirementEvaluation,
    RequirementEvaluationStatus,
    RequirementNode,
    RequirementType,
    ScenarioComparisonSnapshot,
    ScenarioCourseAllocation,
    ScenarioProgram,
    ScenarioProgramAudit,
    ScenarioRelationshipType,
    ScenarioType,
    ScenarioWarning,
    StudentAcademicProgram,
    StudentAcademicProgramStatus,
    StudentCourseAttempt,
    StudentProfile,
    StudentProgramType,
)
from app.services.academic_scenarios.allocator import (
    AllocationCandidate,
    AllocationResult,
    DeterministicMultiProgramAllocator,
    MultiProgramAllocator,
    ProgramCombinationPolicy,
    SourceKey,
)
from app.services.academic_scenarios.exceptions import AcademicScenarioValidationError
from app.services.academic_scenarios.result import ScenarioProgramInput
from app.services.degree_audit.engine import DEGREE_AUDIT_ENGINE_VERSION, DegreeAuditEngine, utc_now
from app.services.degree_audit.persistence import persist_degree_audit_success
from app.services.degree_audit.result import DegreeAuditResult

SCENARIO_ENGINE_VERSION = "phase-3b-academic-scenario-v1"
ZERO = Decimal("0.0")

REQUIRED_LEAF_TYPES = {
    RequirementType.REQUIRED_COURSE,
    RequirementType.CHOOSE_N,
    RequirementType.MINIMUM_CREDITS,
    RequirementType.MINIMUM_COURSES,
    RequirementType.COURSE_LEVEL,
    RequirementType.RESIDENCY,
    RequirementType.CAPSTONE,
}

ALLOCATABLE_REQUIREMENT_TYPES = {
    RequirementType.REQUIRED_COURSE,
    RequirementType.CHOOSE_N,
    RequirementType.CAPSTONE,
}


class AcademicScenarioEngine:
    def __init__(
        self,
        db: Session,
        allocator: MultiProgramAllocator | None = None,
    ) -> None:
        self._db = db
        self._allocator = allocator or DeterministicMultiProgramAllocator()

    def evaluate(
        self,
        *,
        student_profile_id: UUID,
        scenario_name: str,
        scenario_type: ScenarioType,
        calculation_mode: AuditMode,
        program_versions: list[ScenarioProgramInput],
    ) -> AcademicPlanScenario:
        student, programs, base_program_version_id = self._validate_request(
            student_profile_id,
            scenario_type,
            program_versions,
        )
        scenario_id = uuid4()
        scenario = AcademicPlanScenario(
            id=scenario_id,
            student_profile_id=student.id,
            name=scenario_name,
            scenario_type=scenario_type,
            status=AcademicPlanScenarioStatus.RUNNING,
            base_program_version_id=base_program_version_id,
            engine_version=SCENARIO_ENGINE_VERSION,
        )
        self._db.add(scenario)
        self._db.flush()

        try:
            scenario_programs = self._create_scenario_programs(
                scenario,
                programs,
                scenario_type,
                program_versions,
            )
            audit_results = self._create_program_audits(
                scenario,
                scenario_programs,
                calculation_mode,
            )
            policies = self._load_combination_policies(scenario, scenario_programs)
            candidates = self._load_allocation_candidates(scenario.id)
            allocation_result = self._allocator.allocate(candidates, policies)
            self._persist_allocations(scenario.id, allocation_result)
            self._add_policy_warnings(scenario, scenario_programs, policies, allocation_result)
            self._add_estimate_warning(scenario)
            self._persist_comparison(scenario, audit_results, allocation_result)
            warning_count = self._db.scalar(
                select(func.count())
                .select_from(ScenarioWarning)
                .where(ScenarioWarning.academic_plan_scenario_id == scenario.id)
            )
            scenario.status = (
                AcademicPlanScenarioStatus.COMPLETED_WITH_WARNINGS
                if warning_count
                else AcademicPlanScenarioStatus.COMPLETED
            )
            scenario.completed_at = utc_now()
            self._db.commit()
        except Exception:
            self._db.rollback()
            failed = AcademicPlanScenario(
                id=scenario_id,
                student_profile_id=student.id,
                name=scenario_name,
                scenario_type=scenario_type,
                status=AcademicPlanScenarioStatus.FAILED,
                base_program_version_id=base_program_version_id,
                engine_version=SCENARIO_ENGINE_VERSION,
                completed_at=utc_now(),
            )
            self._db.merge(failed)
            self._db.commit()
            raise
        self._db.refresh(scenario)
        return scenario

    def _validate_request(
        self,
        student_profile_id: UUID,
        scenario_type: ScenarioType,
        program_inputs: list[ScenarioProgramInput],
    ) -> tuple[StudentProfile, dict[UUID, ProgramVersion], UUID]:
        if not program_inputs:
            raise AcademicScenarioValidationError(
                "scenario_programs_required",
                "At least one ProgramVersion is required for a scenario.",
            )
        student = self._db.get(StudentProfile, student_profile_id)
        if student is None:
            raise AcademicScenarioValidationError(
                "not_found",
                f"StudentProfile {student_profile_id} was not found.",
            )
        program_ids = [program.program_version_id for program in program_inputs]
        if len(set(program_ids)) != len(program_ids):
            raise AcademicScenarioValidationError(
                "duplicate_program_version",
                "The same ProgramVersion cannot be added twice to one scenario.",
            )
        primary_inputs = [
            program
            for program in program_inputs
            if program.relationship_type is ScenarioRelationshipType.PRIMARY_MAJOR
        ]
        if len(primary_inputs) != 1:
            raise AcademicScenarioValidationError(
                "one_primary_major_required",
                "Exactly one Primary Major is required in a scenario.",
            )
        programs = {
            program.id: program
            for program in self._db.scalars(
                select(ProgramVersion).where(ProgramVersion.id.in_(program_ids))
            ).all()
        }
        missing = set(program_ids) - set(programs)
        if missing:
            raise AcademicScenarioValidationError(
                "not_found",
                f"ProgramVersion {sorted(str(item) for item in missing)[0]} was not found.",
            )
        for program in programs.values():
            if program.institution_id != student.home_institution_id:
                raise AcademicScenarioValidationError(
                    "institution_scope_mismatch",
                    "Student and ProgramVersion must belong to the same institution.",
                )

        active_primary = self._db.scalar(
            select(StudentAcademicProgram).where(
                StudentAcademicProgram.student_profile_id == student.id,
                StudentAcademicProgram.program_type == StudentProgramType.PRIMARY_MAJOR,
                StudentAcademicProgram.status == StudentAcademicProgramStatus.ACTIVE,
            )
        )
        if active_primary is not None:
            base_program_version_id = active_primary.program_version_id
        else:
            base_program_version_id = primary_inputs[0].program_version_id
        if scenario_type is ScenarioType.CHANGE_PRIMARY_MAJOR:
            candidate_primary = primary_inputs[0]
            if (
                active_primary is not None
                and candidate_primary.program_version_id == active_primary.program_version_id
            ):
                raise AcademicScenarioValidationError(
                    "change_major_candidate_required",
                    "Change Primary Major scenarios need a hypothetical candidate primary.",
                )
        return student, programs, base_program_version_id

    def _create_scenario_programs(
        self,
        scenario: AcademicPlanScenario,
        programs: dict[UUID, ProgramVersion],
        scenario_type: ScenarioType,
        program_inputs: list[ScenarioProgramInput],
    ) -> list[ScenarioProgram]:
        active_programs = {
            program.program_version_id: program
            for program in self._db.scalars(
                select(StudentAcademicProgram).where(
                    StudentAcademicProgram.student_profile_id == scenario.student_profile_id,
                    StudentAcademicProgram.status == StudentAcademicProgramStatus.ACTIVE,
                )
            ).all()
        }
        scenario_programs: list[ScenarioProgram] = []
        for program_input in sorted(
            program_inputs,
            key=lambda item: (item.priority, str(item.program_version_id)),
        ):
            is_change_candidate = (
                scenario_type is ScenarioType.CHANGE_PRIMARY_MAJOR
                and program_input.relationship_type is ScenarioRelationshipType.PRIMARY_MAJOR
            )
            is_existing = (
                program_input.program_version_id in active_programs and not is_change_candidate
            )
            scenario_program = ScenarioProgram(
                id=uuid4(),
                academic_plan_scenario_id=scenario.id,
                program_version_id=programs[program_input.program_version_id].id,
                relationship_type=program_input.relationship_type,
                is_existing_program=is_existing,
                is_hypothetical=not is_existing,
                priority=program_input.priority,
            )
            self._db.add(scenario_program)
            scenario_programs.append(scenario_program)
        self._db.flush()
        return scenario_programs

    def _create_program_audits(
        self,
        scenario: AcademicPlanScenario,
        scenario_programs: list[ScenarioProgram],
        mode: AuditMode,
    ) -> list[DegreeAuditResult]:
        results: list[DegreeAuditResult] = []
        audit_engine = DegreeAuditEngine(self._db)
        for scenario_program in scenario_programs:
            run = DegreeAuditRun(
                id=uuid4(),
                student_profile_id=scenario.student_profile_id,
                program_version_id=scenario_program.program_version_id,
                status=AuditRunStatus.RUNNING,
                engine_version=DEGREE_AUDIT_ENGINE_VERSION,
                calculation_mode=mode,
                started_at=utc_now(),
                total_required_credits=ZERO,
                completed_credits=ZERO,
                in_progress_credits=ZERO,
                planned_credits=ZERO,
                remaining_credits=ZERO,
                completion_percentage=Decimal("0.00"),
                source_snapshot_hash="pending",
            )
            self._db.add(run)
            self._db.flush()
            result = audit_engine.evaluate(
                scenario.student_profile_id,
                scenario_program.program_version_id,
                mode,
            )
            persist_degree_audit_success(self._db, run, result)
            self._db.add(
                ScenarioProgramAudit(
                    id=uuid4(),
                    academic_plan_scenario_id=scenario.id,
                    scenario_program_id=scenario_program.id,
                    degree_audit_run_id=run.id,
                )
            )
            for warning in result.warnings:
                self._db.add(
                    ScenarioWarning(
                        id=uuid4(),
                        academic_plan_scenario_id=scenario.id,
                        scenario_program_id=scenario_program.id,
                        warning_code=warning.warning_code,
                        severity=warning.severity,
                        message=warning.message,
                        requires_advisor_confirmation=warning.requires_advisor_confirmation,
                    )
                )
            results.append(result)
        self._db.flush()
        return results

    def _load_combination_policies(
        self,
        scenario: AcademicPlanScenario,
        scenario_programs: list[ScenarioProgram],
    ) -> list[ProgramCombinationPolicy]:
        primary = next(
            program
            for program in scenario_programs
            if program.relationship_type is ScenarioRelationshipType.PRIMARY_MAJOR
        )
        policies: list[ProgramCombinationPolicy] = []
        for secondary in scenario_programs:
            if secondary.id == primary.id:
                continue
            rule = self._db.scalar(
                select(ProgramCombinationRule)
                .where(
                    ProgramCombinationRule.primary_program_version_id == primary.program_version_id,
                    ProgramCombinationRule.secondary_program_version_id
                    == secondary.program_version_id,
                    ProgramCombinationRule.combination_type == secondary.relationship_type,
                )
                .order_by(ProgramCombinationRule.effective_term_id.desc())
                .limit(1)
            )
            if rule is None:
                self._db.add(
                    ScenarioWarning(
                        id=uuid4(),
                        academic_plan_scenario_id=scenario.id,
                        scenario_program_id=secondary.id,
                        warning_code="MISSING_PROGRAM_COMBINATION_RULE",
                        severity=AuditWarningSeverity.WARNING,
                        message=(
                            "No directional ProgramCombinationRule exists for this "
                            "program combination; advisor confirmation is required."
                        ),
                        requires_advisor_confirmation=True,
                    )
                )
                continue
            policies.append(
                ProgramCombinationPolicy(
                    primary_program_version_id=rule.primary_program_version_id,
                    secondary_program_version_id=rule.secondary_program_version_id,
                    relationship_type=rule.combination_type,
                    maximum_shared_credits=rule.maximum_shared_credits,
                    minimum_unique_secondary_credits=rule.minimum_unique_secondary_credits,
                    minimum_unique_courses=rule.minimum_unique_courses,
                    allows_double_counting=rule.allows_double_counting,
                    requires_manual_confirmation=rule.requires_manual_confirmation,
                    source_type=rule.source_type,
                    is_official=rule.is_official,
                )
            )
            if rule.requires_manual_confirmation:
                self._db.add(
                    ScenarioWarning(
                        id=uuid4(),
                        academic_plan_scenario_id=scenario.id,
                        scenario_program_id=secondary.id,
                        warning_code="COMBINATION_RULE_REQUIRES_REVIEW",
                        severity=AuditWarningSeverity.WARNING,
                        message="The mock combination rule requires advisor confirmation.",
                        requires_advisor_confirmation=True,
                    )
                )
        self._db.flush()
        return policies

    def _load_allocation_candidates(self, scenario_id: UUID) -> list[AllocationCandidate]:
        rows = self._db.execute(
            select(
                AuditCourseApplication,
                RequirementEvaluation,
                RequirementNode,
                ScenarioProgram,
                Course,
                StudentCourseAttempt,
            )
            .join(
                RequirementEvaluation,
                AuditCourseApplication.requirement_evaluation_id == RequirementEvaluation.id,
            )
            .join(RequirementNode, RequirementEvaluation.requirement_node_id == RequirementNode.id)
            .join(
                ScenarioProgramAudit,
                ScenarioProgramAudit.degree_audit_run_id
                == AuditCourseApplication.degree_audit_run_id,
            )
            .join(ScenarioProgram, ScenarioProgramAudit.scenario_program_id == ScenarioProgram.id)
            .outerjoin(Course, AuditCourseApplication.course_id == Course.id)
            .outerjoin(
                StudentCourseAttempt,
                AuditCourseApplication.student_course_attempt_id == StudentCourseAttempt.id,
            )
            .where(ScenarioProgramAudit.academic_plan_scenario_id == scenario_id)
            .order_by(
                ScenarioProgram.priority,
                RequirementEvaluation.display_order,
                RequirementNode.code,
                AuditCourseApplication.id,
            )
        ).all()
        candidates: list[AllocationCandidate] = []
        for application, evaluation, node, scenario_program, course, attempt in rows:
            if node.requirement_type not in ALLOCATABLE_REQUIREMENT_TYPES:
                continue
            source_key = source_key_for_application(application)
            if source_key is None:
                continue
            course_code = (
                f"{course.subject_code} {course.course_number}"
                if course is not None
                else application.application_type.value
            )
            candidates.append(
                AllocationCandidate(
                    candidate_id=application.id,
                    source_key=source_key,
                    course_id=application.course_id,
                    course_code=course_code,
                    program_version_id=scenario_program.program_version_id,
                    relationship_type=scenario_program.relationship_type,
                    requirement_node_id=evaluation.requirement_node_id,
                    requirement_code=node.code,
                    requirement_display_order=evaluation.display_order,
                    requirement_allows_overlap=node.allows_overlap,
                    program_priority=scenario_program.priority,
                    credit_amount=application.credit_amount,
                    is_earned=(
                        application.is_completed
                        and application.application_type is not AuditApplicationType.WAIVER
                    ),
                    is_completed=application.is_completed,
                    is_in_progress=application.is_in_progress,
                    is_planned=application.is_planned,
                    attempt_number=attempt.attempt_number if attempt is not None else 0,
                    explanation=application.explanation,
                    student_course_attempt_id=application.student_course_attempt_id,
                    transfer_credit_id=application.transfer_credit_id,
                    course_waiver_id=application.course_waiver_id,
                    course_substitution_id=application.course_substitution_id,
                )
            )
        return candidates

    def _persist_allocations(
        self,
        scenario_id: UUID,
        allocation_result: AllocationResult,
    ) -> None:
        for allocation in allocation_result.allocations:
            candidate = allocation.candidate
            self._db.add(
                ScenarioCourseAllocation(
                    id=uuid4(),
                    academic_plan_scenario_id=scenario_id,
                    student_course_attempt_id=candidate.student_course_attempt_id,
                    transfer_credit_id=candidate.transfer_credit_id,
                    course_waiver_id=candidate.course_waiver_id,
                    course_substitution_id=candidate.course_substitution_id,
                    course_id=candidate.course_id,
                    program_version_id=candidate.program_version_id,
                    requirement_node_id=candidate.requirement_node_id,
                    allocation_type=allocation.allocation_type,
                    credit_amount=candidate.credit_amount,
                    is_shared=allocation.is_shared,
                    is_unique_to_program=allocation.is_unique_to_program,
                    allocation_rank=allocation.allocation_rank,
                    reason_code=allocation.reason_code,
                    explanation=allocation.explanation,
                )
            )
        self._db.flush()

    def _add_policy_warnings(
        self,
        scenario: AcademicPlanScenario,
        scenario_programs: list[ScenarioProgram],
        policies: list[ProgramCombinationPolicy],
        allocation_result: AllocationResult,
    ) -> None:
        if allocation_result.search_limit_reached:
            self._db.add(
                ScenarioWarning(
                    id=uuid4(),
                    academic_plan_scenario_id=scenario.id,
                    scenario_program_id=None,
                    warning_code="ALLOCATION_SEARCH_LIMIT_REACHED",
                    severity=AuditWarningSeverity.WARNING,
                    message="Allocation search reached its configured deterministic limit.",
                    requires_advisor_confirmation=True,
                )
            )
        scenario_program_by_version = {
            program.program_version_id: program for program in scenario_programs
        }
        for policy in policies:
            unique_credits = sum(
                (
                    allocation.candidate.credit_amount
                    for allocation in allocation_result.allocations
                    if allocation.is_unique_to_program
                    and allocation.candidate.program_version_id
                    == policy.secondary_program_version_id
                    and allocation.candidate.is_earned
                ),
                ZERO,
            )
            if unique_credits < policy.minimum_unique_secondary_credits:
                self._db.add(
                    ScenarioWarning(
                        id=uuid4(),
                        academic_plan_scenario_id=scenario.id,
                        scenario_program_id=scenario_program_by_version[
                            policy.secondary_program_version_id
                        ].id,
                        warning_code="MINIMUM_UNIQUE_SECONDARY_CREDITS_NOT_MET",
                        severity=AuditWarningSeverity.WARNING,
                        message=(
                            "Current records do not meet the mock minimum unique "
                            "secondary-credit rule."
                        ),
                        requires_advisor_confirmation=True,
                    )
                )
        self._db.flush()

    def _add_estimate_warning(self, scenario: AcademicPlanScenario) -> None:
        self._db.add(
            ScenarioWarning(
                id=uuid4(),
                academic_plan_scenario_id=scenario.id,
                scenario_program_id=None,
                warning_code="ESTIMATED_ADDITIONAL_CREDITS",
                severity=AuditWarningSeverity.WARNING,
                message=(
                    "Estimated additional credits are not official policy and do not "
                    "predict graduation timing."
                ),
                requires_advisor_confirmation=True,
            )
        )
        self._db.flush()

    def _persist_comparison(
        self,
        scenario: AcademicPlanScenario,
        audit_results: list[DegreeAuditResult],
        allocation_result: AllocationResult,
    ) -> None:
        completed_credits = max(
            (result.completed_credits for result in audit_results), default=ZERO
        )
        in_progress_credits = max(
            (result.in_progress_credits for result in audit_results),
            default=ZERO,
        )
        planned_credits = max((result.planned_credits for result in audit_results), default=ZERO)
        remaining_requirement_credits, unresolved_requirements = self._remaining_requirements(
            scenario.id
        )
        estimated_additional = max(
            remaining_requirement_credits - allocation_result.objective.shared_credits,
            ZERO,
        )
        manual_review_count = (
            self._db.scalar(
                select(func.count())
                .select_from(ScenarioWarning)
                .where(
                    ScenarioWarning.academic_plan_scenario_id == scenario.id,
                    ScenarioWarning.requires_advisor_confirmation.is_(True),
                )
            )
            or 0
        )
        total_required = sum((result.total_required_credits for result in audit_results), ZERO)
        completion_percentage = (
            ((completed_credits / total_required) * Decimal("100.0")).quantize(Decimal("0.01"))
            if total_required > ZERO
            else ZERO
        )
        self._db.add(
            ScenarioComparisonSnapshot(
                academic_plan_scenario_id=scenario.id,
                completed_credits=completed_credits,
                in_progress_credits=in_progress_credits,
                planned_credits=planned_credits,
                remaining_requirement_credits=remaining_requirement_credits,
                shared_credits=allocation_result.objective.shared_credits,
                unique_secondary_credits=allocation_result.objective.unique_secondary_credits,
                estimated_additional_credits=estimated_additional,
                unresolved_requirements=unresolved_requirements,
                manual_review_count=manual_review_count,
                completion_percentage=completion_percentage,
                is_estimate=True,
            )
        )
        self._db.flush()

    def _remaining_requirements(self, scenario_id: UUID) -> tuple[Decimal, int]:
        rows = self._db.execute(
            select(RequirementEvaluation, RequirementNode)
            .join(RequirementNode, RequirementEvaluation.requirement_node_id == RequirementNode.id)
            .join(
                ScenarioProgramAudit,
                ScenarioProgramAudit.degree_audit_run_id
                == RequirementEvaluation.degree_audit_run_id,
            )
            .where(ScenarioProgramAudit.academic_plan_scenario_id == scenario_id)
        ).all()
        remaining = ZERO
        unresolved = 0
        for evaluation, node in rows:
            if not node.is_required or node.requirement_type not in REQUIRED_LEAF_TYPES:
                continue
            remaining += evaluation.remaining_credits
            if evaluation.status not in {
                RequirementEvaluationStatus.SATISFIED,
                RequirementEvaluationStatus.WAIVED,
                RequirementEvaluationStatus.NOT_APPLICABLE,
            }:
                unresolved += 1
        return remaining, unresolved


class AcademicScenarioApplicationService:
    def __init__(self, db: Session) -> None:
        self._engine = AcademicScenarioEngine(db)

    def create_scenario(
        self,
        *,
        student_profile_id: UUID,
        scenario_name: str,
        scenario_type: ScenarioType,
        calculation_mode: AuditMode,
        programs: list[ScenarioProgramInput],
    ) -> AcademicPlanScenario:
        return self._engine.evaluate(
            student_profile_id=student_profile_id,
            scenario_name=scenario_name,
            scenario_type=scenario_type,
            calculation_mode=calculation_mode,
            program_versions=programs,
        )


def source_key_for_application(application: AuditCourseApplication) -> SourceKey | None:
    if application.course_waiver_id is not None:
        return ("waiver", application.course_waiver_id)
    if application.course_substitution_id is not None:
        return ("substitution", application.course_substitution_id)
    if application.student_course_attempt_id is not None:
        return ("attempt", application.student_course_attempt_id)
    if application.transfer_credit_id is not None:
        return ("transfer", application.transfer_credit_id)
    return None
