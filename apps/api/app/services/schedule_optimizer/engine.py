from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Protocol, TypedDict
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import (
    AcademicPlanCourse,
    AcademicPlanRun,
    AcademicPlanTerm,
    AcademicTerm,
    AuditMode,
    AuditWarningSeverity,
    Course,
    CourseStateSnapshot,
    DayOfWeek,
    EligibilityMode,
    EligibilityOverallResult,
    RequirementCourseOption,
    RequirementEvaluationStatus,
    RequirementNode,
    RequirementType,
    ScheduleConflict,
    ScheduleConflictType,
    ScheduleConstraintSet,
    ScheduleOptimizationRun,
    ScheduleOption,
    ScheduleOptionSection,
    ScheduleOptionStatus,
    SchedulePlanningMode,
    ScheduleRepairSuggestion,
    ScheduleRunStatus,
    ScheduleWarning,
    Section,
    SectionMeeting,
    SectionModality,
    SectionStatus,
    StudentAcademicProgram,
    StudentAcademicProgramStatus,
    StudentProfile,
    StudentProgramType,
)
from app.services.course_eligibility.engine import CourseEligibilityEngine
from app.services.course_eligibility.result import EligibilityResult
from app.services.degree_audit.engine import DegreeAuditEngine, quantize_credits
from app.services.schedule_optimizer.exceptions import ScheduleOptimizerValidationError

ENGINE_VERSION = "phase-6b-schedule-optimizer-v1"
ZERO = Decimal("0.0")
MAX_CANDIDATE_COURSES = 6
MAX_SECTIONS_PER_COURSE = 8
MAX_COMBINATIONS_EVALUATED = 500
DEFAULT_PREFERENCE_WEIGHT = Decimal("1.0")

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


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True)
class UnavailableBlock:
    day_of_week: DayOfWeek
    start_time: time
    end_time: time


@dataclass(frozen=True)
class CandidateCourse:
    course: Course
    priority: int
    reason_code: str


@dataclass(frozen=True)
class SectionCandidate:
    section: Section
    course: Course
    meetings: tuple[SectionMeeting, ...]
    eligibility: EligibilityResult
    credits: Decimal
    selection_reason: str
    warning_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConflictDraft:
    conflict_type: ScheduleConflictType
    message: str
    section_id: UUID | None = None
    other_section_id: UUID | None = None
    day_of_week: DayOfWeek | None = None
    start_time: time | None = None
    end_time: time | None = None
    option_id: UUID | None = None


@dataclass(frozen=True)
class WarningDraft:
    warning_code: str
    severity: AuditWarningSeverity
    message: str
    requires_advisor_confirmation: bool
    option_id: UUID | None = None


@dataclass
class OptionDraft:
    selected_sections: tuple[SectionCandidate, ...]
    status: ScheduleOptionStatus
    total_credits: Decimal
    class_days_count: int
    earliest_start_time: time | None
    latest_end_time: time | None
    total_gap_minutes: int
    score: Decimal
    credit_score: Decimal
    compactness_score: Decimal
    days_score: Decimal
    gap_score: Decimal
    modality_score: Decimal
    time_preference_score: Decimal
    priority_score: Decimal
    penalty_score: Decimal
    score_explanation: list[dict[str, str]]
    explanation: str
    diversity_rank: int = 1
    difference_summary: str = "Top ranked option."
    shared_section_count_with_previous_option: int = 0
    warnings: list[WarningDraft] = field(default_factory=list)


@dataclass(frozen=True)
class RepairSuggestionDraft:
    suggestion_type: str
    affected_constraint: str | None
    affected_course_id: UUID | None
    affected_section_id: UUID | None
    estimated_impact: str
    message: str
    requires_advisor_confirmation: bool


class ScoreValues(TypedDict):
    total_score: Decimal
    credit_score: Decimal
    compactness_score: Decimal
    days_score: Decimal
    gap_score: Decimal
    modality_score: Decimal
    time_preference_score: Decimal
    priority_score: Decimal
    penalty_score: Decimal
    score_explanation: list[dict[str, str]]
    explanation: str


class ScheduleOptimizer(Protocol):
    def generate_options(
        self,
        *,
        candidates: list[CandidateCourse],
        section_groups: dict[UUID, list[SectionCandidate]],
        minimum_credits: Decimal,
        maximum_credits: Decimal,
        preferred_credits: Decimal,
        requested_option_count: int,
        prefer_online: bool,
        prefer_compact_schedule: bool,
        prefer_fewer_days: bool,
        prefer_in_person: bool,
        avoid_early_start: bool,
        avoid_late_end: bool,
        preference_weights: dict[str, Decimal],
        course_priority_weights: dict[UUID, Decimal],
        section_priority_weights: dict[UUID, Decimal],
        prefer_no_gaps: bool,
        prefer_morning: bool,
        prefer_afternoon: bool,
        diversity_mode: str,
        allow_partial_options: bool,
        max_combinations: int,
        warnings: list[WarningDraft],
    ) -> tuple[list[OptionDraft], list[ConflictDraft]]: ...


