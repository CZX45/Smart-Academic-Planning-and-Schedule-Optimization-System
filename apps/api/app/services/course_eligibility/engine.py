from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models.academic import (
    AcademicProgram,
    AcademicTerm,
    ApprovalStatus,
    AuditWarningSeverity,
    Course,
    CourseRule,
    CourseRuleExpression,
    CourseRuleExpressionNodeType,
    CourseRuleType,
    EligibilityCheckRun,
    EligibilityCheckStatus,
    EligibilityMode,
    EligibilityOverallResult,
    EligibilityRuleResult,
    EligibilityWarning,
    ProgramType,
    ProgramVersion,
    RuleEvaluation,
    RuleExpressionEvaluation,
    Section,
    StudentAcademicProgram,
    StudentAcademicProgramStatus,
    StudentCourseAttempt,
    StudentCourseAttemptStatus,
    StudentProfile,
    TransferCredit,
)
from app.services.course_eligibility.exceptions import CourseEligibilityValidationError
from app.services.course_eligibility.result import (
    CorequisiteSummary,
    EligibilityReason,
    EligibilityResult,
    EligibilityWarningResult,
    ExpressionEvaluationResult,
    RegistrationAvailability,
    RuleEvaluationResult,
)
from app.services.course_state.engine import (
    active_course_state_snapshot,
    effective_student_course_attempts,
)
from app.services.degree_audit.grade_policy import GradePolicy
from app.services.reviewed_rules.eligibility import evaluate_reviewed_prerequisites
from app.services.reviewed_rules.resolution import resolve_for_student

ENGINE_VERSION = "phase-4-course-eligibility-v1"


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True)
class EligibilityRequestContext:
    student: StudentProfile
    course: Course
    target_term: AcademicTerm
    section: Section | None
    mode: EligibilityMode
    planned_corequisite_course_ids: frozenset[UUID]
    catalog_courses: list[Course]


@dataclass(frozen=True)
class AttemptMatch:
    result: EligibilityRuleResult
    reason_code: str
    explanation: str
    actual_value: str | None = None
    expected_value: str | None = None
    matched_course_id: UUID | None = None
    matched_attempt_id: UUID | None = None


LeafEvaluator = Callable[
    ["CourseEligibilityEngine", CourseRuleExpression, CourseRuleType, EligibilityRequestContext],
    AttemptMatch,
]


class EvaluatorRegistry:
    def __init__(self) -> None:
        self._evaluators: dict[CourseRuleExpressionNodeType, LeafEvaluator] = {}

    def register(
        self,
        node_type: CourseRuleExpressionNodeType,
    ) -> Callable[[LeafEvaluator], LeafEvaluator]:
        def decorator(evaluator: LeafEvaluator) -> LeafEvaluator:
            self._evaluators[node_type] = evaluator
            return evaluator

        return decorator

    def evaluate(
        self,
        engine: CourseEligibilityEngine,
        expression: CourseRuleExpression,
        rule_type: CourseRuleType,
        context: EligibilityRequestContext,
    ) -> AttemptMatch:
        evaluator = self._evaluators.get(expression.node_type)
        if evaluator is None:
            return AttemptMatch(
                result=EligibilityRuleResult.MANUAL_REVIEW_REQUIRED,
                reason_code="UNSUPPORTED_RULE_EXPRESSION",
                explanation=f"Expression node {expression.node_type.value} is not supported.",
            )
        return evaluator(engine, expression, rule_type, context)


registry = EvaluatorRegistry()


