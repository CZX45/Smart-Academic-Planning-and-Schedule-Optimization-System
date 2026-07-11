from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.academic import (
    AcademicPlanCourse,
    AcademicPlanCourseSource,
    AcademicPlanCourseStatus,
    AcademicPlanCoverageType,
    AcademicPlanningMode,
    AcademicPlanRequirementCoverage,
    AcademicPlanRun,
    AcademicPlanRunStatus,
    AcademicPlanScenario,
    AcademicPlanTerm,
    AcademicPlanTermStatus,
    AcademicPlanWarning,
    AcademicTerm,
    AuditMode,
    AuditWarningSeverity,
    Course,
    CourseOfferingPattern,
    CourseRule,
    CourseRuleExpression,
    CourseRuleType,
    CourseStateSnapshot,
    EligibilityMode,
    EligibilityOverallResult,
    FrequencyType,
    ProgramVersion,
    RequirementCourseOption,
    RequirementEvaluationStatus,
    RequirementNode,
    RequirementType,
    ScenarioProgram,
    Section,
    SectionStatus,
    SourceType,
    StudentAcademicProgram,
    StudentAcademicProgramStatus,
    StudentCourseAttemptStatus,
    StudentProgramType,
    TermType,
)
from app.services.academic_planner.exceptions import AcademicPlannerValidationError
from app.services.course_eligibility.engine import CourseEligibilityEngine
from app.services.course_eligibility.result import EligibilityResult
from app.services.course_state.engine import (
    active_course_state_snapshot,
    effective_student_course_attempts,
)
from app.services.degree_audit.engine import DegreeAuditEngine, quantize_credits
from app.services.degree_audit.result import DegreeAuditResult, RequirementResult

ENGINE_VERSION = "phase-5a-academic-planner-v1"
ZERO = Decimal("0.0")

SATISFIED_REQUIREMENT_STATUSES = {
    RequirementEvaluationStatus.SATISFIED,
    RequirementEvaluationStatus.WAIVED,
    RequirementEvaluationStatus.NOT_APPLICABLE,
}
COURSE_OPTION_REQUIREMENT_TYPES = {
    RequirementType.REQUIRED_COURSE,
    RequirementType.CHOOSE_N,
    RequirementType.CAPSTONE,
}
BROAD_REQUIREMENT_TYPES = {
    RequirementType.MINIMUM_CREDITS,
    RequirementType.TOTAL_CREDITS,
    RequirementType.COURSE_LEVEL,
    RequirementType.MINIMUM_COURSES,
    RequirementType.RESIDENCY,
}


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True)
class PlannerCandidate:
    requirement: RequirementResult
    requirement_node: RequirementNode
    course: Course
    course_option: RequirementCourseOption
    source: AcademicPlanCourseSource
    coverage_type: AcademicPlanCoverageType
    unlock_value: int

    @property
    def credits(self) -> Decimal:
        return self.course_option.credits_override or self.course.credits_min


@dataclass
class PlannedTermState:
    term: AcademicTerm
    plan_term: AcademicPlanTerm
    planned_credits: Decimal = ZERO

    def can_fit(self, credits: Decimal, maximum: Decimal) -> bool:
        return self.planned_credits + credits <= maximum

    def add_credits(self, credits: Decimal) -> None:
        self.planned_credits = quantize_credits(self.planned_credits + credits)
        self.plan_term.planned_credits = self.planned_credits


@dataclass(frozen=True)
class WarningDraft:
    warning_code: str
    severity: AuditWarningSeverity
    message: str
    requires_advisor_confirmation: bool
    term_id: UUID | None = None
    plan_course_id: UUID | None = None


