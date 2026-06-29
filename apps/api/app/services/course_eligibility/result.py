from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.models.academic import (
    AuditWarningSeverity,
    CourseRuleExpressionNodeType,
    CourseRuleType,
    EligibilityOverallResult,
    EligibilityRuleResult,
)


@dataclass(frozen=True)
class EligibilityReason:
    reason_code: str
    explanation: str
    course_rule_id: UUID | None = None
    course_rule_expression_id: UUID | None = None
    referenced_entity_type: str | None = None
    referenced_entity_id: UUID | None = None
    expected_value: str | None = None
    actual_value: str | None = None


@dataclass(frozen=True)
class CorequisiteSummary:
    required_corequisite_courses: list[UUID] = field(default_factory=list)
    already_completed: list[UUID] = field(default_factory=list)
    currently_in_progress: list[UUID] = field(default_factory=list)
    must_enroll_concurrently: list[UUID] = field(default_factory=list)


@dataclass(frozen=True)
class RegistrationAvailability:
    section_status: str
    available_seats: int | None = None
    waitlist_available: int | None = None
    availability_note: str | None = None


@dataclass(frozen=True)
class ExpressionEvaluationResult:
    course_rule_expression_id: UUID
    node_type: CourseRuleExpressionNodeType
    result: EligibilityRuleResult
    reason_code: str
    explanation: str
    display_order: int
    actual_value: str | None = None
    expected_value: str | None = None
    matched_course_id: UUID | None = None
    matched_attempt_id: UUID | None = None


@dataclass(frozen=True)
class RuleEvaluationResult:
    course_rule_id: UUID
    rule_type: CourseRuleType
    result: EligibilityRuleResult
    explanation: str
    display_order: int
    expressions: list[ExpressionEvaluationResult] = field(default_factory=list)


@dataclass(frozen=True)
class EligibilityWarningResult:
    warning_code: str
    severity: AuditWarningSeverity
    message: str
    requires_advisor_confirmation: bool
    rule_evaluation_id: UUID | None = None


@dataclass(frozen=True)
class EligibilityResult:
    overall_result: EligibilityOverallResult
    academic_eligibility_result: EligibilityOverallResult
    source_snapshot_hash: str
    rule_evaluations: list[RuleEvaluationResult]
    expression_evaluations: list[ExpressionEvaluationResult]
    blocking_reasons: list[EligibilityReason] = field(default_factory=list)
    conditional_reasons: list[EligibilityReason] = field(default_factory=list)
    permissions_required: list[EligibilityReason] = field(default_factory=list)
    manual_review_reasons: list[EligibilityReason] = field(default_factory=list)
    corequisites_to_add: list[UUID] = field(default_factory=list)
    corequisite_summary: CorequisiteSummary | None = None
    registration_availability: RegistrationAvailability | None = None
    warnings: list[EligibilityWarningResult] = field(default_factory=list)