class CourseEligibilityEngine:
    def __init__(self, db: Session, grade_policy: GradePolicy | None = None) -> None:
        self._db = db
        self._grade_policy = grade_policy or GradePolicy()

    def evaluate(
        self,
        student_profile_id: UUID,
        course_id: UUID,
        section_id: UUID | None,
        target_term_id: UUID,
        mode: EligibilityMode,
        planned_corequisite_course_ids: list[UUID] | None = None,
    ) -> EligibilityResult:
        context = self._build_context(
            student_profile_id=student_profile_id,
            course_id=course_id,
            section_id=section_id,
            target_term_id=target_term_id,
            mode=mode,
            planned_corequisite_course_ids=planned_corequisite_course_ids or [],
        )
        reviewed_result = evaluate_reviewed_prerequisites(
            self._db,
            context,
            resolve_for_student(self._db, context.student.id),
        )
        if reviewed_result is not None:
            return reviewed_result
        active_snapshot = active_course_state_snapshot(self._db, context.student.id)
        rules = self._load_rules(context)
        if not rules:
            warning = EligibilityWarningResult(
                warning_code=(
                    "REAL_RESTRICTION_RULES_MISSING"
                    if active_snapshot is not None
                    else "NO_STORED_RESTRICTIONS"
                ),
                severity=AuditWarningSeverity.WARNING,
                message=(
                    "No reviewed prerequisite, corequisite, or restriction rules exist for this "
                    "real imported course-state scope."
                    if active_snapshot is not None
                    else "No stored prerequisite, corequisite, or restriction rules exist for "
                    "this mock course scope."
                ),
                requires_advisor_confirmation=True,
            )
            return EligibilityResult(
                overall_result=(
                    EligibilityOverallResult.MANUAL_REVIEW_REQUIRED
                    if active_snapshot is not None
                    else EligibilityOverallResult.ELIGIBLE
                ),
                academic_eligibility_result=(
                    EligibilityOverallResult.MANUAL_REVIEW_REQUIRED
                    if active_snapshot is not None
                    else EligibilityOverallResult.ELIGIBLE
                ),
                source_snapshot_hash=self._snapshot_hash(context, []),
                rule_evaluations=[],
                expression_evaluations=[],
                warnings=[warning],
                registration_availability=self._registration_availability(context.section),
            )

        roots, children_by_parent = self._load_expression_tree([rule.id for rule in rules])
        rule_results: list[RuleEvaluationResult] = []
        expression_results: list[ExpressionEvaluationResult] = []
        warnings: list[EligibilityWarningResult] = []
        for display_order, rule in enumerate(rules):
            root = roots.get(rule.id)
            if root is None:
                rule_result = RuleEvaluationResult(
                    course_rule_id=rule.id,
                    rule_type=rule.rule_type,
                    result=EligibilityRuleResult.MANUAL_REVIEW_REQUIRED,
                    explanation="The rule has no stored expression tree.",
                    display_order=display_order,
                )
                rule_results.append(rule_result)
                warnings.append(
                    EligibilityWarningResult(
                        warning_code="RULE_TREE_MISSING",
                        severity=AuditWarningSeverity.ERROR,
                        message=f"Rule {rule.name} has no expression tree.",
                        requires_advisor_confirmation=True,
                    )
                )
                continue

            expressions = self._evaluate_expression_tree(
                root,
                rule.rule_type,
                context,
                children_by_parent,
            )
            result = expressions[-1].result
            rule_results.append(
                RuleEvaluationResult(
                    course_rule_id=rule.id,
                    rule_type=rule.rule_type,
                    result=result,
                    explanation=self._rule_explanation(rule, result),
                    display_order=display_order,
                    expressions=expressions,
                )
            )
            expression_results.extend(expressions)
            if rule.requires_manual_confirmation:
                warnings.append(
                    EligibilityWarningResult(
                        warning_code="RULE_REQUIRES_MANUAL_CONFIRMATION",
                        severity=AuditWarningSeverity.WARNING,
                        message=(
                            f"Rule {rule.name} is mock data and requires advisor confirmation."
                        ),
                        requires_advisor_confirmation=True,
                    )
                )

        academic_result = self._aggregate_overall([rule.result for rule in rule_results])
        blocking, conditional, permission, manual = self._reasons_from_expressions(
            expression_results,
        )
        corequisite_summary = self._corequisite_summary(expression_results)
        warnings.append(
            EligibilityWarningResult(
                warning_code=(
                    "IMPORTED_COURSE_STATE_ADVISORY"
                    if active_snapshot is not None
                    else "MOCK_ELIGIBILITY_ESTIMATE"
                ),
                severity=AuditWarningSeverity.INFO,
                message=(
                    "This eligibility result uses reviewed non-official course-state evidence "
                    f"from import {active_snapshot.data_import_run_id} and does not replace "
                    "school or advisor confirmation."
                    if active_snapshot is not None
                    else "This eligibility result uses mock non-official rules and does not "
                    "replace school or advisor confirmation."
                ),
                requires_advisor_confirmation=True,
            )
        )
        return EligibilityResult(
            overall_result=academic_result,
            academic_eligibility_result=academic_result,
            source_snapshot_hash=self._snapshot_hash(context, rules),
            rule_evaluations=rule_results,
            expression_evaluations=expression_results,
            blocking_reasons=blocking,
            conditional_reasons=conditional,
            permissions_required=permission,
            manual_review_reasons=manual,
            corequisites_to_add=(
                [] if corequisite_summary is None else corequisite_summary.must_enroll_concurrently
            ),
            corequisite_summary=corequisite_summary,
            registration_availability=self._registration_availability(context.section),
            warnings=warnings,
        )

    def _build_context(
        self,
        *,
        student_profile_id: UUID,
        course_id: UUID,
        section_id: UUID | None,
        target_term_id: UUID,
        mode: EligibilityMode,
        planned_corequisite_course_ids: list[UUID],
    ) -> EligibilityRequestContext:
        student = self._db.get(StudentProfile, student_profile_id)
        if student is None:
            raise CourseEligibilityValidationError(
                "not_found", f"StudentProfile {student_profile_id} was not found."
            )
        course = self._db.get(Course, course_id)
        if course is None:
            raise CourseEligibilityValidationError(
                "not_found", f"Course {course_id} was not found."
            )
        term = self._db.get(AcademicTerm, target_term_id)
        if term is None:
            raise CourseEligibilityValidationError(
                "not_found", f"AcademicTerm {target_term_id} was not found."
            )
        if student.home_institution_id != course.institution_id:
            raise CourseEligibilityValidationError(
                "institution_scope_mismatch",
                "Student and Course must belong to the same institution.",
            )
        if term.institution_id != course.institution_id:
            raise CourseEligibilityValidationError(
                "institution_scope_mismatch",
                "Course and target term must belong to the same institution.",
            )
        section = self._db.get(Section, section_id) if section_id is not None else None
        if section_id is not None and section is None:
            raise CourseEligibilityValidationError(
                "not_found", f"Section {section_id} was not found."
            )
        if section is not None and section.course_id != course.id:
            raise CourseEligibilityValidationError(
                "section_course_mismatch",
                "Section must belong to the Course being checked.",
            )
        if section is not None and section.term_id != term.id:
            raise CourseEligibilityValidationError(
                "section_term_mismatch",
                "Section must belong to the target term being checked.",
            )
        return EligibilityRequestContext(
            student=student,
            course=course,
            target_term=term,
            section=section,
            mode=mode,
            planned_corequisite_course_ids=frozenset(planned_corequisite_course_ids),
            catalog_courses=list(
                self._db.scalars(
                    select(Course).where(Course.institution_id == course.institution_id)
                ).all()
            ),
        )

    def _load_rules(self, context: EligibilityRequestContext) -> list[CourseRule]:
        section_conditions: list[ColumnElement[bool]] = [CourseRule.section_id.is_(None)]
        if context.section is not None:
            section_conditions.append(CourseRule.section_id == context.section.id)
        return list(
            self._db.scalars(
                select(CourseRule)
                .where(
                    CourseRule.course_id == context.course.id,
                    CourseRule.institution_id == context.course.institution_id,
                    or_(*section_conditions),
                )
                .order_by(
                    CourseRule.section_id,
                    CourseRule.rule_type,
                    CourseRule.name,
                    CourseRule.id,
                )
            ).all()
        )

    def _load_expression_tree(
        self,
        rule_ids: list[UUID],
    ) -> tuple[dict[UUID, CourseRuleExpression], dict[UUID, list[CourseRuleExpression]]]:
        expressions = self._db.scalars(
            select(CourseRuleExpression)
            .where(CourseRuleExpression.course_rule_id.in_(rule_ids))
            .order_by(
                CourseRuleExpression.course_rule_id,
                CourseRuleExpression.display_order,
                CourseRuleExpression.node_type,
                CourseRuleExpression.id,
            )
        ).all()
        roots: dict[UUID, CourseRuleExpression] = {}
        children_by_parent: dict[UUID, list[CourseRuleExpression]] = defaultdict(list)
        for expression in expressions:
            if expression.parent_id is None:
                roots[expression.course_rule_id] = expression
            else:
                children_by_parent[expression.parent_id].append(expression)
        for children in children_by_parent.values():
            children.sort(key=lambda node: (node.display_order, node.node_type.value, str(node.id)))
        return roots, children_by_parent

    def _evaluate_expression_tree(
        self,
        expression: CourseRuleExpression,
        rule_type: CourseRuleType,
        context: EligibilityRequestContext,
        children_by_parent: dict[UUID, list[CourseRuleExpression]],
    ) -> list[ExpressionEvaluationResult]:
        child_results: list[ExpressionEvaluationResult] = []
        child_leaf_results: list[EligibilityRuleResult] = []
        for child in children_by_parent[expression.id]:
            evaluated_children = self._evaluate_expression_tree(
                child,
                rule_type,
                context,
                children_by_parent,
            )
            child_results.extend(evaluated_children)
            child_leaf_results.append(evaluated_children[-1].result)

        if expression.node_type in {
            CourseRuleExpressionNodeType.AND,
            CourseRuleExpressionNodeType.OR,
            CourseRuleExpressionNodeType.NOT,
        }:
            match = self._evaluate_operator(expression, child_leaf_results)
        else:
            match = registry.evaluate(self, expression, rule_type, context)

        return [
            *child_results,
            ExpressionEvaluationResult(
                course_rule_expression_id=expression.id,
                node_type=expression.node_type,
                result=match.result,
                reason_code=match.reason_code,
                explanation=match.explanation,
                display_order=expression.display_order,
                actual_value=match.actual_value,
                expected_value=match.expected_value,
                matched_course_id=match.matched_course_id,
                matched_attempt_id=match.matched_attempt_id,
            ),
        ]

    def _evaluate_operator(
        self,
        expression: CourseRuleExpression,
        child_results: list[EligibilityRuleResult],
    ) -> AttemptMatch:
        if expression.node_type is CourseRuleExpressionNodeType.AND:
            if not child_results:
                return AttemptMatch(
                    EligibilityRuleResult.MANUAL_REVIEW_REQUIRED,
                    "EMPTY_AND_EXPRESSION",
                    "AND expression has no child operands.",
                )
            return AttemptMatch(
                self._rollup_and(child_results),
                "AND_ROLLUP",
                "All child rules must be satisfied for this AND expression.",
            )
        if expression.node_type is CourseRuleExpressionNodeType.OR:
            if not child_results:
                return AttemptMatch(
                    EligibilityRuleResult.MANUAL_REVIEW_REQUIRED,
                    "EMPTY_OR_EXPRESSION",
                    "OR expression has no child operands.",
                )
            return AttemptMatch(
                self._rollup_or(child_results),
                "OR_ROLLUP",
                "At least one child rule must be satisfied for this OR expression.",
            )
        if len(child_results) != 1:
            return AttemptMatch(
                EligibilityRuleResult.MANUAL_REVIEW_REQUIRED,
                "INVALID_NOT_EXPRESSION",
                "NOT expression must have exactly one child operand.",
            )
        return AttemptMatch(
            self._rollup_not(child_results[0]),
            "NOT_ROLLUP",
            "The child rule result is inverted for this NOT expression.",
        )

    def _rollup_and(self, results: list[EligibilityRuleResult]) -> EligibilityRuleResult:
        if EligibilityRuleResult.NOT_SATISFIED in results:
            return EligibilityRuleResult.NOT_SATISFIED
        if EligibilityRuleResult.PERMISSION_REQUIRED in results:
            return EligibilityRuleResult.PERMISSION_REQUIRED
        if EligibilityRuleResult.CONDITIONALLY_SATISFIED in results:
            return EligibilityRuleResult.CONDITIONALLY_SATISFIED
        if EligibilityRuleResult.MANUAL_REVIEW_REQUIRED in results:
            return EligibilityRuleResult.MANUAL_REVIEW_REQUIRED
        return EligibilityRuleResult.SATISFIED

    def _rollup_or(self, results: list[EligibilityRuleResult]) -> EligibilityRuleResult:
        if EligibilityRuleResult.SATISFIED in results:
            return EligibilityRuleResult.SATISFIED
        if EligibilityRuleResult.CONDITIONALLY_SATISFIED in results:
            return EligibilityRuleResult.CONDITIONALLY_SATISFIED
        if EligibilityRuleResult.PERMISSION_REQUIRED in results:
            return EligibilityRuleResult.PERMISSION_REQUIRED
        if EligibilityRuleResult.MANUAL_REVIEW_REQUIRED in results:
            return EligibilityRuleResult.MANUAL_REVIEW_REQUIRED
        return EligibilityRuleResult.NOT_SATISFIED

    def _rollup_not(self, result: EligibilityRuleResult) -> EligibilityRuleResult:
        if result is EligibilityRuleResult.SATISFIED:
            return EligibilityRuleResult.NOT_SATISFIED
        if result is EligibilityRuleResult.NOT_SATISFIED:
            return EligibilityRuleResult.SATISFIED
        return EligibilityRuleResult.MANUAL_REVIEW_REQUIRED

    def _course_attempts(
        self,
        context: EligibilityRequestContext,
        course_id: UUID,
    ) -> list[StudentCourseAttempt]:
        return effective_student_course_attempts(
            self._db,
            context.student.id,
            course_id=course_id,
        )

    def _approved_transfer(
        self,
        context: EligibilityRequestContext,
        course_id: UUID,
    ) -> TransferCredit | None:
        return self._db.scalar(
            select(TransferCredit)
            .where(
                TransferCredit.student_profile_id == context.student.id,
                TransferCredit.equivalent_course_id == course_id,
                TransferCredit.status == ApprovalStatus.APPROVED,
            )
            .order_by(TransferCredit.id)
            .limit(1)
        )

    def evaluate_completed_course(
        self,
        expression: CourseRuleExpression,
        rule_type: CourseRuleType,
        context: EligibilityRequestContext,
    ) -> AttemptMatch:
        course_id = expression.referenced_course_id
        if course_id is None:
            return AttemptMatch(
                EligibilityRuleResult.MANUAL_REVIEW_REQUIRED,
                "COMPLETED_COURSE_OPERAND_MISSING",
                "Completed-course expression is missing a referenced course.",
            )

        attempts = self._course_attempts(context, course_id)
        for attempt in attempts:
            if attempt.status is not StudentCourseAttemptStatus.COMPLETED:
                continue
            grade_decision = self._grade_policy.satisfies_minimum(attempt.grade, None)
            if grade_decision.is_satisfied:
                if rule_type is CourseRuleType.COREQUISITE:
                    return AttemptMatch(
                        EligibilityRuleResult.SATISFIED,
                        "COREQUISITE_COMPLETED",
                        "Corequisite course has already been completed.",
                        actual_value=f"{attempt.status.value}:{attempt.grade or 'NO_GRADE'}",
                        expected_value="COMPLETED_OR_CONCURRENT_ENROLLMENT",
                        matched_course_id=course_id,
                        matched_attempt_id=attempt.id,
                    )
                return AttemptMatch(
                    EligibilityRuleResult.SATISFIED,
                    "COMPLETED_COURSE_SATISFIED",
                    "Required course has been completed.",
                    actual_value=f"{attempt.status.value}:{attempt.grade or 'NO_GRADE'}",
                    expected_value="COMPLETED",
                    matched_course_id=course_id,
                    matched_attempt_id=attempt.id,
                )

        approved_transfer = self._approved_transfer(context, course_id)
        if approved_transfer is not None:
            if rule_type is CourseRuleType.COREQUISITE:
                return AttemptMatch(
                    EligibilityRuleResult.SATISFIED,
                    "COREQUISITE_TRANSFER_SATISFIED",
                    "Corequisite course is satisfied by approved transfer credit.",
                    actual_value=f"APPROVED_TRANSFER:{approved_transfer.source_course_code}",
                    expected_value="COMPLETED_OR_CONCURRENT_ENROLLMENT",
                    matched_course_id=course_id,
                )
            return AttemptMatch(
                EligibilityRuleResult.SATISFIED,
                "COMPLETED_COURSE_TRANSFER_SATISFIED",
                "Required course is satisfied by approved transfer credit.",
                actual_value=f"APPROVED_TRANSFER:{approved_transfer.source_course_code}",
                expected_value="COMPLETED",
                matched_course_id=course_id,
            )

        for attempt in attempts:
            is_legacy_or_demo = attempt.course_state_snapshot_id is None
            may_be_conditional = (
                attempt.status is StudentCourseAttemptStatus.IN_PROGRESS
                and (is_legacy_or_demo or rule_type is CourseRuleType.COREQUISITE)
            ) or (attempt.status is StudentCourseAttemptStatus.PLANNED and is_legacy_or_demo)
            if may_be_conditional and context.mode in {
                EligibilityMode.PROJECTED,
                EligibilityMode.REGISTRATION,
            }:
                if rule_type is CourseRuleType.COREQUISITE:
                    if attempt.status is StudentCourseAttemptStatus.IN_PROGRESS:
                        return AttemptMatch(
                            EligibilityRuleResult.CONDITIONALLY_SATISFIED,
                            "COREQUISITE_IN_PROGRESS",
                            "Corequisite course is already in progress.",
                            actual_value=attempt.status.value,
                            expected_value="CONCURRENT_ENROLLMENT",
                            matched_course_id=course_id,
                            matched_attempt_id=attempt.id,
                        )
                    return AttemptMatch(
                        EligibilityRuleResult.CONDITIONALLY_SATISFIED,
                        "COREQUISITE_CONCURRENT_PLAN",
                        "Corequisite is already planned for concurrent enrollment.",
                        actual_value=attempt.status.value,
                        expected_value="CONCURRENT_ENROLLMENT",
                        matched_course_id=course_id,
                        matched_attempt_id=attempt.id,
                    )
                return AttemptMatch(
                    EligibilityRuleResult.CONDITIONALLY_SATISFIED,
                    "COMPLETED_COURSE_IN_PROGRESS",
                    "Required course is in progress or planned, so eligibility is conditional.",
                    actual_value=attempt.status.value,
                    expected_value="COMPLETED",
                    matched_course_id=course_id,
                    matched_attempt_id=attempt.id,
                )

        if rule_type is CourseRuleType.COREQUISITE and context.mode in {
            EligibilityMode.PROJECTED,
            EligibilityMode.REGISTRATION,
        }:
            if course_id in context.planned_corequisite_course_ids:
                return AttemptMatch(
                    EligibilityRuleResult.CONDITIONALLY_SATISFIED,
                    "COREQUISITE_CONCURRENT_PLAN",
                    "Corequisite is explicitly planned for concurrent enrollment.",
                    actual_value="PLANNED_CONCURRENTLY",
                    expected_value="CONCURRENT_ENROLLMENT",
                    matched_course_id=course_id,
                )
            return AttemptMatch(
                EligibilityRuleResult.CONDITIONALLY_SATISFIED,
                "COREQUISITE_MUST_ENROLL",
                "Corequisite must be added for concurrent enrollment.",
                actual_value="NOT_COMPLETED",
                expected_value="CONCURRENT_ENROLLMENT",
                matched_course_id=course_id,
            )

        return AttemptMatch(
            EligibilityRuleResult.NOT_SATISFIED,
            "COMPLETED_COURSE_MISSING",
            "Required course has not been completed.",
            actual_value="NOT_COMPLETED",
            expected_value="COMPLETED",
            matched_course_id=course_id,
        )

    def evaluate_minimum_grade(
        self,
        expression: CourseRuleExpression,
        rule_type: CourseRuleType,
        context: EligibilityRequestContext,
    ) -> AttemptMatch:
        course_id = expression.referenced_course_id
        if course_id is None or expression.minimum_grade is None:
            return AttemptMatch(
                EligibilityRuleResult.MANUAL_REVIEW_REQUIRED,
                "MINIMUM_GRADE_OPERAND_MISSING",
                "Minimum-grade expression is missing a referenced course or grade.",
            )
        expected = expression.minimum_grade
        attempts = self._course_attempts(context, course_id)
        completed_attempts = [
            attempt
            for attempt in attempts
            if attempt.status is StudentCourseAttemptStatus.COMPLETED
            and self._grade_policy.satisfies_minimum(attempt.grade, None).is_satisfied
        ]
        best_attempt = min(
            completed_attempts,
            key=lambda attempt: self._grade_policy.best_grade_key(attempt.grade),
            default=None,
        )
        if best_attempt is not None:
            grade_decision = self._grade_policy.satisfies_minimum(best_attempt.grade, expected)
            if grade_decision.is_satisfied:
                return AttemptMatch(
                    EligibilityRuleResult.SATISFIED,
                    "MINIMUM_GRADE_SATISFIED",
                    "Minimum grade requirement is satisfied by a completed attempt.",
                    actual_value=best_attempt.grade,
                    expected_value=expected,
                    matched_course_id=course_id,
                    matched_attempt_id=best_attempt.id,
                )
            if grade_decision.warning_code is not None:
                return AttemptMatch(
                    EligibilityRuleResult.MANUAL_REVIEW_REQUIRED,
                    grade_decision.warning_code,
                    grade_decision.message or "Minimum grade requires manual review.",
                    actual_value=best_attempt.grade,
                    expected_value=expected,
                    matched_course_id=course_id,
                    matched_attempt_id=best_attempt.id,
                )
            return AttemptMatch(
                EligibilityRuleResult.NOT_SATISFIED,
                "MINIMUM_GRADE_TOO_LOW",
                "Completed attempt does not meet the minimum grade.",
                actual_value=best_attempt.grade,
                expected_value=expected,
                matched_course_id=course_id,
                matched_attempt_id=best_attempt.id,
            )

        for attempt in attempts:
            is_legacy_or_demo = attempt.course_state_snapshot_id is None
            may_be_conditional = (
                attempt.status is StudentCourseAttemptStatus.IN_PROGRESS
                and (is_legacy_or_demo or rule_type is CourseRuleType.COREQUISITE)
            ) or (attempt.status is StudentCourseAttemptStatus.PLANNED and is_legacy_or_demo)
            if may_be_conditional and context.mode in {
                EligibilityMode.PROJECTED,
                EligibilityMode.REGISTRATION,
            }:
                return AttemptMatch(
                    EligibilityRuleResult.CONDITIONALLY_SATISFIED,
                    "MINIMUM_GRADE_PENDING",
                    "Course is in progress or planned; the final grade is not available yet.",
                    actual_value=attempt.status.value,
                    expected_value=expected,
                    matched_course_id=course_id,
                    matched_attempt_id=attempt.id,
                )
        return AttemptMatch(
            EligibilityRuleResult.NOT_SATISFIED,
            "MINIMUM_GRADE_MISSING",
            "No completed attempt can satisfy the minimum grade.",
            actual_value="NO_COMPLETED_ATTEMPT",
            expected_value=expected,
            matched_course_id=course_id,
        )

    def evaluate_minimum_completed_credits(
        self,
        expression: CourseRuleExpression,
        _rule_type: CourseRuleType,
        context: EligibilityRequestContext,
    ) -> AttemptMatch:
        required = expression.minimum_completed_credits
        if required is None:
            return AttemptMatch(
                EligibilityRuleResult.MANUAL_REVIEW_REQUIRED,
                "MINIMUM_CREDITS_OPERAND_MISSING",
                "Minimum completed credits expression is missing a credit threshold.",
            )
        earned = Decimal("0.0")
        potential = Decimal("0.0")
        seen_courses: set[UUID] = set()
        attempts = effective_student_course_attempts(self._db, context.student.id)
        for attempt in attempts:
            if (
                attempt.status is StudentCourseAttemptStatus.COMPLETED
                and attempt.course_id not in seen_courses
            ):
                earned += attempt.credits_earned
                seen_courses.add(attempt.course_id)
            elif attempt.course_state_snapshot_id is None and attempt.status in {
                StudentCourseAttemptStatus.IN_PROGRESS,
                StudentCourseAttemptStatus.PLANNED,
            }:
                potential += attempt.credits_attempted
        transfers = self._db.scalars(
            select(TransferCredit).where(
                TransferCredit.student_profile_id == context.student.id,
                TransferCredit.status == ApprovalStatus.APPROVED,
            )
        ).all()
        for transfer in transfers:
            if (
                transfer.equivalent_course_id is None
                or transfer.equivalent_course_id not in seen_courses
            ):
                earned += transfer.credits_earned
                if transfer.equivalent_course_id is not None:
                    seen_courses.add(transfer.equivalent_course_id)
        if earned >= required:
            return AttemptMatch(
                EligibilityRuleResult.SATISFIED,
                "MINIMUM_CREDITS_SATISFIED",
                "Minimum completed credits threshold is satisfied.",
                actual_value=str(earned),
                expected_value=str(required),
            )
        if (
            context.mode in {EligibilityMode.PROJECTED, EligibilityMode.REGISTRATION}
            and earned + potential >= required
        ):
            return AttemptMatch(
                EligibilityRuleResult.CONDITIONALLY_SATISFIED,
                "MINIMUM_CREDITS_PROJECTED",
                "Completed plus in-progress/planned credits may satisfy the threshold.",
                actual_value=str(earned + potential),
                expected_value=str(required),
            )
        return AttemptMatch(
            EligibilityRuleResult.NOT_SATISFIED,
            "MINIMUM_CREDITS_MISSING",
            "Completed credits do not satisfy the threshold.",
            actual_value=str(earned),
            expected_value=str(required),
        )

    def evaluate_class_standing(
        self,
        expression: CourseRuleExpression,
        _rule_type: CourseRuleType,
        context: EligibilityRequestContext,
    ) -> AttemptMatch:
        expected = expression.class_standing
        actual = context.student.class_standing
        if expected is None or actual is None:
            return AttemptMatch(
                EligibilityRuleResult.MANUAL_REVIEW_REQUIRED,
                "CLASS_STANDING_UNAVAILABLE",
                "Class standing is unavailable or not configured.",
                actual_value=actual,
                expected_value=expected,
            )
        standings = {"FRESHMAN": 1, "SOPHOMORE": 2, "JUNIOR": 3, "SENIOR": 4, "GRADUATE": 5}
        actual_rank = standings.get(actual.upper())
        expected_rank = standings.get(expected.upper())
        if actual_rank is None or expected_rank is None:
            return AttemptMatch(
                EligibilityRuleResult.MANUAL_REVIEW_REQUIRED,
                "CLASS_STANDING_UNKNOWN",
                "Class standing uses an unknown value.",
                actual_value=actual,
                expected_value=expected,
            )
        if actual_rank >= expected_rank:
            return AttemptMatch(
                EligibilityRuleResult.SATISFIED,
                "CLASS_STANDING_SATISFIED",
                "Class standing satisfies the restriction.",
                actual_value=actual,
                expected_value=expected,
            )
        return AttemptMatch(
            EligibilityRuleResult.NOT_SATISFIED,
            "CLASS_STANDING_TOO_LOW",
            "Class standing does not satisfy the restriction.",
            actual_value=actual,
            expected_value=expected,
        )

    def evaluate_program_restriction(
        self,
        expression: CourseRuleExpression,
        rule_type: CourseRuleType,
        context: EligibilityRequestContext,
    ) -> AttemptMatch:
        program_id = expression.referenced_program_id
        if program_id is None:
            return AttemptMatch(
                EligibilityRuleResult.MANUAL_REVIEW_REQUIRED,
                "PROGRAM_RESTRICTION_OPERAND_MISSING",
                "Program restriction is missing a referenced program.",
            )
        rows = self._db.execute(
            select(StudentAcademicProgram, ProgramVersion, AcademicProgram)
            .join(ProgramVersion, StudentAcademicProgram.program_version_id == ProgramVersion.id)
            .join(AcademicProgram, ProgramVersion.program_id == AcademicProgram.id)
            .where(
                StudentAcademicProgram.student_profile_id == context.student.id,
                StudentAcademicProgram.status == StudentAcademicProgramStatus.ACTIVE,
            )
        ).all()
        expected_type = None
        if expression.node_type is CourseRuleExpressionNodeType.MAJOR_RESTRICTION:
            expected_type = ProgramType.MAJOR
        elif expression.node_type is CourseRuleExpressionNodeType.MINOR_RESTRICTION:
            expected_type = ProgramType.MINOR
        for student_program, _version, program in rows:
            if program.id != program_id:
                continue
            if expected_type is not None and program.program_type is not expected_type:
                continue
            if rule_type is CourseRuleType.REGISTRATION_RESTRICTION:
                return AttemptMatch(
                    EligibilityRuleResult.SATISFIED,
                    "PROGRAM_RESTRICTION_SATISFIED",
                    "Student has an active matching program.",
                    actual_value=student_program.program_type.value,
                    expected_value=str(program_id),
                    matched_course_id=context.course.id,
                )
        return AttemptMatch(
            EligibilityRuleResult.NOT_SATISFIED,
            "PROGRAM_RESTRICTION_NOT_MET",
            "Student does not have an active matching program.",
            actual_value="NO_MATCHING_ACTIVE_PROGRAM",
            expected_value=str(program_id),
        )

    def evaluate_campus_restriction(
        self,
        expression: CourseRuleExpression,
        _rule_type: CourseRuleType,
        context: EligibilityRequestContext,
    ) -> AttemptMatch:
        expected = expression.referenced_campus_id
        actual = context.student.home_campus_id
        if expected is None:
            return AttemptMatch(
                EligibilityRuleResult.MANUAL_REVIEW_REQUIRED,
                "CAMPUS_RESTRICTION_OPERAND_MISSING",
                "Campus restriction is missing a referenced campus.",
            )
        if actual == expected:
            return AttemptMatch(
                EligibilityRuleResult.SATISFIED,
                "CAMPUS_RESTRICTION_SATISFIED",
                "Student home campus satisfies the restriction.",
                actual_value=str(actual),
                expected_value=str(expected),
            )
        return AttemptMatch(
            EligibilityRuleResult.MANUAL_REVIEW_REQUIRED,
            "CAMPUS_RESTRICTION_REVIEW",
            "Campus restrictions require advisor confirmation in Phase 4.",
            actual_value=str(actual),
            expected_value=str(expected),
        )

    def evaluate_permission_required(
        self,
        expression: CourseRuleExpression,
        _rule_type: CourseRuleType,
        _context: EligibilityRequestContext,
    ) -> AttemptMatch:
        return AttemptMatch(
            EligibilityRuleResult.PERMISSION_REQUIRED,
            "PERMISSION_REQUIRED",
            "Permission is required before registration eligibility can be confirmed.",
            actual_value=None,
            expected_value=expression.permission_type or "PERMISSION",
        )

    def _aggregate_overall(
        self,
        rule_results: list[EligibilityRuleResult],
    ) -> EligibilityOverallResult:
        if EligibilityRuleResult.NOT_SATISFIED in rule_results:
            return EligibilityOverallResult.NOT_ELIGIBLE
        if EligibilityRuleResult.PERMISSION_REQUIRED in rule_results:
            return EligibilityOverallResult.PERMISSION_REQUIRED
        if EligibilityRuleResult.CONDITIONALLY_SATISFIED in rule_results:
            return EligibilityOverallResult.CONDITIONALLY_ELIGIBLE
        if EligibilityRuleResult.MANUAL_REVIEW_REQUIRED in rule_results:
            return EligibilityOverallResult.MANUAL_REVIEW_REQUIRED
        return EligibilityOverallResult.ELIGIBLE

    def _rule_explanation(self, rule: CourseRule, result: EligibilityRuleResult) -> str:
        return f"{rule.rule_type.value} rule {rule.name} evaluated as {result.value}."

    def _reasons_from_expressions(
        self,
        expressions: list[ExpressionEvaluationResult],
    ) -> tuple[
        list[EligibilityReason],
        list[EligibilityReason],
        list[EligibilityReason],
        list[EligibilityReason],
    ]:
        blocking: list[EligibilityReason] = []
        conditional: list[EligibilityReason] = []
        permission: list[EligibilityReason] = []
        manual: list[EligibilityReason] = []
        for expression in expressions:
            reason = EligibilityReason(
                reason_code=expression.reason_code,
                explanation=expression.explanation,
                course_rule_expression_id=expression.course_rule_expression_id,
                referenced_entity_type="course" if expression.matched_course_id else None,
                referenced_entity_id=expression.matched_course_id,
                expected_value=expression.expected_value,
                actual_value=expression.actual_value,
            )
            if expression.result is EligibilityRuleResult.NOT_SATISFIED:
                blocking.append(reason)
            elif expression.result is EligibilityRuleResult.CONDITIONALLY_SATISFIED:
                conditional.append(reason)
            elif expression.result is EligibilityRuleResult.PERMISSION_REQUIRED:
                permission.append(reason)
            elif expression.result is EligibilityRuleResult.MANUAL_REVIEW_REQUIRED:
                manual.append(reason)
        return blocking, conditional, permission, manual

    def _corequisite_summary(
        self,
        expressions: list[ExpressionEvaluationResult],
    ) -> CorequisiteSummary | None:
        required: list[UUID] = []
        already_completed: list[UUID] = []
        currently_in_progress: list[UUID] = []
        must_enroll: list[UUID] = []
        for expression in expressions:
            if expression.reason_code.startswith("COREQUISITE") and expression.matched_course_id:
                required.append(expression.matched_course_id)
                if expression.reason_code == "COREQUISITE_MUST_ENROLL":
                    must_enroll.append(expression.matched_course_id)
                elif expression.reason_code == "COREQUISITE_CONCURRENT_PLAN":
                    must_enroll.append(expression.matched_course_id)
                elif expression.reason_code == "COREQUISITE_IN_PROGRESS":
                    currently_in_progress.append(expression.matched_course_id)
                elif expression.reason_code in {
                    "COREQUISITE_COMPLETED",
                    "COREQUISITE_TRANSFER_SATISFIED",
                }:
                    already_completed.append(expression.matched_course_id)
        if not required:
            return None
        return CorequisiteSummary(
            required_corequisite_courses=list(dict.fromkeys(required)),
            already_completed=list(dict.fromkeys(already_completed)),
            currently_in_progress=list(dict.fromkeys(currently_in_progress)),
            must_enroll_concurrently=list(dict.fromkeys(must_enroll)),
        )

    def _registration_availability(
        self, section: Section | None
    ) -> RegistrationAvailability | None:
        if section is None:
            return None
        note = "Section availability is reported separately from academic eligibility."
        return RegistrationAvailability(
            section_status=section.status.value,
            available_seats=section.available_seats,
            waitlist_available=section.waitlist_available,
            availability_note=note,
        )

    def _snapshot_hash(
        self,
        context: EligibilityRequestContext,
        rules: list[CourseRule],
    ) -> str:
        snapshot = active_course_state_snapshot(self._db, context.student.id)
        attempts = effective_student_course_attempts(self._db, context.student.id)
        payload = "|".join(
            [
                str(context.student.id),
                str(context.course.id),
                str(context.section.id if context.section else ""),
                str(context.target_term.id),
                context.mode.value,
                ",".join(str(rule.id) for rule in rules),
                ",".join(
                    str(course_id) for course_id in sorted(context.planned_corequisite_course_ids)
                ),
                str(snapshot.id) if snapshot is not None else "demo",
                ",".join(str(attempt.id) for attempt in attempts),
            ]
        )
        return sha256(payload.encode("utf-8")).hexdigest()


