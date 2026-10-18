from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import (
    AuditApplicationType,
    AuditMode,
    AuditRunStatus,
    AuditWarningSeverity,
    Course,
    CourseEquivalency,
    CourseSubstitution,
    CourseWaiver,
    ProgramVersion,
    RequirementCourseOption,
    RequirementEvaluationStatus,
    RequirementNode,
    RequirementType,
    SourceType,
    StudentCourseAttemptStatus,
    TransferCredit,
)
from app.services.course_state.engine import (
    active_course_state_snapshot,
    effective_student_course_attempts,
)
from app.services.degree_audit.allocator import AuditAllocator
from app.services.degree_audit.context import (
    ZERO,
    AuditContext,
    CourseCandidate,
    add_pending_record_warnings,
    build_attempts_by_course,
    build_children_by_parent,
    build_equivalencies_by_equivalent,
    build_options_by_node,
    build_substitutions_by_requirement,
    build_transfers_by_course,
    build_waivers_by_requirement,
)
from app.services.degree_audit.grade_policy import GradePolicy
from app.services.degree_audit.result import (
    AuditWarningResult,
    CourseApplicationResult,
    DegreeAuditResult,
    RequirementResult,
)
from app.services.reviewed_rules.resolution import (
    RuleResolutionState,
    resolve_for_program_version,
    reviewed_requirement_view,
)

DEGREE_AUDIT_ENGINE_VERSION = "phase-3a-degree-audit-v1"
ONE_HUNDRED = Decimal("100.00")

EvaluateNode = Callable[[RequirementNode], RequirementResult]


class RequirementEvaluator(Protocol):
    def evaluate(
        self,
        node: RequirementNode,
        context: AuditContext,
        evaluate_node: EvaluateNode,
        allocator: AuditAllocator,
    ) -> RequirementResult: ...