class ScheduleOptimizerApplicationService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._eligibility_engine = CourseEligibilityEngine(db)

    def create_schedule(
        self,
        *,
        student_profile_id: UUID,
        term_id: UUID,
        academic_plan_run_id: UUID | None,
        planning_mode: SchedulePlanningMode,
        candidate_course_ids: list[UUID],
        minimum_credits: Decimal,
        maximum_credits: Decimal,
        preferred_credits: Decimal,
        requested_option_count: int,
        excluded_days: list[DayOfWeek],
        unavailable_time_blocks: list[dict[str, str]],
        earliest_start_time: time | None,
        latest_end_time: time | None,
        allowed_modalities: list[SectionModality],
        excluded_modalities: list[SectionModality],
        required_course_ids: list[UUID],
        excluded_course_ids: list[UUID],
        required_section_ids: list[UUID],
        excluded_section_ids: list[UUID],
        prefer_online: bool,
        prefer_compact_schedule: bool,
        prefer_fewer_days: bool,
        prefer_in_person: bool,
        avoid_early_start: bool,
        avoid_late_end: bool,
        allow_permission_required: bool,
        minimum_gap_minutes: int | None = None,
        maximum_gap_minutes: int | None = None,
        preference_weights: dict[str, Decimal] | None = None,
        course_priority_weights: dict[UUID, Decimal] | None = None,
        section_priority_weights: dict[UUID, Decimal] | None = None,
        prefer_no_gaps: bool = False,
        prefer_morning: bool = False,
        prefer_afternoon: bool = False,
        diversity_mode: str = "STANDARD",
        allow_partial_options: bool = True,
        max_combinations: int = MAX_COMBINATIONS_EVALUATED,
    ) -> ScheduleOptimizationRun:
        preference_weights = preference_weights or {}
        course_priority_weights = course_priority_weights or {}
        section_priority_weights = section_priority_weights or {}
        self._validate_credit_inputs(
            minimum_credits=minimum_credits,
            maximum_credits=maximum_credits,
            preferred_credits=preferred_credits,
            requested_option_count=requested_option_count,
        )
        self._validate_phase_6b_inputs(
            preference_weights=preference_weights,
            course_priority_weights=course_priority_weights,
            section_priority_weights=section_priority_weights,
            diversity_mode=diversity_mode,
            max_combinations=max_combinations,
        )
        student = self._validate_student(student_profile_id)
        term = self._validate_term(term_id, student)
        self._validate_course_state_readiness(student_profile_id)
        academic_plan = self._validate_plan(
            academic_plan_run_id=academic_plan_run_id,
            student_profile_id=student_profile_id,
            term_id=term_id,
            planning_mode=planning_mode,
        )
        blocks = self._parse_unavailable_blocks(unavailable_time_blocks)
        self._validate_section_ids(
            section_ids=[*required_section_ids, *excluded_section_ids],
            term=term,
            student=student,
        )

        run_id = uuid4()
        run = ScheduleOptimizationRun(
            id=run_id,
            student_profile_id=student_profile_id,
            term_id=term_id,
            academic_plan_run_id=academic_plan.id if academic_plan else None,
            planning_mode=planning_mode,
            status=ScheduleRunStatus.RUNNING,
            engine_version=ENGINE_VERSION,
            minimum_credits=quantize_credits(minimum_credits),
            maximum_credits=quantize_credits(maximum_credits),
            preferred_credits=quantize_credits(preferred_credits),
            requested_option_count=requested_option_count,
        )
        self._db.add(run)
        self._db.flush()
        self._persist_constraints(
            run_id=run.id,
            candidate_course_ids=candidate_course_ids,
            excluded_days=excluded_days,
            unavailable_time_blocks=unavailable_time_blocks,
            earliest_start_time=earliest_start_time,
            latest_end_time=latest_end_time,
            minimum_gap_minutes=minimum_gap_minutes,
            maximum_gap_minutes=maximum_gap_minutes,
            allowed_modalities=allowed_modalities,
            excluded_modalities=excluded_modalities,
            required_course_ids=required_course_ids,
            excluded_course_ids=excluded_course_ids,
            required_section_ids=required_section_ids,
            excluded_section_ids=excluded_section_ids,
            prefer_online=prefer_online,
            prefer_compact_schedule=prefer_compact_schedule,
            prefer_fewer_days=prefer_fewer_days,
            prefer_in_person=prefer_in_person,
            avoid_early_start=avoid_early_start,
            avoid_late_end=avoid_late_end,
            allow_permission_required=allow_permission_required,
            preference_weights=preference_weights,
            course_priority_weights=course_priority_weights,
            section_priority_weights=section_priority_weights,
            prefer_no_gaps=prefer_no_gaps,
            prefer_morning=prefer_morning,
            prefer_afternoon=prefer_afternoon,
            diversity_mode=diversity_mode,
            allow_partial_options=allow_partial_options,
            max_combinations=max_combinations,
        )

        warnings: list[WarningDraft] = [
            WarningDraft(
                warning_code="MOCK_SECTION_DATA_NOT_OFFICIAL",
                severity=AuditWarningSeverity.INFO,
                message=(
                    "Mock section data - not official university policy. Generated schedules "
                    "are not registration and need advisor or school confirmation."
                ),
                requires_advisor_confirmation=True,
            )
        ]
        conflicts: list[ConflictDraft] = []
        try:
            candidates = self._candidate_courses(
                student=student,
                term=term,
                academic_plan=academic_plan,
                planning_mode=planning_mode,
                candidate_course_ids=candidate_course_ids,
                required_course_ids=required_course_ids,
                excluded_course_ids=excluded_course_ids,
                warnings=warnings,
            )
            section_groups = self._section_groups(
                student=student,
                term=term,
                candidates=candidates,
                excluded_days=set(excluded_days),
                unavailable_blocks=blocks,
                earliest_start_time=earliest_start_time,
                latest_end_time=latest_end_time,
                allowed_modalities=set(allowed_modalities),
                excluded_modalities=set(excluded_modalities),
                required_section_ids=set(required_section_ids),
                excluded_section_ids=set(excluded_section_ids),
                allow_permission_required=allow_permission_required,
                warnings=warnings,
                conflicts=conflicts,
            )
            optimizer: ScheduleOptimizer = BoundedSearchScheduleOptimizer(self)
            options, optionless_conflicts = optimizer.generate_options(
                candidates=candidates,
                section_groups=section_groups,
                minimum_credits=quantize_credits(minimum_credits),
                maximum_credits=quantize_credits(maximum_credits),
                preferred_credits=quantize_credits(preferred_credits),
                requested_option_count=requested_option_count,
                prefer_online=prefer_online,
                prefer_compact_schedule=prefer_compact_schedule,
                prefer_fewer_days=prefer_fewer_days,
                prefer_in_person=prefer_in_person,
                avoid_early_start=avoid_early_start,
                avoid_late_end=avoid_late_end,
                preference_weights=preference_weights,
                course_priority_weights=course_priority_weights,
                section_priority_weights=section_priority_weights,
                prefer_no_gaps=prefer_no_gaps,
                prefer_morning=prefer_morning,
                prefer_afternoon=prefer_afternoon,
                diversity_mode=diversity_mode,
                allow_partial_options=allow_partial_options,
                max_combinations=max_combinations,
                warnings=warnings,
            )
            conflicts.extend(optionless_conflicts)
            repair_suggestions = self._repair_suggestions(
                conflicts=conflicts,
                excluded_days=set(excluded_days),
                required_section_ids=set(required_section_ids),
                minimum_credits=quantize_credits(minimum_credits),
                maximum_credits=quantize_credits(maximum_credits),
                allow_permission_required=allow_permission_required,
            )
            if not options:
                warnings.append(
                    WarningDraft(
                        warning_code="NO_FEASIBLE_SCHEDULE_FOUND",
                        severity=AuditWarningSeverity.WARNING,
                        message=(
                            "No feasible mock schedule satisfied the hard constraints. "
                            "Try relaxing time, modality, or course constraints."
                        ),
                        requires_advisor_confirmation=True,
                    )
                )
                options = [
                    OptionDraft(
                        selected_sections=(),
                        status=ScheduleOptionStatus.INFEASIBLE,
                        total_credits=ZERO,
                        class_days_count=0,
                        earliest_start_time=None,
                        latest_end_time=None,
                        total_gap_minutes=0,
                        score=Decimal("0.00"),
                        credit_score=Decimal("0.00"),
                        compactness_score=Decimal("0.00"),
                        days_score=Decimal("0.00"),
                        gap_score=Decimal("0.00"),
                        modality_score=Decimal("0.00"),
                        time_preference_score=Decimal("0.00"),
                        priority_score=Decimal("0.00"),
                        penalty_score=Decimal("0.00"),
                        score_explanation=[
                            {
                                "reason_code": "NO_FEASIBLE_SCHEDULE",
                                "score": "0.00",
                                "explanation": "No schedule satisfied the hard constraints.",
                            }
                        ],
                        explanation=(
                            "No sections could be selected under the hard constraints; "
                            "score is zero because no schedule exists."
                        ),
                    )
                ]
            self._persist_conflicts(run.id, conflicts)
            option_warning_count = self._persist_options(run.id, options)
            self._persist_warnings(run.id, warnings)
            self._persist_repair_suggestions(run.id, repair_suggestions)
            run.status = (
                ScheduleRunStatus.COMPLETED_WITH_WARNINGS
                if warnings or option_warning_count > 0
                else ScheduleRunStatus.COMPLETED
            )
            run.completed_at = utc_now()
            self._db.commit()
        except Exception:
            self._db.rollback()
            failed = ScheduleOptimizationRun(
                id=run_id,
                student_profile_id=student_profile_id,
                term_id=term_id,
                academic_plan_run_id=academic_plan_run_id,
                planning_mode=planning_mode,
                status=ScheduleRunStatus.FAILED,
                engine_version=ENGINE_VERSION,
                minimum_credits=quantize_credits(minimum_credits),
                maximum_credits=quantize_credits(maximum_credits),
                preferred_credits=quantize_credits(preferred_credits),
                requested_option_count=requested_option_count,
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
        minimum_credits: Decimal,
        maximum_credits: Decimal,
        preferred_credits: Decimal,
        requested_option_count: int,
    ) -> None:
        if minimum_credits < ZERO or maximum_credits < ZERO or preferred_credits < ZERO:
            raise ScheduleOptimizerValidationError(
                "invalid_credit_limits",
                "Schedule credit limits cannot be negative.",
            )
        if maximum_credits < minimum_credits:
            raise ScheduleOptimizerValidationError(
                "invalid_credit_limits",
                "maximum_credits must be greater than or equal to minimum_credits.",
            )
        if preferred_credits > maximum_credits:
            raise ScheduleOptimizerValidationError(
                "invalid_credit_limits",
                "preferred_credits cannot exceed maximum_credits.",
            )
        if requested_option_count <= 0 or requested_option_count > 20:
            raise ScheduleOptimizerValidationError(
                "invalid_option_count",
                "requested_option_count must be between 1 and 20.",
            )

    def _validate_phase_6b_inputs(
        self,
        *,
        preference_weights: dict[str, Decimal],
        course_priority_weights: dict[UUID, Decimal],
        section_priority_weights: dict[UUID, Decimal],
        diversity_mode: str,
        max_combinations: int,
    ) -> None:
        all_weights = [
            *preference_weights.values(),
            *course_priority_weights.values(),
            *section_priority_weights.values(),
        ]
        if any(weight < ZERO for weight in all_weights):
            raise ScheduleOptimizerValidationError(
                "invalid_preference_weight",
                "Schedule preference and priority weights cannot be negative.",
            )
        if diversity_mode not in {"STANDARD", "HIGH"}:
            raise ScheduleOptimizerValidationError(
                "invalid_diversity_mode",
                "diversity_mode must be STANDARD or HIGH.",
            )
        if max_combinations <= 0 or max_combinations > 5000:
            raise ScheduleOptimizerValidationError(
                "invalid_search_limit",
                "max_combinations must be between 1 and 5000.",
            )

    def _validate_student(self, student_profile_id: UUID) -> StudentProfile:
        student = self._db.get(StudentProfile, student_profile_id)
        if student is None:
            raise ScheduleOptimizerValidationError(
                "not_found",
                f"StudentProfile {student_profile_id} was not found.",
            )
        return student

    def _validate_term(self, term_id: UUID, student: StudentProfile) -> AcademicTerm:
        term = self._db.get(AcademicTerm, term_id)
        if term is None:
            raise ScheduleOptimizerValidationError(
                "not_found",
                f"AcademicTerm {term_id} was not found.",
            )
        if term.institution_id != student.home_institution_id:
            raise ScheduleOptimizerValidationError(
                "institution_scope_mismatch",
                "Student and target term must belong to the same institution.",
            )
        return term

    def _validate_section_ids(
        self,
        *,
        section_ids: list[UUID],
        term: AcademicTerm,
        student: StudentProfile,
    ) -> None:
        for section_id in dict.fromkeys(section_ids):
            section = self._db.get(Section, section_id)
            if section is None:
                raise ScheduleOptimizerValidationError(
                    "invalid_section",
                    f"Section {section_id} was not found.",
                )
            if section.institution_id != student.home_institution_id or section.term_id != term.id:
                raise ScheduleOptimizerValidationError(
                    "invalid_section",
                    "Required or excluded sections must belong to the target term and institution.",
                )

    def _validate_plan(
        self,
        *,
        academic_plan_run_id: UUID | None,
        student_profile_id: UUID,
        term_id: UUID,
        planning_mode: SchedulePlanningMode,
    ) -> AcademicPlanRun | None:
        if (
            planning_mode is SchedulePlanningMode.FROM_LONG_TERM_PLAN
            and academic_plan_run_id is None
        ):
            raise ScheduleOptimizerValidationError(
                "academic_plan_required",
                "FROM_LONG_TERM_PLAN mode requires academic_plan_run_id.",
            )
        if academic_plan_run_id is None:
            return None
        plan = self._db.get(AcademicPlanRun, academic_plan_run_id)
        if plan is None:
            raise ScheduleOptimizerValidationError(
                "not_found",
                f"AcademicPlanRun {academic_plan_run_id} was not found.",
            )
        if plan.student_profile_id != student_profile_id:
            raise ScheduleOptimizerValidationError(
                "academic_plan_student_mismatch",
                "Academic plan must belong to the requested student.",
            )
        has_target_term = self._db.scalar(
            select(AcademicPlanTerm.id).where(
                AcademicPlanTerm.academic_plan_run_id == plan.id,
                AcademicPlanTerm.term_id == term_id,
            )
        )
        if has_target_term is None and planning_mode is SchedulePlanningMode.FROM_LONG_TERM_PLAN:
            raise ScheduleOptimizerValidationError(
                "academic_plan_term_missing",
                "Academic plan has no term matching the requested schedule term.",
            )
        return plan

    def _validate_course_state_readiness(self, student_profile_id: UUID) -> None:
        active_snapshot = self._db.scalar(
            select(CourseStateSnapshot)
            .where(
                CourseStateSnapshot.student_profile_id == student_profile_id,
                CourseStateSnapshot.is_active.is_(True),
            )
            .order_by(CourseStateSnapshot.applied_at.desc(), CourseStateSnapshot.id.desc())
        )
        if active_snapshot is None:
            return
        readiness = active_snapshot.readiness_payload.get("semester_schedule")
        readiness_payload = readiness if isinstance(readiness, dict) else {}
        status = str(readiness_payload.get("status") or "BLOCKED")
        if status in {"READY", "READY_WITH_WARNINGS"}:
            return
        blocking = readiness_payload.get("blocking_reasons")
        reason_codes = blocking if isinstance(blocking, list) and blocking else [status]
        raise ScheduleOptimizerValidationError(
            "course_state_schedule_not_ready",
            "Semester schedule optimization is blocked by active course-state readiness: "
            + ", ".join(str(reason) for reason in reason_codes),
        )

    def _parse_unavailable_blocks(
        self,
        unavailable_time_blocks: list[dict[str, str]],
    ) -> list[UnavailableBlock]:
        blocks: list[UnavailableBlock] = []
        for block in unavailable_time_blocks:
            try:
                day = DayOfWeek(block["day_of_week"])
                start = time.fromisoformat(block["start_time"])
                end = time.fromisoformat(block["end_time"])
            except (KeyError, ValueError) as error:
                raise ScheduleOptimizerValidationError(
                    "invalid_unavailable_block",
                    "Unavailable time blocks must include day_of_week, start_time, and end_time.",
                ) from error
            if end <= start:
                raise ScheduleOptimizerValidationError(
                    "invalid_unavailable_block",
                    "Unavailable time block end_time must be after start_time.",
                )
            blocks.append(UnavailableBlock(day, start, end))
        return blocks

    def _persist_constraints(
        self,
        *,
        run_id: UUID,
        candidate_course_ids: list[UUID],
        excluded_days: list[DayOfWeek],
        unavailable_time_blocks: list[dict[str, str]],
        earliest_start_time: time | None,
        latest_end_time: time | None,
        minimum_gap_minutes: int | None,
        maximum_gap_minutes: int | None,
        allowed_modalities: list[SectionModality],
        excluded_modalities: list[SectionModality],
        required_course_ids: list[UUID],
        excluded_course_ids: list[UUID],
        required_section_ids: list[UUID],
        excluded_section_ids: list[UUID],
        prefer_online: bool,
        prefer_compact_schedule: bool,
        prefer_fewer_days: bool,
        prefer_in_person: bool,
        avoid_early_start: bool,
        avoid_late_end: bool,
        allow_permission_required: bool,
        preference_weights: dict[str, Decimal],
        course_priority_weights: dict[UUID, Decimal],
        section_priority_weights: dict[UUID, Decimal],
        prefer_no_gaps: bool,
        prefer_morning: bool,
        prefer_afternoon: bool,
        diversity_mode: str,
        allow_partial_options: bool,
        max_combinations: int,
    ) -> None:
        self._db.add(
            ScheduleConstraintSet(
                id=uuid4(),
                schedule_optimization_run_id=run_id,
                excluded_days=[day.value for day in excluded_days],
                unavailable_time_blocks=unavailable_time_blocks,
                earliest_start_time=earliest_start_time,
                latest_end_time=latest_end_time,
                minimum_gap_minutes=minimum_gap_minutes,
                maximum_gap_minutes=maximum_gap_minutes,
                candidate_course_ids=[str(course_id) for course_id in candidate_course_ids],
                allowed_modalities=[modality.value for modality in allowed_modalities],
                excluded_modalities=[modality.value for modality in excluded_modalities],
                required_course_ids=[str(course_id) for course_id in required_course_ids],
                excluded_course_ids=[str(course_id) for course_id in excluded_course_ids],
                required_section_ids=[str(section_id) for section_id in required_section_ids],
                excluded_section_ids=[str(section_id) for section_id in excluded_section_ids],
                prefer_online=prefer_online,
                prefer_compact_schedule=prefer_compact_schedule,
                prefer_fewer_days=prefer_fewer_days,
                prefer_in_person=prefer_in_person,
                avoid_early_start=avoid_early_start,
                avoid_late_end=avoid_late_end,
                allow_permission_required=allow_permission_required,
                preference_weights={
                    key: str(value) for key, value in sorted(preference_weights.items())
                },
                course_priority_weights={
                    str(key): str(value)
                    for key, value in sorted(
                        course_priority_weights.items(), key=lambda item: str(item[0])
                    )
                },
                section_priority_weights={
                    str(key): str(value)
                    for key, value in sorted(
                        section_priority_weights.items(), key=lambda item: str(item[0])
                    )
                },
                prefer_no_gaps=prefer_no_gaps,
                prefer_morning=prefer_morning,
                prefer_afternoon=prefer_afternoon,
                diversity_mode=diversity_mode,
                allow_partial_options=allow_partial_options,
                max_combinations=max_combinations,
            )
        )
        self._db.flush()

    def _candidate_courses(
        self,
        *,
        student: StudentProfile,
        term: AcademicTerm,
        academic_plan: AcademicPlanRun | None,
        planning_mode: SchedulePlanningMode,
        candidate_course_ids: list[UUID],
        required_course_ids: list[UUID],
        excluded_course_ids: list[UUID],
        warnings: list[WarningDraft],
    ) -> list[CandidateCourse]:
        if candidate_course_ids:
            raw_ids = list(dict.fromkeys([*candidate_course_ids, *required_course_ids]))
            candidates = [
                CandidateCourse(
                    self._validate_candidate_course(course_id, student),
                    index,
                    "MANUAL_CANDIDATE",
                )
                for index, course_id in enumerate(raw_ids)
            ]
        elif planning_mode is SchedulePlanningMode.FROM_LONG_TERM_PLAN and academic_plan:
            candidates = self._courses_from_academic_plan(academic_plan.id, term.id, student)
        else:
            candidates = self._courses_from_degree_audit(student, warnings)

        excluded = set(excluded_course_ids)
        candidates = [candidate for candidate in candidates if candidate.course.id not in excluded]
        candidates = sorted(candidates, key=self._candidate_sort_key)
        if len(candidates) > MAX_CANDIDATE_COURSES:
            warnings.append(
                WarningDraft(
                    warning_code="SCHEDULE_SEARCH_LIMIT_REACHED",
                    severity=AuditWarningSeverity.WARNING,
                    message=(
                        f"Only the first {MAX_CANDIDATE_COURSES} mock candidate courses were "
                        "evaluated; the result is not silently presented as exhaustive."
                    ),
                    requires_advisor_confirmation=True,
                )
            )
            candidates = candidates[:MAX_CANDIDATE_COURSES]
        if not candidates:
            raise ScheduleOptimizerValidationError(
                "no_candidate_courses",
                "No candidate courses are available for schedule generation.",
            )
        return candidates

    def _validate_candidate_course(self, course_id: UUID, student: StudentProfile) -> Course:
        course = self._db.get(Course, course_id)
        if course is None:
            raise ScheduleOptimizerValidationError(
                "not_found",
                f"Course {course_id} was not found.",
            )
        if course.institution_id != student.home_institution_id:
            raise ScheduleOptimizerValidationError(
                "institution_scope_mismatch",
                "Candidate course and student must belong to the same institution.",
            )
        return course

    def _courses_from_academic_plan(
        self,
        academic_plan_run_id: UUID,
        term_id: UUID,
        student: StudentProfile,
    ) -> list[CandidateCourse]:
        rows = self._db.execute(
            select(AcademicPlanCourse, Course)
            .join(AcademicPlanTerm, AcademicPlanCourse.academic_plan_term_id == AcademicPlanTerm.id)
            .join(Course, AcademicPlanCourse.course_id == Course.id)
            .where(
                AcademicPlanTerm.academic_plan_run_id == academic_plan_run_id,
                AcademicPlanTerm.term_id == term_id,
            )
            .order_by(AcademicPlanCourse.priority_rank, Course.subject_code, Course.course_number)
        ).all()
        return [
            CandidateCourse(course, plan_course.priority_rank, "ACADEMIC_PLAN_TERM")
            for plan_course, course in rows
            if course.institution_id == student.home_institution_id
        ]

    def _courses_from_degree_audit(
        self,
        student: StudentProfile,
        warnings: list[WarningDraft],
    ) -> list[CandidateCourse]:
        active_program = self._db.scalar(
            select(StudentAcademicProgram).where(
                StudentAcademicProgram.student_profile_id == student.id,
                StudentAcademicProgram.program_type == StudentProgramType.PRIMARY_MAJOR,
                StudentAcademicProgram.status == StudentAcademicProgramStatus.ACTIVE,
            )
        )
        if active_program is None:
            raise ScheduleOptimizerValidationError(
                "program_not_declared",
                "FROM_DEGREE_AUDIT mode requires an active primary program.",
            )
        audit = DegreeAuditEngine(self._db).evaluate(
            student.id,
            active_program.program_version_id,
            AuditMode.CURRENT,
        )
        requirement_ids = [requirement.requirement_node_id for requirement in audit.requirements]
        nodes_by_id = {
            node.id: node
            for node in self._db.scalars(
                select(RequirementNode).where(RequirementNode.id.in_(requirement_ids))
            ).all()
        }
        options_by_requirement: dict[UUID, list[RequirementCourseOption]] = defaultdict(list)
        if requirement_ids:
            for option in self._db.scalars(
                select(RequirementCourseOption)
                .where(RequirementCourseOption.requirement_node_id.in_(requirement_ids))
                .order_by(
                    RequirementCourseOption.requirement_node_id,
                    RequirementCourseOption.display_order,
                    RequirementCourseOption.id,
                )
            ).all():
                options_by_requirement[option.requirement_node_id].append(option)
        course_ids: list[UUID] = []
        priority = 0
        for requirement in audit.requirements:
            if requirement.status in SATISFIED_REQUIREMENT_STATUSES:
                continue
            node = nodes_by_id[requirement.requirement_node_id]
            if node.requirement_type not in COURSE_OPTION_REQUIREMENT_TYPES:
                warnings.append(
                    WarningDraft(
                        warning_code="MANUAL_REVIEW_REQUIREMENT_POOL",
                        severity=AuditWarningSeverity.WARNING,
                        message=(
                            f"{node.name} is too broad for automatic section scheduling; "
                            "candidate courses must be confirmed."
                        ),
                        requires_advisor_confirmation=True,
                    )
                )
                continue
            for option in options_by_requirement.get(node.id, []):
                if option.course_id not in course_ids:
                    course_ids.append(option.course_id)
                    priority += 10
        courses = {
            course.id: course
            for course in self._db.scalars(select(Course).where(Course.id.in_(course_ids))).all()
        }
        return [
            CandidateCourse(courses[course_id], index, "DEGREE_AUDIT_REMAINING")
            for index, course_id in enumerate(course_ids)
            if course_id in courses
        ]

    def _candidate_sort_key(self, candidate: CandidateCourse) -> tuple[int, str, str, str]:
        return (
            candidate.priority,
            candidate.course.subject_code,
            candidate.course.course_number,
            str(candidate.course.id),
        )

    def _section_groups(
        self,
        *,
        student: StudentProfile,
        term: AcademicTerm,
        candidates: list[CandidateCourse],
        excluded_days: set[DayOfWeek],
        unavailable_blocks: list[UnavailableBlock],
        earliest_start_time: time | None,
        latest_end_time: time | None,
        allowed_modalities: set[SectionModality],
        excluded_modalities: set[SectionModality],
        required_section_ids: set[UUID],
        excluded_section_ids: set[UUID],
        allow_permission_required: bool,
        warnings: list[WarningDraft],
        conflicts: list[ConflictDraft],
    ) -> dict[UUID, list[SectionCandidate]]:
        groups: dict[UUID, list[SectionCandidate]] = {}
        for candidate in candidates:
            sections = self._db.scalars(
                select(Section)
                .where(
                    Section.course_id == candidate.course.id,
                    Section.term_id == term.id,
                )
                .order_by(Section.section_code, Section.modality, Section.id)
            ).all()
            if not sections:
                self._add_no_section_warning(candidate.course, warnings, conflicts)
                continue
            required_for_course = {
                section_id
                for section_id in required_section_ids
                if any(section.id == section_id for section in sections)
            }
            selected: list[SectionCandidate] = []
            for section in sections:
                if required_for_course and section.id not in required_for_course:
                    continue
                section_candidate = self._section_candidate(
                    student=student,
                    term=term,
                    course=candidate.course,
                    section=section,
                    excluded_days=excluded_days,
                    unavailable_blocks=unavailable_blocks,
                    earliest_start_time=earliest_start_time,
                    latest_end_time=latest_end_time,
                    allowed_modalities=allowed_modalities,
                    excluded_modalities=excluded_modalities,
                    excluded_section_ids=excluded_section_ids,
                    allow_permission_required=allow_permission_required,
                    warnings=warnings,
                    conflicts=conflicts,
                )
                if section_candidate is not None:
                    selected.append(section_candidate)
            if not selected:
                self._add_no_section_warning(candidate.course, warnings, conflicts)
                continue
            groups[candidate.course.id] = sorted(selected, key=self._section_sort_key)[
                :MAX_SECTIONS_PER_COURSE
            ]
        return groups

    def _section_candidate(
        self,
        *,
        student: StudentProfile,
        term: AcademicTerm,
        course: Course,
        section: Section,
        excluded_days: set[DayOfWeek],
        unavailable_blocks: list[UnavailableBlock],
        earliest_start_time: time | None,
        latest_end_time: time | None,
        allowed_modalities: set[SectionModality],
        excluded_modalities: set[SectionModality],
        excluded_section_ids: set[UUID],
        allow_permission_required: bool,
        warnings: list[WarningDraft],
        conflicts: list[ConflictDraft],
    ) -> SectionCandidate | None:
        if section.id in excluded_section_ids:
            return None
        if allowed_modalities and section.modality not in allowed_modalities:
            return None
        if section.modality in excluded_modalities:
            return None
        if section.status in {SectionStatus.CLOSED, SectionStatus.CANCELLED}:
            warnings.append(
                WarningDraft(
                    warning_code="CLOSED_SECTION_INFORMATIONAL",
                    severity=AuditWarningSeverity.WARNING,
                    message=(
                        f"{course.subject_code} {course.course_number} section "
                        f"{section.section_code} is {section.status.value}; it is kept only "
                        "as informational mock data and is not selected."
                    ),
                    requires_advisor_confirmation=True,
                )
            )
            return None

        meetings = tuple(self._meetings(section.id))
        if self._violates_meeting_constraints(
            section=section,
            meetings=meetings,
            excluded_days=excluded_days,
            unavailable_blocks=unavailable_blocks,
            earliest_start_time=earliest_start_time,
            latest_end_time=latest_end_time,
            conflicts=conflicts,
        ):
            return None

        eligibility = self._eligibility_engine.evaluate(
            student_profile_id=student.id,
            course_id=course.id,
            section_id=section.id,
            target_term_id=term.id,
            mode=EligibilityMode.REGISTRATION,
        )
        warning_codes: list[str] = []
        for warning in eligibility.warnings:
            if warning.warning_code == "NO_STORED_RESTRICTIONS":
                warning_codes.append("NO_STORED_RESTRICTIONS")
        if eligibility.overall_result is EligibilityOverallResult.NOT_ELIGIBLE:
            conflicts.append(
                ConflictDraft(
                    conflict_type=ScheduleConflictType.ELIGIBILITY_BLOCKED,
                    section_id=section.id,
                    message=(
                        f"{course.subject_code} {course.course_number} section "
                        f"{section.section_code} is blocked by academic eligibility."
                    ),
                )
            )
            return None
        if eligibility.overall_result is EligibilityOverallResult.PERMISSION_REQUIRED:
            if not allow_permission_required:
                warnings.append(
                    WarningDraft(
                        warning_code="PERMISSION_REQUIRED_BLOCKED",
                        severity=AuditWarningSeverity.WARNING,
                        message=(
                            f"{course.subject_code} {course.course_number} section "
                            f"{section.section_code} requires permission and was not selected."
                        ),
                        requires_advisor_confirmation=True,
                    )
                )
                conflicts.append(
                    ConflictDraft(
                        conflict_type=ScheduleConflictType.MANUAL_REVIEW_REQUIRED,
                        section_id=section.id,
                        message="Permission-required section was blocked by request settings.",
                    )
                )
                return None
            warning_codes.append("PERMISSION_REQUIRED")
        elif eligibility.overall_result is EligibilityOverallResult.MANUAL_REVIEW_REQUIRED:
            warnings.append(
                WarningDraft(
                    warning_code="MANUAL_REVIEW_REQUIRED",
                    severity=AuditWarningSeverity.WARNING,
                    message=(
                        f"{course.subject_code} {course.course_number} section "
                        f"{section.section_code} needs manual review and was not selected."
                    ),
                    requires_advisor_confirmation=True,
                )
            )
            conflicts.append(
                ConflictDraft(
                    conflict_type=ScheduleConflictType.MANUAL_REVIEW_REQUIRED,
                    section_id=section.id,
                    message="Manual-review eligibility cannot be selected as feasible.",
                )
            )
            return None
        elif eligibility.overall_result is EligibilityOverallResult.CONDITIONALLY_ELIGIBLE:
            warning_codes.append("ELIGIBILITY_CONDITIONAL")

        if section.status is SectionStatus.WAITLIST:
            warning_codes.append("SECTION_WAITLIST_SEPARATE_FROM_ELIGIBILITY")
        if (
            any(meeting.is_arranged for meeting in meetings)
            or section.modality is SectionModality.ARRANGED
        ):
            warning_codes.append("ARRANGED_MEETING_TIME_UNKNOWN")
        if section.modality is SectionModality.ONLINE_ASYNCHRONOUS or any(
            meeting.is_online and meeting.day_of_week is None for meeting in meetings
        ):
            warning_codes.append("ONLINE_ASYNC_TIMING_UNKNOWN")

        return SectionCandidate(
            section=section,
            course=course,
            meetings=meetings,
            eligibility=eligibility,
            credits=quantize_credits(section.credits or course.credits_min),
            selection_reason="SECTION_SATISFIES_HARD_CONSTRAINTS",
            warning_codes=tuple(dict.fromkeys(warning_codes)),
        )

    def _meetings(self, section_id: UUID) -> list[SectionMeeting]:
        return list(
            self._db.scalars(
                select(SectionMeeting)
                .where(SectionMeeting.section_id == section_id)
                .order_by(SectionMeeting.display_order, SectionMeeting.id)
            ).all()
        )

    def _violates_meeting_constraints(
        self,
        *,
        section: Section,
        meetings: tuple[SectionMeeting, ...],
        excluded_days: set[DayOfWeek],
        unavailable_blocks: list[UnavailableBlock],
        earliest_start_time: time | None,
        latest_end_time: time | None,
        conflicts: list[ConflictDraft],
    ) -> bool:
        violated = False
        for meeting in meetings:
            if self._is_floating_meeting(meeting):
                continue
            if meeting.day_of_week in excluded_days:
                conflicts.append(
                    ConflictDraft(
                        conflict_type=ScheduleConflictType.EXCLUDED_DAY,
                        section_id=section.id,
                        day_of_week=meeting.day_of_week,
                        start_time=meeting.start_time,
                        end_time=meeting.end_time,
                        message="Section meeting falls on an excluded day.",
                    )
                )
                violated = True
            if (
                earliest_start_time is not None
                and meeting.start_time is not None
                and meeting.start_time < earliest_start_time
            ):
                conflicts.append(
                    ConflictDraft(
                        conflict_type=ScheduleConflictType.UNAVAILABLE_TIME,
                        section_id=section.id,
                        day_of_week=meeting.day_of_week,
                        start_time=meeting.start_time,
                        end_time=meeting.end_time,
                        message="Section starts before the configured earliest start time.",
                    )
                )
                violated = True
            if (
                latest_end_time is not None
                and meeting.end_time is not None
                and meeting.end_time > latest_end_time
            ):
                conflicts.append(
                    ConflictDraft(
                        conflict_type=ScheduleConflictType.UNAVAILABLE_TIME,
                        section_id=section.id,
                        day_of_week=meeting.day_of_week,
                        start_time=meeting.start_time,
                        end_time=meeting.end_time,
                        message="Section ends after the configured latest end time.",
                    )
                )
                violated = True
            for block in unavailable_blocks:
                if (
                    meeting.day_of_week is block.day_of_week
                    and meeting.start_time is not None
                    and meeting.end_time is not None
                    and times_overlap(
                        meeting.start_time, meeting.end_time, block.start_time, block.end_time
                    )
                ):
                    conflicts.append(
                        ConflictDraft(
                            conflict_type=ScheduleConflictType.UNAVAILABLE_TIME,
                            section_id=section.id,
                            day_of_week=meeting.day_of_week,
                            start_time=max(meeting.start_time, block.start_time),
                            end_time=min(meeting.end_time, block.end_time),
                            message="Section overlaps a user unavailable time block.",
                        )
                    )
                    violated = True
        return violated

    def _add_no_section_warning(
        self,
        course: Course,
        warnings: list[WarningDraft],
        conflicts: list[ConflictDraft],
    ) -> None:
        warnings.append(
            WarningDraft(
                warning_code="NO_SECTION_AVAILABLE",
                severity=AuditWarningSeverity.WARNING,
                message=(
                    f"No selectable mock section is available for "
                    f"{course.subject_code} {course.course_number} in the target term."
                ),
                requires_advisor_confirmation=True,
            )
        )
        conflicts.append(
            ConflictDraft(
                conflict_type=ScheduleConflictType.NO_SECTION_AVAILABLE,
                message=(
                    f"No selectable section exists for "
                    f"{course.subject_code} {course.course_number}."
                ),
            )
        )

    def _section_sort_key(self, candidate: SectionCandidate) -> tuple[str, str, str]:
        first_meeting = min(
            (
                (
                    meeting.day_of_week.value if meeting.day_of_week else "ZZZ",
                    meeting.start_time.isoformat() if meeting.start_time else "99:99",
                )
                for meeting in candidate.meetings
            ),
            default=("ZZZ", "99:99"),
        )
        return (
            candidate.section.section_code,
            f"{first_meeting[0]}-{first_meeting[1]}",
            str(candidate.section.id),
        )

    def _build_options(
        self,
        *,
        candidates: list[CandidateCourse],
        section_groups: dict[UUID, list[SectionCandidate]],
        minimum_credits: Decimal,
        maximum_credits: Decimal,
        preferred_credits: Decimal,
        requested_option_count: int,
        prefer_online: bool,
        prefer_compact_schedule: bool,
        prefer_fewer_days: bool,
        prefer_in_person: bool,
        avoid_early_start: bool,
        avoid_late_end: bool,
        preference_weights: dict[str, Decimal],
        course_priority_weights: dict[UUID, Decimal],
        section_priority_weights: dict[UUID, Decimal],
        prefer_no_gaps: bool,
        prefer_morning: bool,
        prefer_afternoon: bool,
        diversity_mode: str,
        allow_partial_options: bool,
        max_combinations: int,
        warnings: list[WarningDraft],
    ) -> tuple[list[OptionDraft], list[ConflictDraft]]:
        groups = [
            section_groups[candidate.course.id]
            for candidate in candidates
            if candidate.course.id in section_groups
        ]
        conflicts: list[ConflictDraft] = []
        if not groups:
            return [], conflicts

        combinations: list[tuple[SectionCandidate, ...]] = []
        evaluated = 0

        def backtrack(index: int, selected: list[SectionCandidate]) -> None:
            nonlocal evaluated
            if evaluated >= max_combinations:
                return
            if index == len(groups):
                evaluated += 1
                combinations.append(tuple(selected))
                return
            for candidate in groups[index]:
                selected.append(candidate)
                backtrack(index + 1, selected)
                selected.pop()

        backtrack(0, [])
        if evaluated >= max_combinations:
            warnings.append(
                WarningDraft(
                    warning_code="SCHEDULE_SEARCH_LIMIT_REACHED",
                    severity=AuditWarningSeverity.WARNING,
                    message=(
                        "The bounded schedule search limit was reached; returned options are "
                        "deterministic but not exhaustive."
                    ),
                    requires_advisor_confirmation=True,
                )
            )

        drafts: list[OptionDraft] = []
        full_course_count = len(candidates)
        for combination in combinations:
            conflict = self._combination_conflict(combination)
            if conflict is not None:
                conflicts.append(conflict)
                continue
            total_credits = quantize_credits(sum((item.credits for item in combination), ZERO))
            if total_credits > maximum_credits:
                conflicts.append(
                    ConflictDraft(
                        conflict_type=ScheduleConflictType.CREDIT_LIMIT,
                        message=(
                            f"Combination has {total_credits} credits, above maximum "
                            f"{maximum_credits}."
                        ),
                    )
                )
                continue
            stats = self._schedule_stats(combination)
            option_warnings = self._option_warnings(combination)
            if len(combination) < full_course_count or total_credits < minimum_credits:
                status = ScheduleOptionStatus.PARTIAL
                if total_credits < minimum_credits:
                    option_warnings.append(
                        WarningDraft(
                            warning_code="MINIMUM_CREDITS_NOT_MET",
                            severity=AuditWarningSeverity.WARNING,
                            message=(
                                f"Option has {total_credits} credits, below requested minimum "
                                f"{minimum_credits}."
                            ),
                            requires_advisor_confirmation=False,
                        )
                    )
                if not allow_partial_options:
                    continue
            elif option_warnings:
                status = ScheduleOptionStatus.FEASIBLE_WITH_WARNINGS
            else:
                status = ScheduleOptionStatus.FEASIBLE
            if not allow_partial_options and status is ScheduleOptionStatus.PARTIAL:
                continue
            score_values = self._score(
                combination=combination,
                total_credits=total_credits,
                class_days_count=stats[0],
                earliest_start_time=stats[1],
                latest_end_time=stats[2],
                total_gap_minutes=stats[3],
                preferred_credits=preferred_credits,
                prefer_online=prefer_online,
                prefer_compact_schedule=prefer_compact_schedule,
                prefer_fewer_days=prefer_fewer_days,
                prefer_in_person=prefer_in_person,
                avoid_early_start=avoid_early_start,
                avoid_late_end=avoid_late_end,
                preference_weights=preference_weights,
                course_priority_weights=course_priority_weights,
                section_priority_weights=section_priority_weights,
                prefer_no_gaps=prefer_no_gaps,
                prefer_morning=prefer_morning,
                prefer_afternoon=prefer_afternoon,
            )
            drafts.append(
                OptionDraft(
                    selected_sections=combination,
                    status=status,
                    total_credits=total_credits,
                    class_days_count=stats[0],
                    earliest_start_time=stats[1],
                    latest_end_time=stats[2],
                    total_gap_minutes=stats[3],
                    score=score_values["total_score"],
                    credit_score=score_values["credit_score"],
                    compactness_score=score_values["compactness_score"],
                    days_score=score_values["days_score"],
                    gap_score=score_values["gap_score"],
                    modality_score=score_values["modality_score"],
                    time_preference_score=score_values["time_preference_score"],
                    priority_score=score_values["priority_score"],
                    penalty_score=score_values["penalty_score"],
                    score_explanation=score_values["score_explanation"],
                    explanation=score_values["explanation"],
                    warnings=option_warnings,
                )
            )
        drafts.sort(key=self._option_sort_key)
        return self._select_ranked_options(
            drafts, requested_option_count, diversity_mode
        ), conflicts

    def _combination_conflict(
        self,
        combination: tuple[SectionCandidate, ...],
    ) -> ConflictDraft | None:
        for index, left in enumerate(combination):
            for right in combination[index + 1 :]:
                for left_meeting in left.meetings:
                    if self._is_floating_meeting(left_meeting):
                        continue
                    for right_meeting in right.meetings:
                        if self._is_floating_meeting(right_meeting):
                            continue
                        if (
                            left_meeting.day_of_week is right_meeting.day_of_week
                            and left_meeting.start_time is not None
                            and left_meeting.end_time is not None
                            and right_meeting.start_time is not None
                            and right_meeting.end_time is not None
                            and times_overlap(
                                left_meeting.start_time,
                                left_meeting.end_time,
                                right_meeting.start_time,
                                right_meeting.end_time,
                            )
                        ):
                            return ConflictDraft(
                                conflict_type=ScheduleConflictType.TIME_OVERLAP,
                                section_id=left.section.id,
                                other_section_id=right.section.id,
                                day_of_week=left_meeting.day_of_week,
                                start_time=max(left_meeting.start_time, right_meeting.start_time),
                                end_time=min(left_meeting.end_time, right_meeting.end_time),
                                message=(
                                    f"{left.course.subject_code} {left.course.course_number} "
                                    f"{left.section.section_code} overlaps "
                                    f"{right.course.subject_code} {right.course.course_number} "
                                    f"{right.section.section_code}."
                                ),
                            )
        return None

    def _is_floating_meeting(self, meeting: SectionMeeting) -> bool:
        return (
            meeting.is_online
            or meeting.is_arranged
            or meeting.day_of_week is None
            or meeting.start_time is None
            or meeting.end_time is None
        )

    def _schedule_stats(
        self,
        combination: tuple[SectionCandidate, ...],
    ) -> tuple[int, time | None, time | None, int]:
        meetings_by_day: dict[DayOfWeek, list[tuple[time, time]]] = defaultdict(list)
        for selected in combination:
            for meeting in selected.meetings:
                if self._is_floating_meeting(meeting):
                    continue
                assert meeting.day_of_week is not None
                assert meeting.start_time is not None
                assert meeting.end_time is not None
                meetings_by_day[meeting.day_of_week].append((meeting.start_time, meeting.end_time))
        all_meetings = [meeting for meetings in meetings_by_day.values() for meeting in meetings]
        earliest = min((start for start, _ in all_meetings), default=None)
        latest = max((end for _, end in all_meetings), default=None)
        total_gap = 0
        for meetings in meetings_by_day.values():
            ordered = sorted(meetings)
            for index, (_start, end) in enumerate(ordered[:-1]):
                next_start = ordered[index + 1][0]
                gap = minutes_between(end, next_start)
                if gap > 0:
                    total_gap += gap
        return len(meetings_by_day), earliest, latest, total_gap

    def _option_warnings(
        self,
        combination: tuple[SectionCandidate, ...],
    ) -> list[WarningDraft]:
        warning_messages = {
            "NO_STORED_RESTRICTIONS": (
                "No stored restrictions were available for one selected mock course; "
                "this is not an official eligibility guarantee."
            ),
            "PERMISSION_REQUIRED": (
                "A selected section requires permission before registration can be confirmed."
            ),
            "ELIGIBILITY_CONDITIONAL": (
                "A selected section is conditionally eligible and needs confirmation."
            ),
            "SECTION_WAITLIST_SEPARATE_FROM_ELIGIBILITY": (
                "A selected section is waitlisted; seat availability is separate from "
                "academic eligibility."
            ),
            "ARRANGED_MEETING_TIME_UNKNOWN": (
                "A selected section has arranged timing that cannot be checked for conflicts."
            ),
            "ONLINE_ASYNC_TIMING_UNKNOWN": (
                "A selected online asynchronous section has no fixed meeting time."
            ),
        }
        drafts: list[WarningDraft] = []
        for selected in combination:
            for code in selected.warning_codes:
                drafts.append(
                    WarningDraft(
                        warning_code=code,
                        severity=AuditWarningSeverity.WARNING
                        if code != "ONLINE_ASYNC_TIMING_UNKNOWN"
                        else AuditWarningSeverity.INFO,
                        message=warning_messages[code],
                        requires_advisor_confirmation=code
                        not in {
                            "ONLINE_ASYNC_TIMING_UNKNOWN",
                            "SECTION_WAITLIST_SEPARATE_FROM_ELIGIBILITY",
                        },
                    )
                )
        return drafts

    def _score(
        self,
        *,
        combination: tuple[SectionCandidate, ...],
        total_credits: Decimal,
        class_days_count: int,
        earliest_start_time: time | None,
        latest_end_time: time | None,
        total_gap_minutes: int,
        preferred_credits: Decimal,
        prefer_online: bool,
        prefer_compact_schedule: bool,
        prefer_fewer_days: bool,
        prefer_in_person: bool,
        avoid_early_start: bool,
        avoid_late_end: bool,
        preference_weights: dict[str, Decimal],
        course_priority_weights: dict[UUID, Decimal],
        section_priority_weights: dict[UUID, Decimal],
        prefer_no_gaps: bool,
        prefer_morning: bool,
        prefer_afternoon: bool,
    ) -> ScoreValues:
        explanations: list[dict[str, str]] = []

        def weight(name: str) -> Decimal:
            return preference_weights.get(name, DEFAULT_PREFERENCE_WEIGHT)

        credit_score = max(
            ZERO,
            Decimal("30.00") - (abs(total_credits - preferred_credits) * Decimal("6.00")),
        ) * weight("credit")
        explanations.append(
            {
                "reason_code": "PREFERRED_CREDITS",
                "score": str(credit_score.quantize(Decimal("0.01"))),
                "explanation": (
                    f"{total_credits} credits compared with preferred {preferred_credits}."
                ),
            }
        )

        compactness_score = Decimal("0.00")
        if prefer_fewer_days:
            days_score = max(ZERO, Decimal("18.00") - Decimal(class_days_count * 3)) * weight(
                "days"
            )
        else:
            days_score = Decimal("0.00")
        if prefer_fewer_days:
            explanations.append(
                {
                    "reason_code": "FEWER_DAYS",
                    "score": str(days_score.quantize(Decimal("0.01"))),
                    "explanation": f"{class_days_count} class days in the option.",
                }
            )

        if prefer_compact_schedule:
            compactness_score = max(
                ZERO,
                Decimal("20.00") - (Decimal(total_gap_minutes) / Decimal("15")),
            ) * weight("compactness")
            explanations.append(
                {
                    "reason_code": "COMPACT_SCHEDULE",
                    "score": str(compactness_score.quantize(Decimal("0.01"))),
                    "explanation": f"{total_gap_minutes} total gap minutes.",
                }
            )

        gap_score = Decimal("0.00")
        if prefer_no_gaps:
            gap_score = max(
                ZERO,
                Decimal("15.00") - (Decimal(total_gap_minutes) / Decimal("10")),
            ) * weight("gap")
            explanations.append(
                {
                    "reason_code": "NO_GAPS",
                    "score": str(gap_score.quantize(Decimal("0.01"))),
                    "explanation": f"{total_gap_minutes} total gap minutes.",
                }
            )

        online_count = sum(
            1
            for selected in combination
            if selected.section.modality
            in {SectionModality.ONLINE_ASYNCHRONOUS, SectionModality.ONLINE_SYNCHRONOUS}
        )
        in_person_count = sum(
            1 for selected in combination if selected.section.modality is SectionModality.IN_PERSON
        )
        modality_score = Decimal("0.00")
        if prefer_online:
            modality_score += Decimal(online_count * 6)
            explanations.append(
                {
                    "reason_code": "PREFER_ONLINE",
                    "score": str(Decimal(online_count * 6).quantize(Decimal("0.01"))),
                    "explanation": f"{online_count} online sections selected.",
                }
            )
        if prefer_in_person:
            modality_score += Decimal(in_person_count * 4)
            explanations.append(
                {
                    "reason_code": "PREFER_IN_PERSON",
                    "score": str(Decimal(in_person_count * 4).quantize(Decimal("0.01"))),
                    "explanation": f"{in_person_count} in-person sections selected.",
                }
            )
        modality_score *= weight("modality")

        time_preference_score = Decimal("0.00")
        fixed_start_times: list[time] = []
        for selected in combination:
            for meeting in selected.meetings:
                if self._is_floating_meeting(meeting) or meeting.start_time is None:
                    continue
                fixed_start_times.append(meeting.start_time)
        if prefer_morning:
            morning_count = sum(1 for start_time in fixed_start_times if start_time < time(12, 0))
            morning_score = Decimal(morning_count * 3)
            time_preference_score += morning_score
            explanations.append(
                {
                    "reason_code": "PREFER_MORNING",
                    "score": str(morning_score.quantize(Decimal("0.01"))),
                    "explanation": f"{morning_count} fixed meetings start before noon.",
                }
            )
        if prefer_afternoon:
            afternoon_count = sum(
                1 for start_time in fixed_start_times if time(12, 0) <= start_time < time(17, 0)
            )
            afternoon_score = Decimal(afternoon_count * 3)
            time_preference_score += afternoon_score
            explanations.append(
                {
                    "reason_code": "PREFER_AFTERNOON",
                    "score": str(afternoon_score.quantize(Decimal("0.01"))),
                    "explanation": f"{afternoon_count} fixed meetings start in the afternoon.",
                }
            )
        time_preference_score *= weight("time")

        priority_score = Decimal("0.00")
        for selected in combination:
            course_weight = course_priority_weights.get(selected.course.id, ZERO)
            section_weight = section_priority_weights.get(selected.section.id, ZERO)
            if course_weight > ZERO:
                course_score = course_weight * Decimal("4.00")
                priority_score += course_score
                explanations.append(
                    {
                        "reason_code": "COURSE_PRIORITY_WEIGHT",
                        "score": str(course_score.quantize(Decimal("0.01"))),
                        "explanation": (
                            f"{selected.course.subject_code} {selected.course.course_number} "
                            "has a course priority weight."
                        ),
                    }
                )
            if section_weight > ZERO:
                section_score = section_weight * Decimal("4.00")
                priority_score += section_score
                explanations.append(
                    {
                        "reason_code": "SECTION_PRIORITY_WEIGHT",
                        "score": str(section_score.quantize(Decimal("0.01"))),
                        "explanation": (
                            f"{selected.course.subject_code} {selected.course.course_number} "
                            f"{selected.section.section_code} has a section priority weight."
                        ),
                    }
                )
        priority_score *= weight("priority")

        penalty_score = Decimal("0.00")
        if (
            avoid_early_start
            and earliest_start_time is not None
            and earliest_start_time < time(9, 0)
        ):
            penalty_score -= Decimal("5.00") * weight("time")
            explanations.append(
                {
                    "reason_code": "EARLY_START_PENALTY",
                    "score": str((-Decimal("5.00") * weight("time")).quantize(Decimal("0.01"))),
                    "explanation": "Earliest fixed meeting starts before 09:00.",
                }
            )
        if avoid_late_end and latest_end_time is not None and latest_end_time > time(17, 0):
            penalty_score -= Decimal("5.00") * weight("time")
            explanations.append(
                {
                    "reason_code": "LATE_END_PENALTY",
                    "score": str((-Decimal("5.00") * weight("time")).quantize(Decimal("0.01"))),
                    "explanation": "Latest fixed meeting ends after 17:00.",
                }
            )

        total_score = (
            credit_score
            + compactness_score
            + days_score
            + gap_score
            + modality_score
            + time_preference_score
            + priority_score
            + penalty_score
        )
        if total_score < ZERO:
            total_score = ZERO
        component_text = "; ".join(
            f"{item['reason_code']} {item['score']}" for item in explanations
        )
        return {
            "total_score": total_score.quantize(Decimal("0.01")),
            "credit_score": credit_score.quantize(Decimal("0.01")),
            "compactness_score": compactness_score.quantize(Decimal("0.01")),
            "days_score": days_score.quantize(Decimal("0.01")),
            "gap_score": gap_score.quantize(Decimal("0.01")),
            "modality_score": modality_score.quantize(Decimal("0.01")),
            "time_preference_score": time_preference_score.quantize(Decimal("0.01")),
            "priority_score": priority_score.quantize(Decimal("0.01")),
            "penalty_score": penalty_score.quantize(Decimal("0.01")),
            "score_explanation": explanations,
            "explanation": f"Score components: {component_text}",
        }

    def _option_sort_key(self, option: OptionDraft) -> tuple[int, Decimal, Decimal, str]:
        status_rank = {
            ScheduleOptionStatus.FEASIBLE: 0,
            ScheduleOptionStatus.FEASIBLE_WITH_WARNINGS: 1,
            ScheduleOptionStatus.PARTIAL: 2,
            ScheduleOptionStatus.INFEASIBLE: 3,
        }[option.status]
        section_key = "|".join(
            f"{selected.course.subject_code}{selected.course.course_number}-{selected.section.section_code}-{selected.section.id}"
            for selected in option.selected_sections
        )
        return (status_rank, -option.score, -option.total_credits, section_key)

    def _select_ranked_options(
        self,
        drafts: list[OptionDraft],
        requested_option_count: int,
        diversity_mode: str,
    ) -> list[OptionDraft]:
        remaining = list(drafts)
        selected: list[OptionDraft] = []
        while remaining and len(selected) < requested_option_count:
            if not selected or diversity_mode != "HIGH":
                next_option = remaining.pop(0)
            else:
                previous = selected[-1]
                best_index = min(
                    range(len(remaining)),
                    key=lambda index: (
                        self._shared_section_count(previous, remaining[index]),
                        self._option_sort_key(remaining[index]),
                    ),
                )
                next_option = remaining.pop(best_index)
            if selected:
                previous = selected[-1]
                next_option.shared_section_count_with_previous_option = self._shared_section_count(
                    previous, next_option
                )
                next_option.difference_summary = self._difference_summary(previous, next_option)
            else:
                next_option.shared_section_count_with_previous_option = 0
                next_option.difference_summary = "Top ranked option."
            next_option.diversity_rank = len(selected) + 1
            selected.append(next_option)
        return selected

    def _shared_section_count(self, left: OptionDraft, right: OptionDraft) -> int:
        left_ids = {selected.section.id for selected in left.selected_sections}
        right_ids = {selected.section.id for selected in right.selected_sections}
        return len(left_ids & right_ids)

    def _difference_summary(self, previous: OptionDraft, current: OptionDraft) -> str:
        previous_sections = {
            selected.course.id: selected for selected in previous.selected_sections
        }
        differences: list[str] = []
        for selected in current.selected_sections:
            previous_selected = previous_sections.get(selected.course.id)
            if previous_selected is None:
                differences.append(
                    f"adds {selected.course.subject_code} {selected.course.course_number}"
                )
                continue
            if previous_selected.section.id != selected.section.id:
                differences.append(
                    f"uses {selected.course.subject_code} {selected.course.course_number} "
                    f"section {selected.section.section_code} instead of "
                    f"{previous_selected.section.section_code}"
                )
            if previous_selected.section.modality is not selected.section.modality:
                differences.append(f"changes modality to {selected.section.modality.value}")
        if current.class_days_count != previous.class_days_count:
            differences.append(
                f"changes class days from {previous.class_days_count} to {current.class_days_count}"
            )
        return "; ".join(differences) if differences else "Similar section mix with score tie."

    def _repair_suggestions(
        self,
        *,
        conflicts: list[ConflictDraft],
        excluded_days: set[DayOfWeek],
        required_section_ids: set[UUID],
        minimum_credits: Decimal,
        maximum_credits: Decimal,
        allow_permission_required: bool,
    ) -> list[RepairSuggestionDraft]:
        suggestions: list[RepairSuggestionDraft] = []
        seen: set[tuple[str, str | None, UUID | None, UUID | None]] = set()

        def add(suggestion: RepairSuggestionDraft) -> None:
            key = (
                suggestion.suggestion_type,
                suggestion.affected_constraint,
                suggestion.affected_course_id,
                suggestion.affected_section_id,
            )
            if key not in seen:
                seen.add(key)
                suggestions.append(suggestion)

        for conflict in conflicts:
            if conflict.conflict_type is ScheduleConflictType.EXCLUDED_DAY:
                day = conflict.day_of_week.value if conflict.day_of_week else "excluded day"
                add(
                    RepairSuggestionDraft(
                        suggestion_type="RELAX_EXCLUDED_DAY",
                        affected_constraint="excluded_days",
                        affected_course_id=None,
                        affected_section_id=conflict.section_id,
                        estimated_impact="Could make a section on the excluded day selectable.",
                        message=f"Relax the {day} hard constraint for this mock schedule.",
                        requires_advisor_confirmation=True,
                    )
                )
            if (
                conflict.conflict_type is ScheduleConflictType.MANUAL_REVIEW_REQUIRED
                and not allow_permission_required
            ):
                add(
                    RepairSuggestionDraft(
                        suggestion_type="ALLOW_PERMISSION_REQUIRED",
                        affected_constraint="allow_permission_required",
                        affected_course_id=None,
                        affected_section_id=conflict.section_id,
                        estimated_impact="Could include permission-required advisory sections.",
                        message="Allow permission-required sections with advisor confirmation.",
                        requires_advisor_confirmation=True,
                    )
                )
            if conflict.conflict_type is ScheduleConflictType.CREDIT_LIMIT:
                add(
                    RepairSuggestionDraft(
                        suggestion_type="INCREASE_MAX_CREDITS",
                        affected_constraint="maximum_credits",
                        affected_course_id=None,
                        affected_section_id=None,
                        estimated_impact=f"Could allow loads above {maximum_credits} credits.",
                        message="Increase maximum credits if the load is realistic.",
                        requires_advisor_confirmation=True,
                    )
                )
            if conflict.conflict_type is ScheduleConflictType.UNAVAILABLE_TIME:
                add(
                    RepairSuggestionDraft(
                        suggestion_type="RELAX_UNAVAILABLE_BLOCK",
                        affected_constraint="unavailable_time_blocks",
                        affected_course_id=None,
                        affected_section_id=conflict.section_id,
                        estimated_impact="Could make a time-blocked section selectable.",
                        message="Relax or narrow the unavailable time block for this advisory run.",
                        requires_advisor_confirmation=False,
                    )
                )

        for section_id in sorted(required_section_ids, key=str):
            add(
                RepairSuggestionDraft(
                    suggestion_type="REMOVE_REQUIRED_SECTION",
                    affected_constraint="required_section_ids",
                    affected_course_id=None,
                    affected_section_id=section_id,
                    estimated_impact="Could let the optimizer choose another section.",
                    message="Remove the pinned section if it conflicts with hard rules.",
                    requires_advisor_confirmation=True,
                )
            )
        if minimum_credits > maximum_credits:
            add(
                RepairSuggestionDraft(
                    suggestion_type="RELAX_CREDIT_RANGE",
                    affected_constraint="minimum_credits",
                    affected_course_id=None,
                    affected_section_id=None,
                    estimated_impact="Could make the requested credit range internally consistent.",
                    message="Lower minimum credits or raise maximum credits.",
                    requires_advisor_confirmation=True,
                )
            )
        if excluded_days:
            for day in sorted(excluded_days, key=lambda value: value.value):
                add(
                    RepairSuggestionDraft(
                        suggestion_type="RELAX_EXCLUDED_DAY",
                        affected_constraint="excluded_days",
                        affected_course_id=None,
                        affected_section_id=None,
                        estimated_impact="Could expand the available section pool.",
                        message=f"Allow {day.value.title()} sections if no full schedule exists.",
                        requires_advisor_confirmation=False,
                    )
                )
        return suggestions

    def _persist_conflicts(self, run_id: UUID, conflicts: list[ConflictDraft]) -> None:
        for conflict in conflicts:
            self._db.add(
                ScheduleConflict(
                    id=uuid4(),
                    schedule_optimization_run_id=run_id,
                    schedule_option_id=conflict.option_id,
                    conflict_type=conflict.conflict_type,
                    section_id=conflict.section_id,
                    other_section_id=conflict.other_section_id,
                    day_of_week=conflict.day_of_week,
                    start_time=conflict.start_time,
                    end_time=conflict.end_time,
                    message=conflict.message,
                )
            )

    def _persist_options(self, run_id: UUID, options: list[OptionDraft]) -> int:
        warning_count = 0
        for rank, draft in enumerate(options, start=1):
            option = ScheduleOption(
                id=uuid4(),
                schedule_optimization_run_id=run_id,
                option_rank=rank,
                status=draft.status,
                total_credits=draft.total_credits,
                class_days_count=draft.class_days_count,
                earliest_start_time=draft.earliest_start_time,
                latest_end_time=draft.latest_end_time,
                total_gap_minutes=draft.total_gap_minutes,
                score=draft.score,
                total_score=draft.score,
                credit_score=draft.credit_score,
                compactness_score=draft.compactness_score,
                days_score=draft.days_score,
                gap_score=draft.gap_score,
                modality_score=draft.modality_score,
                time_preference_score=draft.time_preference_score,
                priority_score=draft.priority_score,
                penalty_score=draft.penalty_score,
                score_explanation=draft.score_explanation,
                diversity_rank=draft.diversity_rank,
                difference_summary=draft.difference_summary,
                shared_section_count_with_previous_option=(
                    draft.shared_section_count_with_previous_option
                ),
                explanation=draft.explanation,
            )
            self._db.add(option)
            self._db.flush()
            for selected in draft.selected_sections:
                self._db.add(
                    ScheduleOptionSection(
                        id=uuid4(),
                        schedule_option_id=option.id,
                        section_id=selected.section.id,
                        course_id=selected.course.id,
                        credits=selected.credits,
                        eligibility_result=selected.eligibility.overall_result,
                        selection_reason=selected.selection_reason,
                    )
                )
            for warning in draft.warnings:
                warning_count += 1
                self._db.add(
                    ScheduleWarning(
                        id=uuid4(),
                        schedule_optimization_run_id=run_id,
                        schedule_option_id=option.id,
                        warning_code=warning.warning_code,
                        severity=warning.severity,
                        message=warning.message,
                        requires_advisor_confirmation=warning.requires_advisor_confirmation,
                    )
                )
        return warning_count

    def _persist_warnings(self, run_id: UUID, warnings: list[WarningDraft]) -> None:
        for warning in warnings:
            self._db.add(
                ScheduleWarning(
                    id=uuid4(),
                    schedule_optimization_run_id=run_id,
                    schedule_option_id=warning.option_id,
                    warning_code=warning.warning_code,
                    severity=warning.severity,
                    message=warning.message,
                    requires_advisor_confirmation=warning.requires_advisor_confirmation,
                )
            )

    def _persist_repair_suggestions(
        self,
        run_id: UUID,
        suggestions: list[RepairSuggestionDraft],
    ) -> None:
        for suggestion in suggestions:
            self._db.add(
                ScheduleRepairSuggestion(
                    id=uuid4(),
                    schedule_optimization_run_id=run_id,
                    suggestion_type=suggestion.suggestion_type,
                    affected_constraint=suggestion.affected_constraint,
                    affected_course_id=suggestion.affected_course_id,
                    affected_section_id=suggestion.affected_section_id,
                    estimated_impact=suggestion.estimated_impact,
                    message=suggestion.message,
                    requires_advisor_confirmation=suggestion.requires_advisor_confirmation,
                )
            )