class CourseEligibilityApplicationService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_check(
        self,
        student_profile_id: UUID,
        course_id: UUID,
        section_id: UUID | None,
        target_term_id: UUID,
        mode: EligibilityMode,
        planned_corequisite_course_ids: list[UUID] | None = None,
    ) -> EligibilityCheckRun:
        engine = CourseEligibilityEngine(self._db)
        result = engine.evaluate(
            student_profile_id=student_profile_id,
            course_id=course_id,
            section_id=section_id,
            target_term_id=target_term_id,
            mode=mode,
            planned_corequisite_course_ids=planned_corequisite_course_ids,
        )
        course = self._db.get(Course, course_id)
        if course is None:
            raise CourseEligibilityValidationError(
                "not_found", f"Course {course_id} was not found."
            )
        run = EligibilityCheckRun(
            id=uuid4(),
            institution_id=course.institution_id,
            student_profile_id=student_profile_id,
            course_id=course_id,
            section_id=section_id,
            target_term_id=target_term_id,
            mode=mode,
            status=(
                EligibilityCheckStatus.COMPLETED_WITH_WARNINGS
                if result.warnings
                else EligibilityCheckStatus.COMPLETED
            ),
            engine_version=ENGINE_VERSION,
            overall_result=result.overall_result,
            academic_eligibility_result=result.academic_eligibility_result,
            started_at=utc_now(),
            completed_at=utc_now(),
            source_snapshot_hash=result.source_snapshot_hash,
            reviewed_rule_set_id=result.reviewed_rule_set_id,
            rule_resolution_state=result.rule_resolution_state,
            rule_source_reference=result.rule_source_reference,
            rule_catalog_year=result.rule_catalog_year,
            rule_resolution_explanation=result.rule_resolution_explanation,
            reviewed_rule_reasons=[
                {
                    "reason_code": reason.reason_code,
                    "explanation": reason.explanation,
                    "course_rule_id": str(reason.course_rule_id) if reason.course_rule_id else None,
                    "course_rule_expression_id": str(reason.course_rule_expression_id)
                    if reason.course_rule_expression_id
                    else None,
                    "referenced_entity_type": reason.referenced_entity_type,
                    "referenced_entity_id": str(reason.referenced_entity_id)
                    if reason.referenced_entity_id
                    else None,
                    "expected_value": reason.expected_value,
                    "actual_value": reason.actual_value,
                    "reviewed_rule_set_id": str(reason.reviewed_rule_set_id)
                    if reason.reviewed_rule_set_id
                    else None,
                    "rule_source_reference": reason.rule_source_reference,
                    "rule_catalog_year": reason.rule_catalog_year,
                }
                for reason in result.reviewed_rule_reasons
            ],
            reviewed_corequisite_summary=(
                {
                    "required_corequisite_courses": [
                        str(course_id)
                        for course_id in result.corequisite_summary.required_corequisite_courses
                    ],
                    "already_completed": [
                        str(course_id) for course_id in result.corequisite_summary.already_completed
                    ],
                    "currently_in_progress": [
                        str(course_id)
                        for course_id in result.corequisite_summary.currently_in_progress
                    ],
                    "must_enroll_concurrently": [
                        str(course_id)
                        for course_id in result.corequisite_summary.must_enroll_concurrently
                    ],
                }
                if result.reviewed_rule_set_id is not None
                and result.corequisite_summary is not None
                else None
            ),
        )
        self._db.add(run)
        self._db.flush()
        rule_evaluation_ids: dict[UUID, UUID] = {}
        for rule in result.rule_evaluations:
            rule_evaluation_id = uuid4()
            rule_evaluation_ids[rule.course_rule_id] = rule_evaluation_id
            self._db.add(
                RuleEvaluation(
                    id=rule_evaluation_id,
                    eligibility_check_run_id=run.id,
                    course_rule_id=rule.course_rule_id,
                    result=rule.result,
                    rule_type=rule.rule_type,
                    explanation=rule.explanation,
                    display_order=rule.display_order,
                )
            )
        self._db.flush()
        expression_to_rule_id = {
            expression.course_rule_expression_id: rule_evaluation_ids[rule.course_rule_id]
            for rule in result.rule_evaluations
            for expression in rule.expressions
        }
        for expression in result.expression_evaluations:
            self._db.add(
                RuleExpressionEvaluation(
                    id=uuid4(),
                    rule_evaluation_id=expression_to_rule_id[expression.course_rule_expression_id],
                    course_rule_expression_id=expression.course_rule_expression_id,
                    result=expression.result,
                    actual_value=expression.actual_value,
                    expected_value=expression.expected_value,
                    matched_course_id=expression.matched_course_id,
                    matched_attempt_id=expression.matched_attempt_id,
                    reason_code=expression.reason_code,
                    explanation=expression.explanation,
                )
            )
        for warning in result.warnings:
            self._db.add(
                EligibilityWarning(
                    id=uuid4(),
                    eligibility_check_run_id=run.id,
                    rule_evaluation_id=warning.rule_evaluation_id,
                    warning_code=warning.warning_code,
                    severity=warning.severity,
                    message=warning.message,
                    requires_advisor_confirmation=warning.requires_advisor_confirmation,
                )
            )
        self._db.commit()
        self._db.refresh(run)
        return run


