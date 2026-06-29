from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from decimal import Decimal
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

ENGINE_VERSION = "phase-6a-schedule-optimizer-v1"
ZERO = Decimal("0.0")
MAX_CANDIDATE_COURSES = 6
MAX_SECTIONS_PER_COURSE = 8
MAX_COMBINATIONS_EVALUATED = 500

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
    explanation: str
    warnings: list[WarningDraft] = field(default_factory=list)


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
    ) -> ScheduleOptimizationRun:
        self._validate_credit_inputs(
            minimum_credits=minimum_credits,
            maximum_credits=maximum_credits,
            preferred_credits=preferred_credits,
            requested_option_count=requested_option_count,
        )
        student = self._validate_student(student_profile_id)
        term = self._validate_term(term_id, student)
        academic_plan = self._validate_plan(
            academic_plan_run_id=academic_plan_run_id,
            student_profile_id=student_profile_id,
            term_id=term_id,
            planning_mode=planning_mode,
        )
        blocks = self._parse_unavailable_blocks(unavailable_time_blocks)

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
            options, optionless_conflicts = self._build_options(
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
                warnings=warnings,
            )
            conflicts.extend(optionless_conflicts)
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
                        explanation=(
                            "No sections could be selected under the hard constraints; "
                            "score is zero because no schedule exists."
                        ),
                    )
                ]
            self._persist_conflicts(run.id, conflicts)
            option_warning_count = self._persist_options(run.id, options)
            self._persist_warnings(run.id, warnings)
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
            if evaluated >= MAX_COMBINATIONS_EVALUATED:
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
        if evaluated >= MAX_COMBINATIONS_EVALUATED:
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
            elif option_warnings:
                status = ScheduleOptionStatus.FEASIBLE_WITH_WARNINGS
            else:
                status = ScheduleOptionStatus.FEASIBLE
            score, explanation = self._score(
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
                    score=score,
                    explanation=explanation,
                    warnings=option_warnings,
                )
            )
        drafts.sort(key=self._option_sort_key)
        return drafts[:requested_option_count], conflicts

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
    ) -> tuple[Decimal, str]:
        score = Decimal("100.00")
        components: list[str] = []
        credit_penalty = abs(total_credits - preferred_credits) * Decimal("3.0")
        score -= credit_penalty
        components.append(
            f"credits {total_credits} vs preferred {preferred_credits}: -{credit_penalty}"
        )
        if prefer_fewer_days:
            day_penalty = Decimal(class_days_count)
            score -= day_penalty
            components.append(f"class days {class_days_count}: -{day_penalty}")
        if prefer_compact_schedule:
            gap_penalty = Decimal(total_gap_minutes) / Decimal("30")
            score -= gap_penalty
            components.append(f"gap minutes {total_gap_minutes}: -{gap_penalty:.2f}")
        online_count = sum(
            1
            for selected in combination
            if selected.section.modality
            in {SectionModality.ONLINE_ASYNCHRONOUS, SectionModality.ONLINE_SYNCHRONOUS}
        )
        in_person_count = sum(
            1 for selected in combination if selected.section.modality is SectionModality.IN_PERSON
        )
        if prefer_online:
            bonus = Decimal(online_count * 4)
            score += bonus
            components.append(f"online sections {online_count}: +{bonus}")
        if prefer_in_person:
            bonus = Decimal(in_person_count * 2)
            score += bonus
            components.append(f"in-person sections {in_person_count}: +{bonus}")
        if (
            avoid_early_start
            and earliest_start_time is not None
            and earliest_start_time < time(9, 0)
        ):
            score -= Decimal("4.0")
            components.append("early start before 09:00: -4.0")
        if avoid_late_end and latest_end_time is not None and latest_end_time > time(17, 0):
            score -= Decimal("4.0")
            components.append("late end after 17:00: -4.0")
        if score < ZERO:
            score = ZERO
        return score.quantize(Decimal("0.01")), "Score components: " + "; ".join(components)

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


def times_overlap(
    left_start: time,
    left_end: time,
    right_start: time,
    right_end: time,
) -> bool:
    return left_start < right_end and right_start < left_end


def minutes_between(start: time, end: time) -> int:
    return (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