def quantize_credits(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.1"))


def quantize_percentage(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def application_from_candidate(
    node: RequirementNode,
    candidate: CourseCandidate,
    *,
    is_shared: bool,
) -> CourseApplicationResult:
    return CourseApplicationResult(
        requirement_node_id=node.id,
        course_id=candidate.course_id,
        student_course_attempt_id=candidate.student_course_attempt_id,
        transfer_credit_id=candidate.transfer_credit_id,
        course_waiver_id=candidate.course_waiver_id,
        course_substitution_id=candidate.course_substitution_id,
        application_type=candidate.application_type,
        credit_amount=quantize_credits(candidate.credits),
        grade=candidate.grade,
        is_completed=candidate.is_completed,
        is_in_progress=candidate.is_in_progress,
        is_planned=candidate.is_planned,
        is_shared=is_shared,
        explanation=candidate.explanation,
    )


def candidate_sort_key(candidate: CourseCandidate) -> tuple[int, int, str]:
    if candidate.is_completed:
        state_rank = 0
    elif candidate.is_in_progress:
        state_rank = 1
    elif candidate.is_planned:
        state_rank = 2
    else:
        state_rank = 3
    source_id = str(candidate.source_key[1])
    return (
        state_rank,
        0 if candidate.application_type is AuditApplicationType.WAIVER else 1,
        source_id,
    )


class BaseEvaluator:
    def manual_review(
        self,
        node: RequirementNode,
        message: str,
        *,
        warning_code: str = "REQUIREMENT_CONFIGURATION_INCOMPLETE",
    ) -> RequirementResult:
        warning = AuditWarningResult(
            warning_code=warning_code,
            severity=AuditWarningSeverity.WARNING,
            message=message,
            requires_advisor_confirmation=True,
            requirement_node_id=node.id,
        )
        return RequirementResult(
            requirement_node_id=node.id,
            requirement_code=node.code,
            requirement_name=node.name,
            requirement_type=node.requirement_type,
            status=RequirementEvaluationStatus.MANUAL_REVIEW_REQUIRED,
            required_credits=node.minimum_credits,
            satisfied_credits=ZERO,
            remaining_credits=quantize_credits(node.minimum_credits or ZERO),
            required_courses=node.minimum_courses or node.choose_n,
            satisfied_courses=0,
            remaining_courses=node.minimum_courses or node.choose_n or 0,
            minimum_grade=node.minimum_grade,
            explanation=message,
            display_order=node.display_order,
            warnings=[warning],
        )

    def result(
        self,
        node: RequirementNode,
        *,
        status: RequirementEvaluationStatus,
        required_credits: Decimal | None,
        satisfied_credits: Decimal,
        required_courses: int | None,
        satisfied_courses: int,
        explanation: str,
        applications: list[CourseApplicationResult] | None = None,
        warnings: list[AuditWarningResult] | None = None,
    ) -> RequirementResult:
        remaining_credits = max((required_credits or ZERO) - satisfied_credits, ZERO)
        remaining_courses = max((required_courses or 0) - satisfied_courses, 0)
        return RequirementResult(
            requirement_node_id=node.id,
            requirement_code=node.code,
            requirement_name=node.name,
            requirement_type=node.requirement_type,
            status=status,
            required_credits=quantize_credits(required_credits)
            if required_credits is not None
            else None,
            satisfied_credits=quantize_credits(satisfied_credits),
            remaining_credits=quantize_credits(remaining_credits),
            required_courses=required_courses,
            satisfied_courses=satisfied_courses,
            remaining_courses=remaining_courses,
            minimum_grade=node.minimum_grade,
            explanation=explanation,
            display_order=node.display_order,
            applications=applications or [],
            warnings=warnings or [],
        )


class RequiredCourseEvaluator(BaseEvaluator):
    def evaluate(
        self,
        node: RequirementNode,
        context: AuditContext,
        evaluate_node: EvaluateNode,
        allocator: AuditAllocator,
    ) -> RequirementResult:
        del evaluate_node
        waiver = first_available_candidate(
            context.waiver_candidates(node),
            allocator,
            allows_overlap=node.allows_overlap,
        )
        if waiver is not None:
            is_shared = allocator.reserve(waiver.source_key, allows_overlap=node.allows_overlap)
            return self.result(
                node,
                status=RequirementEvaluationStatus.WAIVED,
                required_credits=ZERO,
                satisfied_credits=ZERO,
                required_courses=1,
                satisfied_courses=1,
                explanation=(
                    "Approved waiver satisfies this requirement but adds no earned credits."
                ),
                applications=[application_from_candidate(node, waiver, is_shared=is_shared)],
            )

        options = context.options_by_node.get(node.id, [])
        if not options:
            return self.manual_review(
                node,
                f"{node.name} has no course options or approved waiver to evaluate.",
            )

        best_candidate: CourseCandidate | None = None
        required_credits = ZERO
        for option in options:
            course = context.courses_by_id[option.course_id]
            required_credits = option.credits_override or course.credits_min
            candidates = context.course_candidates(
                node,
                option.course_id,
                option.minimum_grade or node.minimum_grade,
            )
            candidate = first_available_candidate(
                candidates,
                allocator,
                allows_overlap=node.allows_overlap,
            )
            if candidate is not None:
                best_candidate = candidate
                break

        if best_candidate is None:
            return self.result(
                node,
                status=RequirementEvaluationStatus.NOT_SATISFIED,
                required_credits=required_credits,
                satisfied_credits=ZERO,
                required_courses=1,
                satisfied_courses=0,
                explanation=(
                    "No eligible completed, in-progress, planned, transfer, "
                    f"waiver, or substitution record satisfies {node.name}."
                ),
            )

        is_shared = allocator.reserve(best_candidate.source_key, allows_overlap=node.allows_overlap)
        status = leaf_status(best_candidate)
        satisfied_courses = 1 if best_candidate.is_completed else 0
        satisfied_credits = best_candidate.credits if best_candidate.is_completed else ZERO
        return self.result(
            node,
            status=status,
            required_credits=required_credits,
            satisfied_credits=satisfied_credits,
            required_courses=1,
            satisfied_courses=satisfied_courses,
            explanation=best_candidate.explanation,
            applications=[application_from_candidate(node, best_candidate, is_shared=is_shared)],
        )


class ChooseNEvaluator(BaseEvaluator):
    def evaluate(
        self,
        node: RequirementNode,
        context: AuditContext,
        evaluate_node: EvaluateNode,
        allocator: AuditAllocator,
    ) -> RequirementResult:
        del evaluate_node
        if node.choose_n is None or node.choose_n <= 0:
            return self.manual_review(node, f"{node.name} is missing a valid choose_n value.")

        candidates: list[CourseCandidate] = []
        candidates.extend(context.waiver_candidates(node))
        for option in context.options_by_node.get(node.id, []):
            candidates.extend(
                context.course_candidates(
                    node,
                    option.course_id,
                    option.minimum_grade or node.minimum_grade,
                )
            )

        selected: list[CourseCandidate] = []
        seen_courses: set[UUID] = set()
        for candidate in sorted(candidates, key=candidate_sort_key):
            if candidate.course_id is not None and candidate.course_id in seen_courses:
                continue
            if not allocator.is_available(candidate.source_key, allows_overlap=node.allows_overlap):
                continue
            selected.append(candidate)
            if candidate.course_id is not None:
                seen_courses.add(candidate.course_id)
            if len(selected) >= node.choose_n:
                break

        applications: list[CourseApplicationResult] = []
        for candidate in selected:
            is_shared = allocator.reserve(candidate.source_key, allows_overlap=node.allows_overlap)
            applications.append(application_from_candidate(node, candidate, is_shared=is_shared))

        completed_count = sum(1 for candidate in selected if candidate.is_completed)
        in_progress_count = sum(1 for candidate in selected if candidate.is_in_progress)
        planned_count = sum(1 for candidate in selected if candidate.is_planned)
        satisfied_credits = sum(
            (candidate.credits for candidate in selected if candidate.is_completed), ZERO
        )
        status = count_status(
            required=node.choose_n,
            completed=completed_count,
            in_progress=in_progress_count,
            planned=planned_count,
        )
        return self.result(
            node,
            status=status,
            required_credits=None,
            satisfied_credits=satisfied_credits,
            required_courses=node.choose_n,
            satisfied_courses=completed_count,
            explanation=choose_n_explanation(
                node, completed_count, in_progress_count, planned_count
            ),
            applications=applications,
        )


class MinimumCreditsEvaluator(BaseEvaluator):
    def evaluate(
        self,
        node: RequirementNode,
        context: AuditContext,
        evaluate_node: EvaluateNode,
        allocator: AuditAllocator,
    ) -> RequirementResult:
        del evaluate_node
        if node.minimum_credits is None:
            return self.manual_review(node, f"{node.name} is missing minimum credits.")
        return evaluate_credit_pool(
            self,
            node,
            context,
            allocator,
            required_credits=node.minimum_credits,
            reserve_sources=True,
            only_resident=False,
            minimum_course_level=node.minimum_course_level,
        )


class TotalCreditsEvaluator(BaseEvaluator):
    def evaluate(
        self,
        node: RequirementNode,
        context: AuditContext,
        evaluate_node: EvaluateNode,
        allocator: AuditAllocator,
    ) -> RequirementResult:
        del evaluate_node, allocator
        required_credits = node.minimum_credits or context.total_required_credits
        completed, in_progress, planned = context.credit_summary()
        status = credit_status(required_credits, completed, in_progress, planned)
        return self.result(
            node,
            status=status,
            required_credits=required_credits,
            satisfied_credits=completed,
            required_courses=None,
            satisfied_courses=0,
            explanation=(
                f"{completed} completed credits are counted toward "
                f"{required_credits} total required credits."
            ),
        )


class MinimumCoursesEvaluator(BaseEvaluator):
    def evaluate(
        self,
        node: RequirementNode,
        context: AuditContext,
        evaluate_node: EvaluateNode,
        allocator: AuditAllocator,
    ) -> RequirementResult:
        del evaluate_node
        if node.minimum_courses is None:
            return self.manual_review(node, f"{node.name} is missing minimum courses.")
        candidates = context.all_course_candidates(node, node.minimum_grade)
        selected = select_distinct_candidates(
            candidates, allocator, allows_overlap=node.allows_overlap
        )
        completed = sum(1 for candidate in selected if candidate.is_completed)
        in_progress = sum(1 for candidate in selected if candidate.is_in_progress)
        planned = sum(1 for candidate in selected if candidate.is_planned)
        applications = [
            application_from_candidate(
                node,
                candidate,
                is_shared=allocator.reserve(
                    candidate.source_key, allows_overlap=node.allows_overlap
                ),
            )
            for candidate in selected[: node.minimum_courses]
        ]
        return self.result(
            node,
            status=count_status(node.minimum_courses, completed, in_progress, planned),
            required_credits=None,
            satisfied_credits=sum(
                (candidate.credits for candidate in selected if candidate.is_completed),
                ZERO,
            ),
            required_courses=node.minimum_courses,
            satisfied_courses=min(completed, node.minimum_courses),
            explanation=f"{completed} distinct completed courses count toward {node.name}.",
            applications=applications,
        )


class CourseLevelEvaluator(BaseEvaluator):
    def evaluate(
        self,
        node: RequirementNode,
        context: AuditContext,
        evaluate_node: EvaluateNode,
        allocator: AuditAllocator,
    ) -> RequirementResult:
        del evaluate_node
        if node.minimum_course_level is None:
            return self.manual_review(node, f"{node.name} is missing a minimum course level.")
        required_credits = node.minimum_credits or ZERO
        return evaluate_credit_pool(
            self,
            node,
            context,
            allocator,
            required_credits=required_credits,
            reserve_sources=False,
            only_resident=False,
            minimum_course_level=node.minimum_course_level,
        )


class ResidencyEvaluator(BaseEvaluator):
    def evaluate(
        self,
        node: RequirementNode,
        context: AuditContext,
        evaluate_node: EvaluateNode,
        allocator: AuditAllocator,
    ) -> RequirementResult:
        del evaluate_node
        if node.minimum_residency_credits is None:
            return self.manual_review(node, f"{node.name} is missing residency credits.")
        return evaluate_credit_pool(
            self,
            node,
            context,
            allocator,
            required_credits=node.minimum_residency_credits,
            reserve_sources=False,
            only_resident=True,
            minimum_course_level=None,
        )


class AllOfEvaluator(BaseEvaluator):
    def evaluate(
        self,
        node: RequirementNode,
        context: AuditContext,
        evaluate_node: EvaluateNode,
        allocator: AuditAllocator,
    ) -> RequirementResult:
        del allocator
        children = [evaluate_node(child) for child in context.children_by_parent.get(node.id, [])]
        if not children:
            return self.manual_review(node, f"{node.name} has no child requirements.")
        status = all_of_status(children)
        return self.result(
            node,
            status=status,
            required_credits=sum_optional(child.required_credits for child in children),
            satisfied_credits=sum((child.satisfied_credits for child in children), ZERO),
            required_courses=sum_optional_int(child.required_courses for child in children),
            satisfied_courses=sum(child.satisfied_courses for child in children),
            explanation=parent_explanation(node, children),
            warnings=[warning for child in children for warning in child.warnings],
        )


class GroupEvaluator(AllOfEvaluator):
    pass


class AnyOfEvaluator(BaseEvaluator):
    def evaluate(
        self,
        node: RequirementNode,
        context: AuditContext,
        evaluate_node: EvaluateNode,
        allocator: AuditAllocator,
    ) -> RequirementResult:
        del allocator
        children = [evaluate_node(child) for child in context.children_by_parent.get(node.id, [])]
        if not children:
            return self.manual_review(node, f"{node.name} has no child requirements.")
        status = any_of_status(children)
        best = sorted(children, key=lambda child: (status_rank(child.status), child.display_order))[
            0
        ]
        return self.result(
            node,
            status=status,
            required_credits=best.required_credits,
            satisfied_credits=best.satisfied_credits,
            required_courses=best.required_courses,
            satisfied_courses=best.satisfied_courses,
            explanation=(
                f"{node.name} uses the best currently available child result: "
                f"{best.requirement_name}."
            ),
            warnings=[warning for child in children for warning in child.warnings],
        )


class ManualReviewEvaluator(BaseEvaluator):
    def evaluate(
        self,
        node: RequirementNode,
        context: AuditContext,
        evaluate_node: EvaluateNode,
        allocator: AuditAllocator,
    ) -> RequirementResult:
        del context, evaluate_node, allocator
        return self.manual_review(
            node,
            (
                f"{node.name} requires advisor confirmation because Phase 3A "
                "cannot determine its scope safely."
            ),
            warning_code="UNSUPPORTED_REQUIREMENT_SCOPE",
        )


class EvaluatorRegistry:
    def __init__(self) -> None:
        required_course = RequiredCourseEvaluator()
        manual_review = ManualReviewEvaluator()
        self._evaluators: dict[RequirementType, RequirementEvaluator] = {
            RequirementType.GROUP: GroupEvaluator(),
            RequirementType.ALL_OF: AllOfEvaluator(),
            RequirementType.ANY_OF: AnyOfEvaluator(),
            RequirementType.REQUIRED_COURSE: required_course,
            RequirementType.CAPSTONE: required_course,
            RequirementType.CHOOSE_N: ChooseNEvaluator(),
            RequirementType.MINIMUM_CREDITS: MinimumCreditsEvaluator(),
            RequirementType.MINIMUM_COURSES: MinimumCoursesEvaluator(),
            RequirementType.COURSE_LEVEL: CourseLevelEvaluator(),
            RequirementType.RESIDENCY: ResidencyEvaluator(),
            RequirementType.TOTAL_CREDITS: TotalCreditsEvaluator(),
            RequirementType.MINIMUM_GRADE: manual_review,
            RequirementType.EXCLUSION: manual_review,
        }

    def for_node(self, node: RequirementNode) -> RequirementEvaluator:
        return self._evaluators[node.requirement_type]


class DegreeAuditEngine:
    def __init__(self, db: Session, grade_policy: GradePolicy | None = None) -> None:
        self._db = db
        self._grade_policy = grade_policy or GradePolicy()
        self._registry = EvaluatorRegistry()

    def evaluate(
        self,
        student_profile_id: UUID,
        program_version_id: UUID,
        mode: AuditMode,
    ) -> DegreeAuditResult:
        context = self._load_context(student_profile_id, program_version_id, mode)
        allocator = AuditAllocator()
        evaluated: dict[UUID, RequirementResult] = {}

        def evaluate_node(node: RequirementNode) -> RequirementResult:
            existing = evaluated.get(node.id)
            if existing is not None:
                return existing
            result = self._registry.for_node(node).evaluate(node, context, evaluate_node, allocator)
            evaluated[node.id] = result
            return result

        for root in context.children_by_parent.get(None, []):
            evaluate_node(root)
        for node in context.nodes_by_id.values():
            evaluate_node(node)

        requirements = sorted(
            evaluated.values(),
            key=lambda result: (
                result.display_order,
                result.requirement_code,
                str(result.requirement_node_id),
            ),
        )
        completed, in_progress, planned = context.credit_summary()
        remaining = max(context.total_required_credits - completed, ZERO)
        percentage = (
            quantize_percentage((completed / context.total_required_credits) * ONE_HUNDRED)
            if context.total_required_credits > ZERO
            else ZERO
        )
        percentage = min(percentage, ONE_HUNDRED)
        warnings = context.warnings + [
            warning for requirement in requirements for warning in requirement.warnings
        ]
        return DegreeAuditResult(
            student_profile_id=student_profile_id,
            program_version_id=program_version_id,
            status=AuditRunStatus.COMPLETED_WITH_WARNINGS if warnings else AuditRunStatus.COMPLETED,
            engine_version=DEGREE_AUDIT_ENGINE_VERSION,
            calculation_mode=mode,
            total_required_credits=quantize_credits(context.total_required_credits),
            completed_credits=quantize_credits(completed),
            in_progress_credits=quantize_credits(in_progress),
            planned_credits=quantize_credits(planned),
            remaining_credits=quantize_credits(remaining),
            completion_percentage=percentage,
            source_snapshot_hash=context.source_snapshot_hash(),
            requirements=requirements,
            warnings=warnings,
            reviewed_rule_set_id=context.reviewed_rule_set_id,
            rule_resolution_state=context.rule_resolution_state,
            rule_source_reference=context.rule_source_reference,
            rule_catalog_year=context.rule_catalog_year,
            rule_resolution_explanation=context.rule_resolution_explanation,
        )

    def _load_context(
        self,
        student_profile_id: UUID,
        program_version_id: UUID,
        mode: AuditMode,
    ) -> AuditContext:
        program_version = self._db.get(ProgramVersion, program_version_id)
        if program_version is None:
            raise ValueError("ProgramVersion not found.")
        nodes = list(
            self._db.scalars(
                select(RequirementNode)
                .where(RequirementNode.program_version_id == program_version_id)
                .order_by(RequirementNode.display_order, RequirementNode.code)
            ).all()
        )
        options = list(
            self._db.scalars(
                select(RequirementCourseOption)
                .where(RequirementCourseOption.program_version_id == program_version_id)
                .order_by(RequirementCourseOption.display_order, RequirementCourseOption.id)
            ).all()
        )
        courses = list(
            self._db.scalars(
                select(Course).where(Course.institution_id == program_version.institution_id)
            ).all()
        )
        resolution = resolve_for_program_version(self._db, program_version_id)
        resolution_warnings: list[str] = []
        if resolution.state is RuleResolutionState.ACTIVE and resolution.rule_set is not None:
            nodes, options, resolution_warnings = reviewed_requirement_view(
                resolution.rule_set, nodes, options, courses
            )
        active_snapshot = active_course_state_snapshot(self._db, student_profile_id)
        attempts = effective_student_course_attempts(self._db, student_profile_id)
        transfer_statement = select(TransferCredit).where(
            TransferCredit.student_profile_id == student_profile_id
        )
        if active_snapshot is not None:
            transfer_statement = transfer_statement.where(
                TransferCredit.source_type != SourceType.MOCK
            )
        transfers = list(self._db.scalars(transfer_statement).all())
        waiver_statement = select(CourseWaiver).where(
            CourseWaiver.student_profile_id == student_profile_id,
            CourseWaiver.program_version_id == program_version_id,
        )
        if active_snapshot is not None:
            waiver_statement = waiver_statement.where(CourseWaiver.source_type != SourceType.MOCK)
        waivers = list(self._db.scalars(waiver_statement).all())
        substitution_statement = select(CourseSubstitution).where(
            CourseSubstitution.student_profile_id == student_profile_id,
            CourseSubstitution.program_version_id == program_version_id,
        )
        if active_snapshot is not None:
            substitution_statement = substitution_statement.where(
                CourseSubstitution.source_type != SourceType.MOCK
            )
        substitutions = list(self._db.scalars(substitution_statement).all())
        equivalencies = list(
            self._db.scalars(
                select(CourseEquivalency).where(
                    CourseEquivalency.institution_id == program_version.institution_id
                )
            ).all()
        )
        context = AuditContext(
            student_profile_id=student_profile_id,
            program_version_id=program_version_id,
            mode=mode,
            institution_id=program_version.institution_id,
            total_required_credits=program_version.total_credits_required,
            nodes_by_id={node.id: node for node in nodes},
            children_by_parent=build_children_by_parent(nodes),
            options_by_node=build_options_by_node(options),
            courses_by_id={course.id: course for course in courses},
            grade_policy=self._grade_policy,
            attempts_by_course=build_attempts_by_course(attempts),
            transfers_by_course=build_transfers_by_course(transfers),
            waivers_by_requirement=build_waivers_by_requirement(waivers),
            substitutions_by_requirement=build_substitutions_by_requirement(substitutions),
            equivalencies_by_equivalent=build_equivalencies_by_equivalent(equivalencies),
            reviewed_rule_set_id=(resolution.record.id if resolution.record is not None else None),
            rule_resolution_state=resolution.state.value,
            rule_source_reference=(
                resolution.rule_set.source.source_url_or_document_id
                if resolution.rule_set is not None
                else None
            ),
            rule_catalog_year=(
                resolution.rule_set.source.catalog_year if resolution.rule_set is not None else None
            ),
            rule_resolution_explanation=resolution.explanation,
        )
        for message in resolution_warnings:
            context.warnings.append(
                AuditWarningResult(
                    warning_code="REVIEWED_RULE_MAPPING_REQUIRES_REVIEW",
                    severity=AuditWarningSeverity.WARNING,
                    message=message,
                    requires_advisor_confirmation=True,
                )
            )
        if resolution.state is RuleResolutionState.CONFLICT:
            context.warnings.append(
                AuditWarningResult(
                    warning_code="REVIEWED_RULE_CONFLICT",
                    severity=AuditWarningSeverity.ERROR,
                    message=resolution.explanation,
                    requires_advisor_confirmation=True,
                )
            )
        add_pending_record_warnings(context, transfers, waivers, substitutions)
        if active_snapshot is not None:
            context.warnings.append(
                AuditWarningResult(
                    warning_code="ACTIVE_NON_OFFICIAL_COURSE_STATE_SNAPSHOT",
                    severity=AuditWarningSeverity.INFO,
                    message=(
                        "Degree audit uses reviewed non-official course-state snapshot "
                        f"{active_snapshot.id} from import {active_snapshot.data_import_run_id}; "
                        f"applied at {active_snapshot.applied_at.isoformat()}."
                    ),
                    requires_advisor_confirmation=True,
                )
            )
            if active_snapshot.extraction_bounded or active_snapshot.extraction_truncated:
                context.warnings.append(
                    AuditWarningResult(
                        warning_code="SOURCE_BOUNDED_OR_TRUNCATED",
                        severity=AuditWarningSeverity.WARNING,
                        message=(
                            "The active MyProgress source was bounded or truncated, so this "
                            "internal audit cannot claim complete requirement coverage."
                        ),
                        requires_advisor_confirmation=True,
                    )
                )
        for course_id, course_attempts in context.attempts_by_course.items():
            completed_attempts = [
                attempt
                for attempt in course_attempts
                if attempt.status is StudentCourseAttemptStatus.COMPLETED
            ]
            if len(completed_attempts) > 1:
                course = context.courses_by_id.get(course_id)
                course_label = (
                    f"{course.subject_code} {course.course_number}"
                    if course is not None
                    else str(course_id)
                )
                context.warnings.append(
                    AuditWarningResult(
                        warning_code="REPEAT_POLICY_AMBIGUITY",
                        severity=AuditWarningSeverity.WARNING,
                        message=(
                            f"Multiple completed attempts exist for {course_label}; Phase 3A "
                            "uses the best valid attempt and does not apply "
                            "school-specific grade replacement."
                        ),
                        requires_advisor_confirmation=True,
                    )
                )
        return context


def first_available_candidate(
    candidates: list[CourseCandidate],
    allocator: AuditAllocator,
    *,
    allows_overlap: bool,
) -> CourseCandidate | None:
    for candidate in sorted(candidates, key=candidate_sort_key):
        if allocator.is_available(candidate.source_key, allows_overlap=allows_overlap):
            return candidate
    return None


def leaf_status(candidate: CourseCandidate) -> RequirementEvaluationStatus:
    if candidate.application_type is AuditApplicationType.WAIVER:
        return RequirementEvaluationStatus.WAIVED
    if candidate.is_completed:
        return RequirementEvaluationStatus.SATISFIED
    if candidate.is_in_progress:
        return RequirementEvaluationStatus.IN_PROGRESS
    if candidate.is_planned:
        return RequirementEvaluationStatus.PLANNED
    return RequirementEvaluationStatus.NOT_SATISFIED


def count_status(
    required: int,
    completed: int,
    in_progress: int,
    planned: int,
) -> RequirementEvaluationStatus:
    if completed >= required:
        return RequirementEvaluationStatus.SATISFIED
    if completed + in_progress >= required:
        return RequirementEvaluationStatus.IN_PROGRESS
    if completed + in_progress + planned >= required:
        return RequirementEvaluationStatus.PLANNED
    if completed > 0 or in_progress > 0 or planned > 0:
        return RequirementEvaluationStatus.PARTIALLY_SATISFIED
    return RequirementEvaluationStatus.NOT_SATISFIED


def credit_status(
    required: Decimal,
    completed: Decimal,
    in_progress: Decimal,
    planned: Decimal,
) -> RequirementEvaluationStatus:
    if completed >= required:
        return RequirementEvaluationStatus.SATISFIED
    if completed + in_progress >= required:
        return RequirementEvaluationStatus.IN_PROGRESS
    if completed + in_progress + planned >= required:
        return RequirementEvaluationStatus.PLANNED
    if completed > ZERO or in_progress > ZERO or planned > ZERO:
        return RequirementEvaluationStatus.PARTIALLY_SATISFIED
    return RequirementEvaluationStatus.NOT_SATISFIED


def choose_n_explanation(
    node: RequirementNode,
    completed: int,
    in_progress: int,
    planned: int,
) -> str:
    return (
        f"{completed} of {node.choose_n or 0} required choices are completed; "
        f"{in_progress} are in progress and {planned} are planned."
    )


def evaluate_credit_pool(
    evaluator: BaseEvaluator,
    node: RequirementNode,
    context: AuditContext,
    allocator: AuditAllocator,
    *,
    required_credits: Decimal,
    reserve_sources: bool,
    only_resident: bool,
    minimum_course_level: int | None,
) -> RequirementResult:
    candidates = context.all_course_candidates(node, node.minimum_grade)
    if only_resident:
        candidates = [candidate for candidate in candidates if candidate.is_resident]
    if minimum_course_level is not None:
        candidates = [
            candidate
            for candidate in candidates
            if candidate.course_level is not None and candidate.course_level >= minimum_course_level
        ]
    selected = select_distinct_candidates(candidates, allocator, allows_overlap=True)
    completed = sum((candidate.credits for candidate in selected if candidate.is_completed), ZERO)
    in_progress = sum(
        (candidate.credits for candidate in selected if candidate.is_in_progress), ZERO
    )
    planned = sum((candidate.credits for candidate in selected if candidate.is_planned), ZERO)
    applications: list[CourseApplicationResult] = []
    applied_credits = ZERO
    for candidate in selected:
        if applied_credits >= required_credits:
            break
        if reserve_sources and not allocator.is_available(
            candidate.source_key, allows_overlap=node.allows_overlap
        ):
            continue
        is_shared = False
        if reserve_sources:
            is_shared = allocator.reserve(candidate.source_key, allows_overlap=node.allows_overlap)
        applications.append(application_from_candidate(node, candidate, is_shared=is_shared))
        if candidate.is_completed:
            applied_credits += candidate.credits

    return evaluator.result(
        node,
        status=credit_status(required_credits, completed, in_progress, planned),
        required_credits=required_credits,
        satisfied_credits=completed,
        required_courses=None,
        satisfied_courses=0,
        explanation=f"{completed} completed credits count toward {node.name}.",
        applications=applications,
    )


def select_distinct_candidates(
    candidates: list[CourseCandidate],
    allocator: AuditAllocator,
    *,
    allows_overlap: bool,
) -> list[CourseCandidate]:
    selected: list[CourseCandidate] = []
    seen_courses: set[UUID] = set()
    for candidate in sorted(candidates, key=candidate_sort_key):
        if candidate.course_id is not None and candidate.course_id in seen_courses:
            continue
        if not allocator.is_available(candidate.source_key, allows_overlap=allows_overlap):
            continue
        selected.append(candidate)
        if candidate.course_id is not None:
            seen_courses.add(candidate.course_id)
    return selected


def all_of_status(children: list[RequirementResult]) -> RequirementEvaluationStatus:
    statuses = {child.status for child in children}
    if RequirementEvaluationStatus.MANUAL_REVIEW_REQUIRED in statuses:
        return RequirementEvaluationStatus.MANUAL_REVIEW_REQUIRED
    satisfied_like = {
        RequirementEvaluationStatus.SATISFIED,
        RequirementEvaluationStatus.WAIVED,
        RequirementEvaluationStatus.NOT_APPLICABLE,
    }
    if statuses.issubset(satisfied_like):
        return RequirementEvaluationStatus.SATISFIED
    if RequirementEvaluationStatus.NOT_SATISFIED not in statuses:
        if RequirementEvaluationStatus.IN_PROGRESS in statuses:
            return RequirementEvaluationStatus.IN_PROGRESS
        if RequirementEvaluationStatus.PLANNED in statuses:
            return RequirementEvaluationStatus.PLANNED
    if statuses & {
        RequirementEvaluationStatus.SATISFIED,
        RequirementEvaluationStatus.WAIVED,
        RequirementEvaluationStatus.IN_PROGRESS,
        RequirementEvaluationStatus.PLANNED,
        RequirementEvaluationStatus.PARTIALLY_SATISFIED,
    }:
        return RequirementEvaluationStatus.PARTIALLY_SATISFIED
    return RequirementEvaluationStatus.NOT_SATISFIED


def any_of_status(children: list[RequirementResult]) -> RequirementEvaluationStatus:
    statuses = {child.status for child in children}
    if (
        RequirementEvaluationStatus.SATISFIED in statuses
        or RequirementEvaluationStatus.WAIVED in statuses
    ):
        return RequirementEvaluationStatus.SATISFIED
    if RequirementEvaluationStatus.IN_PROGRESS in statuses:
        return RequirementEvaluationStatus.IN_PROGRESS
    if RequirementEvaluationStatus.PLANNED in statuses:
        return RequirementEvaluationStatus.PLANNED
    if RequirementEvaluationStatus.PARTIALLY_SATISFIED in statuses:
        return RequirementEvaluationStatus.PARTIALLY_SATISFIED
    if RequirementEvaluationStatus.MANUAL_REVIEW_REQUIRED in statuses:
        return RequirementEvaluationStatus.MANUAL_REVIEW_REQUIRED
    return RequirementEvaluationStatus.NOT_SATISFIED


def status_rank(status: RequirementEvaluationStatus) -> int:
    ranks = {
        RequirementEvaluationStatus.SATISFIED: 0,
        RequirementEvaluationStatus.WAIVED: 1,
        RequirementEvaluationStatus.IN_PROGRESS: 2,
        RequirementEvaluationStatus.PLANNED: 3,
        RequirementEvaluationStatus.PARTIALLY_SATISFIED: 4,
        RequirementEvaluationStatus.NOT_SATISFIED: 5,
        RequirementEvaluationStatus.MANUAL_REVIEW_REQUIRED: 6,
        RequirementEvaluationStatus.NOT_APPLICABLE: 7,
    }
    return ranks[status]


def parent_explanation(node: RequirementNode, children: list[RequirementResult]) -> str:
    remaining = [
        child.requirement_name
        for child in children
        if child.status
        not in {
            RequirementEvaluationStatus.SATISFIED,
            RequirementEvaluationStatus.WAIVED,
            RequirementEvaluationStatus.NOT_APPLICABLE,
        }
    ]
    if not remaining:
        return f"All child requirements for {node.name} are satisfied or waived."
    return f"{node.name} still needs: {', '.join(remaining)}."


def sum_optional(values: Iterable[Decimal | None]) -> Decimal | None:
    total = ZERO
    saw_value = False
    for value in values:
        if isinstance(value, Decimal):
            total += value
            saw_value = True
    return total if saw_value else None


def sum_optional_int(values: Iterable[int | None]) -> int | None:
    total = 0
    saw_value = False
    for value in values:
        if isinstance(value, int):
            total += value
            saw_value = True
    return total if saw_value else None


def utc_now() -> datetime:
    return datetime.now(UTC)