class AcademicPlannerApplicationService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._eligibility_engine = CourseEligibilityEngine(db)

    def create_plan(
        self,
        *,
        student_profile_id: UUID,
        program_version_id: UUID,
        academic_plan_scenario_id: UUID | None,
        planning_mode: AcademicPlanningMode,
        start_term_id: UUID,
        terms_to_plan: int,
        minimum_credits_per_term: Decimal,
        maximum_credits_per_term: Decimal,
        preferred_credits_per_term: Decimal,
    ) -> AcademicPlanRun:
        self._validate_credit_inputs(
            terms_to_plan=terms_to_plan,
            minimum_credits_per_term=minimum_credits_per_term,
            maximum_credits_per_term=maximum_credits_per_term,
            preferred_credits_per_term=preferred_credits_per_term,
        )
        student_program, program_version, scenario = self._validate_scope(
            student_profile_id=student_profile_id,
            program_version_id=program_version_id,
            academic_plan_scenario_id=academic_plan_scenario_id,
            planning_mode=planning_mode,
        )
        active_snapshot = self._validate_course_state_readiness(student_profile_id)
        start_term = self._db.get(AcademicTerm, start_term_id)
        if start_term is None:
            raise AcademicPlannerValidationError(
                "not_found",
                f"AcademicTerm {start_term_id} was not found.",
            )
        if start_term.institution_id != program_version.institution_id:
            raise AcademicPlannerValidationError(
                "institution_scope_mismatch",
                "Start term and ProgramVersion must belong to the same institution.",
            )
        terms = self._target_terms(program_version, start_term, terms_to_plan)
        if not terms:
            raise AcademicPlannerValidationError(
                "no_target_terms",
                "No target terms are available from the requested start term.",
            )

        run_id = uuid4()
        run = AcademicPlanRun(
            id=run_id,
            student_profile_id=student_profile_id,
            program_version_id=program_version_id,
            academic_plan_scenario_id=scenario.id if scenario is not None else None,
            planning_mode=planning_mode,
            status=AcademicPlanRunStatus.RUNNING,
            engine_version=ENGINE_VERSION,
            start_term_id=start_term_id,
            target_completion_term_id=terms[-1].id,
            minimum_credits_per_term=minimum_credits_per_term,
            maximum_credits_per_term=maximum_credits_per_term,
            preferred_credits_per_term=preferred_credits_per_term,
        )
        self._db.add(run)
        self._db.flush()

        warnings: list[WarningDraft] = [
            WarningDraft(
                warning_code=(
                    "IMPORTED_PLAN_ADVISORY_ONLY"
                    if active_snapshot is not None
                    else "MOCK_PLAN_NOT_OFFICIAL"
                ),
                severity=AuditWarningSeverity.INFO,
                message=(
                    "This advisory plan uses reviewed non-official course-state snapshot "
                    f"{active_snapshot.id} from import {active_snapshot.data_import_run_id}; "
                    "it needs school or advisor confirmation."
                    if active_snapshot is not None
                    else "Mock data - not official university policy. This long-term plan is "
                    "an estimate and needs school or advisor confirmation."
                ),
                requires_advisor_confirmation=True,
            )
        ]
        if len(terms) < terms_to_plan:
            warnings.append(
                WarningDraft(
                    warning_code="PLANNING_HORIZON_TRUNCATED",
                    severity=AuditWarningSeverity.WARNING,
                    message=(
                        "Stored terms do not cover the full requested planning horizon; "
                        "the plan was not silently extended."
                    ),
                    requires_advisor_confirmation=True,
                )
            )

        try:
            term_states = self._create_plan_terms(run.id, terms)
            audit = self._run_degree_audit(
                student_profile_id=student_program.student_profile_id,
                program_version_id=program_version.id,
            )
            candidates, candidate_warnings = self._planner_candidates(
                audit,
                program_version,
                planning_mode,
            )
            warnings.extend(candidate_warnings)
            placed_requirement_ids = self._place_candidates(
                run=run,
                term_states=term_states,
                candidates=candidates,
                minimum_credits_per_term=minimum_credits_per_term,
                maximum_credits_per_term=maximum_credits_per_term,
                warnings=warnings,
            )
            unresolved = [
                candidate
                for candidate in candidates
                if candidate.requirement.requirement_node_id not in placed_requirement_ids
            ]
            if unresolved:
                warnings.append(
                    WarningDraft(
                        warning_code="PARTIAL_PLAN_HORIZON_INSUFFICIENT",
                        severity=AuditWarningSeverity.WARNING,
                        message=(
                            "The supplied terms were not enough to place every remaining "
                            "requirement under the credit limits."
                        ),
                        requires_advisor_confirmation=True,
                    )
                )
            self._persist_warnings(run.id, warnings)
            run.status = (
                AcademicPlanRunStatus.COMPLETED_WITH_WARNINGS
                if warnings
                else AcademicPlanRunStatus.COMPLETED
            )
            run.completed_at = utc_now()
            self._db.commit()
        except Exception:
            self._db.rollback()
            failed = AcademicPlanRun(
                id=run_id,
                student_profile_id=student_profile_id,
                program_version_id=program_version_id,
                academic_plan_scenario_id=academic_plan_scenario_id,
                planning_mode=planning_mode,
                status=AcademicPlanRunStatus.FAILED,
                engine_version=ENGINE_VERSION,
                start_term_id=start_term_id,
                target_completion_term_id=terms[-1].id,
                minimum_credits_per_term=minimum_credits_per_term,
                maximum_credits_per_term=maximum_credits_per_term,
                preferred_credits_per_term=preferred_credits_per_term,
                completed_at=utc_now(),
            )
            self._db.add(failed)
            self._db.commit()
            raise

        self._db.refresh(run)
        return run

    def _validate_credit_inputs(
        self,
        *,
        terms_to_plan: int,
        minimum_credits_per_term: Decimal,
        maximum_credits_per_term: Decimal,
        preferred_credits_per_term: Decimal,
    ) -> None:
        if terms_to_plan <= 0:
            raise AcademicPlannerValidationError(
                "invalid_terms_to_plan",
                "terms_to_plan must be greater than zero.",
            )
        if minimum_credits_per_term < ZERO:
            raise AcademicPlannerValidationError(
                "invalid_credit_limits",
                "minimum_credits_per_term cannot be negative.",
            )
        if maximum_credits_per_term < ZERO:
            raise AcademicPlannerValidationError(
                "invalid_credit_limits",
                "maximum_credits_per_term cannot be negative.",
            )
        if preferred_credits_per_term < ZERO:
            raise AcademicPlannerValidationError(
                "invalid_credit_limits",
                "preferred_credits_per_term cannot be negative.",
            )
        if preferred_credits_per_term > maximum_credits_per_term:
            raise AcademicPlannerValidationError(
                "invalid_credit_limits",
                "preferred_credits_per_term cannot exceed maximum_credits_per_term.",
            )

    def _validate_scope(
        self,
        *,
        student_profile_id: UUID,
        program_version_id: UUID,
        academic_plan_scenario_id: UUID | None,
        planning_mode: AcademicPlanningMode,
    ) -> tuple[StudentAcademicProgram, ProgramVersion, AcademicPlanScenario | None]:
        program_version = self._db.get(ProgramVersion, program_version_id)
        if program_version is None:
            raise AcademicPlannerValidationError(
                "not_found",
                f"ProgramVersion {program_version_id} was not found.",
            )
        active_program = self._db.scalar(
            select(StudentAcademicProgram).where(
                StudentAcademicProgram.student_profile_id == student_profile_id,
                StudentAcademicProgram.program_version_id == program_version_id,
                StudentAcademicProgram.status == StudentAcademicProgramStatus.ACTIVE,
            )
        )
        scenario = (
            self._db.get(AcademicPlanScenario, academic_plan_scenario_id)
            if academic_plan_scenario_id is not None
            else None
        )
        if planning_mode is AcademicPlanningMode.CURRENT_PROGRAM:
            if active_program is None:
                raise AcademicPlannerValidationError(
                    "program_not_declared",
                    "CURRENT_PROGRAM mode must use the student's active official program.",
                )
            return active_program, program_version, None

        if academic_plan_scenario_id is None:
            raise AcademicPlannerValidationError(
                "scenario_required",
                "WHAT_IF_SCENARIO mode requires academic_plan_scenario_id.",
            )
        if scenario is None:
            raise AcademicPlannerValidationError(
                "not_found",
                f"AcademicPlanScenario {academic_plan_scenario_id} was not found.",
            )
        if scenario.student_profile_id != student_profile_id:
            raise AcademicPlannerValidationError(
                "scenario_student_mismatch",
                "Scenario must belong to the requested student.",
            )
        scenario_program = self._db.scalar(
            select(ScenarioProgram).where(
                ScenarioProgram.academic_plan_scenario_id == scenario.id,
                ScenarioProgram.program_version_id == program_version_id,
            )
        )
        if scenario_program is None:
            raise AcademicPlannerValidationError(
                "scenario_program_missing",
                "ProgramVersion is not part of the what-if scenario.",
            )
        if active_program is None:
            active_program = StudentAcademicProgram(
                id=uuid4(),
                student_profile_id=student_profile_id,
                program_version_id=program_version_id,
                program_type=StudentProgramType.PRIMARY_MAJOR,
                status=StudentAcademicProgramStatus.ACTIVE,
                source_type=SourceType.MOCK,
                is_official=False,
            )
        return active_program, program_version, scenario

    def _target_terms(
        self,
        program_version: ProgramVersion,
        start_term: AcademicTerm,
        terms_to_plan: int,
    ) -> list[AcademicTerm]:
        return list(
            self._db.scalars(
                select(AcademicTerm)
                .where(
                    AcademicTerm.institution_id == program_version.institution_id,
                    AcademicTerm.starts_on >= start_term.starts_on,
                )
                .order_by(AcademicTerm.starts_on, AcademicTerm.term_code, AcademicTerm.id)
                .limit(terms_to_plan)
            ).all()
        )

    def _create_plan_terms(
        self,
        run_id: UUID,
        terms: list[AcademicTerm],
    ) -> list[PlannedTermState]:
        states: list[PlannedTermState] = []
        for sequence, term in enumerate(terms):
            plan_term = AcademicPlanTerm(
                id=uuid4(),
                academic_plan_run_id=run_id,
                term_id=term.id,
                sequence_index=sequence,
                planned_credits=ZERO,
                status=AcademicPlanTermStatus.PLANNED,
                explanation=f"Term {term.term_code} is part of the long-term course plan.",
            )
            self._db.add(plan_term)
            states.append(PlannedTermState(term=term, plan_term=plan_term))
        self._db.flush()
        return states

    def _run_degree_audit(
        self,
        *,
        student_profile_id: UUID,
        program_version_id: UUID,
    ) -> DegreeAuditResult:
        return DegreeAuditEngine(self._db).evaluate(
            student_profile_id,
            program_version_id,
            AuditMode.CURRENT,
        )

    def _planner_candidates(
        self,
        audit: DegreeAuditResult,
        program_version: ProgramVersion,
        planning_mode: AcademicPlanningMode,
    ) -> tuple[list[PlannerCandidate], list[WarningDraft]]:
        requirement_ids = [requirement.requirement_node_id for requirement in audit.requirements]
        nodes_by_id = {
            node.id: node
            for node in self._db.scalars(
                select(RequirementNode).where(RequirementNode.id.in_(requirement_ids))
            ).all()
        }
        options_by_requirement: dict[UUID, list[RequirementCourseOption]] = {}
        if requirement_ids:
            options = self._db.scalars(
                select(RequirementCourseOption)
                .where(RequirementCourseOption.requirement_node_id.in_(requirement_ids))
                .order_by(
                    RequirementCourseOption.requirement_node_id,
                    RequirementCourseOption.display_order,
                    RequirementCourseOption.id,
                )
            ).all()
            for option in options:
                options_by_requirement.setdefault(option.requirement_node_id, []).append(option)
        courses_by_id = {
            course.id: course
            for course in self._db.scalars(
                select(Course).where(Course.institution_id == program_version.institution_id)
            ).all()
        }
        occupied_course_ids = self._occupied_course_ids(audit.student_profile_id)
        unlock_values = self._unlock_values(program_version.institution_id)
        warnings: list[WarningDraft] = []
        candidates: list[PlannerCandidate] = []
        for requirement in audit.requirements:
            if requirement.status in SATISFIED_REQUIREMENT_STATUSES:
                continue
            node = nodes_by_id[requirement.requirement_node_id]
            if not node.is_required:
                continue
            options = options_by_requirement.get(node.id, [])
            if not options:
                if node.requirement_type in BROAD_REQUIREMENT_TYPES:
                    warnings.append(
                        WarningDraft(
                            warning_code="MANUAL_REVIEW_REQUIREMENT_POOL",
                            severity=AuditWarningSeverity.WARNING,
                            message=(
                                f"{node.name} is a broad requirement without stored course "
                                "candidates; the planner will not guess courses."
                            ),
                            requires_advisor_confirmation=True,
                        )
                    )
                else:
                    warnings.append(
                        WarningDraft(
                            warning_code="NO_ELIGIBLE_COURSE_FOUND",
                            severity=AuditWarningSeverity.WARNING,
                            message=(f"{node.name} has no stored course candidates for planning."),
                            requires_advisor_confirmation=True,
                        )
                    )
                continue
            if node.requirement_type not in COURSE_OPTION_REQUIREMENT_TYPES:
                continue
            for option in options:
                if option.course_id in occupied_course_ids:
                    continue
                course = courses_by_id[option.course_id]
                candidates.append(
                    PlannerCandidate(
                        requirement=requirement,
                        requirement_node=node,
                        course=course,
                        course_option=option,
                        source=(
                            AcademicPlanCourseSource.WHAT_IF_REMAINING
                            if planning_mode is AcademicPlanningMode.WHAT_IF_SCENARIO
                            else AcademicPlanCourseSource.DEGREE_AUDIT_REMAINING
                        ),
                        coverage_type=(
                            AcademicPlanCoverageType.WHAT_IF_REQUIREMENT
                            if planning_mode is AcademicPlanningMode.WHAT_IF_SCENARIO
                            else AcademicPlanCoverageType.DIRECT_REQUIREMENT
                        ),
                        unlock_value=unlock_values.get(option.course_id, 0),
                    )
                )
        candidates.sort(key=self._candidate_sort_key)
        return candidates, warnings

    def _occupied_course_ids(self, student_profile_id: UUID) -> set[UUID]:
        active_snapshot = active_course_state_snapshot(self._db, student_profile_id)
        attempts = effective_student_course_attempts(
            self._db,
            student_profile_id,
            statuses=(
                {
                    StudentCourseAttemptStatus.COMPLETED,
                    StudentCourseAttemptStatus.IN_PROGRESS,
                    StudentCourseAttemptStatus.PLANNED,
                }
                if active_snapshot is not None
                else {StudentCourseAttemptStatus.COMPLETED}
            ),
        )
        return {attempt.course_id for attempt in attempts}

    def _validate_course_state_readiness(
        self,
        student_profile_id: UUID,
    ) -> CourseStateSnapshot | None:
        snapshot = active_course_state_snapshot(self._db, student_profile_id)
        if snapshot is None:
            return None
        readiness = snapshot.readiness_payload.get("long_term_planner")
        readiness_payload = readiness if isinstance(readiness, dict) else {}
        status = str(readiness_payload.get("status") or "BLOCKED")
        if status not in {"READY", "READY_WITH_WARNINGS"}:
            blocking = readiness_payload.get("blocking_reasons")
            blocking_reasons = (
                [str(reason) for reason in blocking] if isinstance(blocking, list) else []
            )
            raise AcademicPlannerValidationError(
                "course_state_snapshot_not_ready",
                "Long-term planning is blocked by active course-state readiness: "
                + ", ".join(blocking_reasons or ["READINESS_MISSING"]),
            )
        return snapshot

    def _unlock_values(self, institution_id: UUID) -> dict[UUID, int]:
        rows = self._db.execute(
            select(CourseRuleExpression.referenced_course_id, func.count())
            .join(CourseRule, CourseRuleExpression.course_rule_id == CourseRule.id)
            .where(
                CourseRule.institution_id == institution_id,
                CourseRule.rule_type.in_([CourseRuleType.PREREQUISITE, CourseRuleType.COREQUISITE]),
                CourseRuleExpression.referenced_course_id.is_not(None),
            )
            .group_by(CourseRuleExpression.referenced_course_id)
        ).all()
        return {course_id: int(count) for course_id, count in rows if course_id is not None}

    def _candidate_sort_key(self, candidate: PlannerCandidate) -> tuple[int, int, int, str, str]:
        strictness = {
            RequirementType.REQUIRED_COURSE: 0,
            RequirementType.CAPSTONE: 1,
            RequirementType.CHOOSE_N: 2,
        }.get(candidate.requirement_node.requirement_type, 9)
        return (
            candidate.requirement.display_order,
            strictness,
            -candidate.unlock_value,
            candidate.requirement.requirement_code,
            (
                f"{candidate.course.subject_code} "
                f"{candidate.course.course_number} {candidate.course.id}"
            ),
        )

    def _place_candidates(
        self,
        *,
        run: AcademicPlanRun,
        term_states: list[PlannedTermState],
        candidates: list[PlannerCandidate],
        minimum_credits_per_term: Decimal,
        maximum_credits_per_term: Decimal,
        warnings: list[WarningDraft],
    ) -> set[UUID]:
        placed_course_ids: set[UUID] = set()
        placed_requirement_ids: set[UUID] = set()
        priority_rank = 0
        for candidate in candidates:
            if candidate.course.id in placed_course_ids:
                placed_requirement_ids.add(candidate.requirement.requirement_node_id)
                continue
            placed = self._place_single_candidate(
                run=run,
                candidate=candidate,
                term_states=term_states,
                maximum_credits_per_term=maximum_credits_per_term,
                placed_course_ids=placed_course_ids,
                priority_rank=priority_rank,
                warnings=warnings,
            )
            if placed:
                placed_requirement_ids.add(candidate.requirement.requirement_node_id)
                priority_rank += 10
            else:
                warnings.append(
                    WarningDraft(
                        warning_code="CREDIT_LIMIT_PREVENTS_PLACEMENT",
                        severity=AuditWarningSeverity.WARNING,
                        message=(
                            f"{candidate.course.subject_code} {candidate.course.course_number} "
                            "could not be placed under the supplied term credit limits."
                        ),
                        requires_advisor_confirmation=True,
                    )
                )
        for state in term_states:
            if state.planned_credits < minimum_credits_per_term:
                state.plan_term.status = (
                    AcademicPlanTermStatus.PARTIAL
                    if state.planned_credits > ZERO
                    else AcademicPlanTermStatus.BLOCKED
                )
                warnings.append(
                    WarningDraft(
                        warning_code="MINIMUM_CREDITS_NOT_MET",
                        severity=AuditWarningSeverity.WARNING,
                        message=(
                            f"{state.term.term_code} has {state.planned_credits} planned "
                            f"credits, below the requested minimum of {minimum_credits_per_term}."
                        ),
                        requires_advisor_confirmation=False,
                        term_id=state.plan_term.id,
                    )
                )
        return placed_requirement_ids

    def _place_single_candidate(
        self,
        *,
        run: AcademicPlanRun,
        candidate: PlannerCandidate,
        term_states: list[PlannedTermState],
        maximum_credits_per_term: Decimal,
        placed_course_ids: set[UUID],
        priority_rank: int,
        warnings: list[WarningDraft],
    ) -> bool:
        for term_index, state in enumerate(term_states):
            eligibility = self._eligibility(
                run.student_profile_id,
                candidate.course.id,
                state.term.id,
            )
            missing_prereqs = [
                reason.referenced_entity_id
                for reason in eligibility.blocking_reasons
                if reason.reason_code == "COMPLETED_COURSE_MISSING"
                and reason.referenced_entity_id is not None
            ]
            if missing_prereqs:
                if term_index == 0:
                    continue
                if not self._place_prerequisites(
                    run=run,
                    candidate=candidate,
                    prereq_course_ids=missing_prereqs,
                    earlier_terms=term_states[:term_index],
                    maximum_credits_per_term=maximum_credits_per_term,
                    placed_course_ids=placed_course_ids,
                    priority_rank=priority_rank,
                    warnings=warnings,
                ):
                    continue
                if not state.can_fit(candidate.credits, maximum_credits_per_term):
                    continue
                self._add_plan_course(
                    run=run,
                    term_state=state,
                    course=candidate.course,
                    requirement_node_id=candidate.requirement.requirement_node_id,
                    source=candidate.source,
                    coverage_type=candidate.coverage_type,
                    priority_rank=priority_rank + 1,
                    credits=candidate.credits,
                    eligibility_result=EligibilityOverallResult.CONDITIONALLY_ELIGIBLE,
                    planning_status=AcademicPlanCourseStatus.CONDITIONALLY_PLANNED,
                    reason_code="PREREQUISITE_PLANNED_EARLIER",
                    explanation=(
                        "Course is conditionally planned after its missing prerequisite is "
                        "placed in an earlier term."
                    ),
                    placed_course_ids=placed_course_ids,
                    warnings=warnings,
                )
                return True

            coreq_ids = [
                course_id
                for course_id in eligibility.corequisites_to_add
                if course_id not in placed_course_ids
            ]
            coreq_courses = [self._db.get(Course, course_id) for course_id in coreq_ids]
            concrete_coreqs = [course for course in coreq_courses if course is not None]
            total_credits = candidate.credits + sum(
                (course.credits_min for course in concrete_coreqs),
                ZERO,
            )
            if not state.can_fit(total_credits, maximum_credits_per_term):
                continue
            if eligibility.overall_result is EligibilityOverallResult.NOT_ELIGIBLE:
                warnings.append(
                    WarningDraft(
                        warning_code="ELIGIBILITY_CHECK_FAILED",
                        severity=AuditWarningSeverity.WARNING,
                        message=(
                            f"{candidate.course.subject_code} {candidate.course.course_number} "
                            "is not eligible in the checked term."
                        ),
                        requires_advisor_confirmation=True,
                        term_id=state.plan_term.id,
                    )
                )
                continue
            self._add_plan_course(
                run=run,
                term_state=state,
                course=candidate.course,
                requirement_node_id=candidate.requirement.requirement_node_id,
                source=candidate.source,
                coverage_type=candidate.coverage_type,
                priority_rank=priority_rank,
                credits=candidate.credits,
                eligibility_result=eligibility.overall_result,
                planning_status=self._planning_status(eligibility),
                reason_code="REQUIREMENT_REMAINING",
                explanation=(
                    "Course was placed for a remaining requirement using deterministic "
                    "requirement order, eligibility, and credit-limit checks."
                ),
                placed_course_ids=placed_course_ids,
                warnings=warnings,
            )
            for offset, coreq in enumerate(concrete_coreqs, start=1):
                self._add_plan_course(
                    run=run,
                    term_state=state,
                    course=coreq,
                    requirement_node_id=candidate.requirement.requirement_node_id,
                    source=AcademicPlanCourseSource.COREQUISITE_PAIR,
                    coverage_type=AcademicPlanCoverageType.PREREQUISITE_ONLY,
                    priority_rank=priority_rank + offset,
                    credits=coreq.credits_min,
                    eligibility_result=EligibilityOverallResult.CONDITIONALLY_ELIGIBLE,
                    planning_status=AcademicPlanCourseStatus.CONDITIONALLY_PLANNED,
                    reason_code="COREQUISITE_PAIR",
                    explanation=(
                        "Corequisite was paired in the same term as the dependent course."
                    ),
                    placed_course_ids=placed_course_ids,
                    warnings=warnings,
                )
            return True
        return False

    def _place_prerequisites(
        self,
        *,
        run: AcademicPlanRun,
        candidate: PlannerCandidate,
        prereq_course_ids: list[UUID],
        earlier_terms: list[PlannedTermState],
        maximum_credits_per_term: Decimal,
        placed_course_ids: set[UUID],
        priority_rank: int,
        warnings: list[WarningDraft],
    ) -> bool:
        for prereq_course_id in prereq_course_ids:
            if prereq_course_id in placed_course_ids:
                continue
            course = self._db.get(Course, prereq_course_id)
            if course is None:
                return False
            placed = False
            for state in earlier_terms:
                if not state.can_fit(course.credits_min, maximum_credits_per_term):
                    continue
                eligibility = self._eligibility(run.student_profile_id, course.id, state.term.id)
                if eligibility.overall_result not in {
                    EligibilityOverallResult.ELIGIBLE,
                    EligibilityOverallResult.CONDITIONALLY_ELIGIBLE,
                }:
                    warnings.append(
                        WarningDraft(
                            warning_code="PREREQUISITE_CHAIN_BLOCKS_COMPLETION",
                            severity=AuditWarningSeverity.WARNING,
                            message=(
                                f"{course.subject_code} {course.course_number} is not eligible "
                                "in an earlier term, so its dependent course cannot be planned."
                            ),
                            requires_advisor_confirmation=True,
                            term_id=state.plan_term.id,
                        )
                    )
                    continue
                self._add_plan_course(
                    run=run,
                    term_state=state,
                    course=course,
                    requirement_node_id=candidate.requirement.requirement_node_id,
                    source=AcademicPlanCourseSource.PREREQUISITE_UNLOCK,
                    coverage_type=AcademicPlanCoverageType.PREREQUISITE_ONLY,
                    priority_rank=priority_rank,
                    credits=course.credits_min,
                    eligibility_result=eligibility.overall_result,
                    planning_status=self._planning_status(eligibility),
                    reason_code="PREREQUISITE_UNLOCK",
                    explanation=(
                        "Course was placed before a dependent planned course to unlock a "
                        "stored prerequisite chain."
                    ),
                    placed_course_ids=placed_course_ids,
                    warnings=warnings,
                )
                placed = True
                break
            if not placed:
                warnings.append(
                    WarningDraft(
                        warning_code="PREREQUISITE_CHAIN_BLOCKS_COMPLETION",
                        severity=AuditWarningSeverity.WARNING,
                        message=(
                            f"{course.subject_code} {course.course_number} could not be "
                            "placed before its dependent course within the supplied horizon."
                        ),
                        requires_advisor_confirmation=True,
                    )
                )
                return False
        return True

    def _eligibility(
        self,
        student_profile_id: UUID,
        course_id: UUID,
        term_id: UUID,
    ) -> EligibilityResult:
        return self._eligibility_engine.evaluate(
            student_profile_id=student_profile_id,
            course_id=course_id,
            section_id=None,
            target_term_id=term_id,
            mode=EligibilityMode.REGISTRATION,
        )

    def _planning_status(self, eligibility: EligibilityResult) -> AcademicPlanCourseStatus:
        if eligibility.overall_result is EligibilityOverallResult.ELIGIBLE:
            return AcademicPlanCourseStatus.PLANNED
        if eligibility.overall_result is EligibilityOverallResult.CONDITIONALLY_ELIGIBLE:
            return AcademicPlanCourseStatus.CONDITIONALLY_PLANNED
        if eligibility.overall_result is EligibilityOverallResult.NOT_ELIGIBLE:
            return AcademicPlanCourseStatus.BLOCKED
        return AcademicPlanCourseStatus.MANUAL_REVIEW_REQUIRED

    def _add_plan_course(
        self,
        *,
        run: AcademicPlanRun,
        term_state: PlannedTermState,
        course: Course,
        requirement_node_id: UUID | None,
        source: AcademicPlanCourseSource,
        coverage_type: AcademicPlanCoverageType,
        priority_rank: int,
        credits: Decimal,
        eligibility_result: EligibilityOverallResult,
        planning_status: AcademicPlanCourseStatus,
        reason_code: str,
        explanation: str,
        placed_course_ids: set[UUID],
        warnings: list[WarningDraft],
    ) -> AcademicPlanCourse:
        plan_course = AcademicPlanCourse(
            id=uuid4(),
            academic_plan_term_id=term_state.plan_term.id,
            course_id=course.id,
            requirement_node_id=requirement_node_id,
            source=source,
            priority_rank=priority_rank,
            credits=quantize_credits(credits),
            eligibility_result=eligibility_result,
            planning_status=planning_status,
            reason_code=reason_code,
            explanation=explanation,
        )
        self._db.add(plan_course)
        if requirement_node_id is not None:
            self._db.add(
                AcademicPlanRequirementCoverage(
                    id=uuid4(),
                    academic_plan_run_id=run.id,
                    academic_plan_course_id=plan_course.id,
                    requirement_node_id=requirement_node_id,
                    coverage_type=coverage_type,
                    credits=quantize_credits(credits),
                )
            )
        term_state.add_credits(credits)
        placed_course_ids.add(course.id)
        warnings.extend(self._availability_warnings(course, term_state.term, plan_course.id))
        return plan_course

    def _availability_warnings(
        self,
        course: Course,
        term: AcademicTerm,
        plan_course_id: UUID,
    ) -> list[WarningDraft]:
        sections = self._db.scalars(
            select(Section)
            .where(Section.course_id == course.id, Section.term_id == term.id)
            .order_by(Section.status, Section.section_code, Section.id)
        ).all()
        if sections:
            if all(
                section.status in {SectionStatus.CLOSED, SectionStatus.CANCELLED}
                for section in sections
            ):
                return [
                    WarningDraft(
                        warning_code="CLOSED_SECTION_NOT_ACADEMIC_IMPOSSIBILITY",
                        severity=AuditWarningSeverity.WARNING,
                        message=(
                            f"{course.subject_code} {course.course_number} has only closed or "
                            "cancelled mock sections in this term; long-term planning treats "
                            "that as a warning, not seat monitoring."
                        ),
                        requires_advisor_confirmation=True,
                        plan_course_id=plan_course_id,
                    )
                ]
            return []

        term_type = self._term_type(term)
        matching_pattern = self._db.scalar(
            select(CourseOfferingPattern).where(
                CourseOfferingPattern.course_id == course.id,
                CourseOfferingPattern.campus_id == term.campus_id,
                CourseOfferingPattern.term_type == term_type,
            )
        )
        if (
            matching_pattern is not None
            and matching_pattern.frequency_type is not FrequencyType.UNKNOWN
        ):
            return []
        any_pattern = self._db.scalar(
            select(CourseOfferingPattern).where(
                CourseOfferingPattern.course_id == course.id,
                CourseOfferingPattern.campus_id == term.campus_id,
            )
        )
        if any_pattern is None:
            return [
                WarningDraft(
                    warning_code="COURSE_OFFERING_PATTERN_UNKNOWN",
                    severity=AuditWarningSeverity.WARNING,
                    message=(
                        f"No mock offering pattern or section is stored for "
                        f"{course.subject_code} {course.course_number} in {term.term_code}."
                    ),
                    requires_advisor_confirmation=True,
                    plan_course_id=plan_course_id,
                )
            ]
        return [
            WarningDraft(
                warning_code="COURSE_NOT_LIKELY_OFFERED",
                severity=AuditWarningSeverity.WARNING,
                message=(
                    f"Stored mock offering patterns do not indicate "
                    f"{course.subject_code} {course.course_number} is likely in {term.term_code}."
                ),
                requires_advisor_confirmation=True,
                plan_course_id=plan_course_id,
            )
        ]

    def _term_type(self, term: AcademicTerm) -> object:
        code = term.term_code.upper()
        name = term.name.upper()
        if "FA" in code or "FALL" in name:
            return TermType.FALL
        if "SP" in code or "SPRING" in name:
            return TermType.SPRING
        if "SU" in code or "SUMMER" in name:
            return TermType.SUMMER
        if "WI" in code or "WINTER" in name:
            return TermType.WINTER
        return TermType.OTHER

    def _persist_warnings(self, run_id: UUID, warnings: list[WarningDraft]) -> None:
        for warning in warnings:
            self._db.add(
                AcademicPlanWarning(
                    id=uuid4(),
                    academic_plan_run_id=run_id,
                    academic_plan_term_id=warning.term_id,
                    academic_plan_course_id=warning.plan_course_id,
                    warning_code=warning.warning_code,
                    severity=warning.severity,
                    message=warning.message,
                    requires_advisor_confirmation=warning.requires_advisor_confirmation,
                )
            )


def source_snapshot_hash(*, student_profile_id: UUID, program_version_id: UUID) -> str:
    payload = f"{student_profile_id}|{program_version_id}|{ENGINE_VERSION}"
    return sha256(payload.encode("utf-8")).hexdigest()