class BoundedSearchScheduleOptimizer:
    def __init__(self, service: ScheduleOptimizerApplicationService) -> None:
        self._service = service

    def generate_options(
        self,
        *,
        candidates: list[CandidateCourse],
        section_groups: dict[UUID, list[SectionCandidate]],
        minimum_credits: Decimal,
        maximum_credits: Decimal,
        preferred_credits: Decimal,
        requested_option_count: int,
        prefer_online: bool,
        prefer_compact_schedule: bool,
        prefer_fewer_days: bool,
        prefer_in_person: bool,
        avoid_early_start: bool,
        avoid_late_end: bool,
        preference_weights: dict[str, Decimal],
        course_priority_weights: dict[UUID, Decimal],
        section_priority_weights: dict[UUID, Decimal],
        prefer_no_gaps: bool,
        prefer_morning: bool,
        prefer_afternoon: bool,
        diversity_mode: str,
        allow_partial_options: bool,
        max_combinations: int,
        warnings: list[WarningDraft],
    ) -> tuple[list[OptionDraft], list[ConflictDraft]]:
        return self._service._build_options(
            candidates=candidates,
            section_groups=section_groups,
            minimum_credits=minimum_credits,
            maximum_credits=maximum_credits,
            preferred_credits=preferred_credits,
            requested_option_count=requested_option_count,
            prefer_online=prefer_online,
            prefer_compact_schedule=prefer_compact_schedule,
            prefer_fewer_days=prefer_fewer_days,
            prefer_in_person=prefer_in_person,
            avoid_early_start=avoid_early_start,
            avoid_late_end=avoid_late_end,
            preference_weights=preference_weights,
            course_priority_weights=course_priority_weights,
            section_priority_weights=section_priority_weights,
            prefer_no_gaps=prefer_no_gaps,
            prefer_morning=prefer_morning,
            prefer_afternoon=prefer_afternoon,
            diversity_mode=diversity_mode,
            allow_partial_options=allow_partial_options,
            max_combinations=max_combinations,
            warnings=warnings,
        )


def times_overlap(
    left_start: time,
    left_end: time,
    right_start: time,
    right_end: time,
) -> bool:
    return left_start < right_end and right_start < left_end


def minutes_between(start: time, end: time) -> int:
    return (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