@registry.register(CourseRuleExpressionNodeType.COMPLETED_COURSE)
def completed_course_evaluator(
    engine: CourseEligibilityEngine,
    expression: CourseRuleExpression,
    rule_type: CourseRuleType,
    context: EligibilityRequestContext,
) -> AttemptMatch:
    return engine.evaluate_completed_course(expression, rule_type, context)


@registry.register(CourseRuleExpressionNodeType.MINIMUM_GRADE)
def minimum_grade_evaluator(
    engine: CourseEligibilityEngine,
    expression: CourseRuleExpression,
    rule_type: CourseRuleType,
    context: EligibilityRequestContext,
) -> AttemptMatch:
    return engine.evaluate_minimum_grade(expression, rule_type, context)


@registry.register(CourseRuleExpressionNodeType.MINIMUM_COMPLETED_CREDITS)
def minimum_completed_credits_evaluator(
    engine: CourseEligibilityEngine,
    expression: CourseRuleExpression,
    rule_type: CourseRuleType,
    context: EligibilityRequestContext,
) -> AttemptMatch:
    return engine.evaluate_minimum_completed_credits(expression, rule_type, context)


@registry.register(CourseRuleExpressionNodeType.CLASS_STANDING)
def class_standing_evaluator(
    engine: CourseEligibilityEngine,
    expression: CourseRuleExpression,
    rule_type: CourseRuleType,
    context: EligibilityRequestContext,
) -> AttemptMatch:
    return engine.evaluate_class_standing(expression, rule_type, context)


@registry.register(CourseRuleExpressionNodeType.MAJOR_RESTRICTION)
@registry.register(CourseRuleExpressionNodeType.MINOR_RESTRICTION)
@registry.register(CourseRuleExpressionNodeType.PROGRAM_RESTRICTION)
def program_restriction_evaluator(
    engine: CourseEligibilityEngine,
    expression: CourseRuleExpression,
    rule_type: CourseRuleType,
    context: EligibilityRequestContext,
) -> AttemptMatch:
    return engine.evaluate_program_restriction(expression, rule_type, context)


@registry.register(CourseRuleExpressionNodeType.CAMPUS_RESTRICTION)
def campus_restriction_evaluator(
    engine: CourseEligibilityEngine,
    expression: CourseRuleExpression,
    rule_type: CourseRuleType,
    context: EligibilityRequestContext,
) -> AttemptMatch:
    return engine.evaluate_campus_restriction(expression, rule_type, context)


@registry.register(CourseRuleExpressionNodeType.PERMISSION_REQUIRED)
def permission_required_evaluator(
    engine: CourseEligibilityEngine,
    expression: CourseRuleExpression,
    rule_type: CourseRuleType,
    context: EligibilityRequestContext,
) -> AttemptMatch:
    return engine.evaluate_permission_required(expression, rule_type, context)
