from __future__ import annotations

from hashlib import sha256
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.academic import (
    AuditWarningSeverity,
    Course,
    EligibilityOverallResult,
    EligibilityRuleResult,
    StudentCourseAttempt,
    StudentCourseAttemptStatus,
    StudentProfile,
)
from app.services.course_eligibility.result import (
    CorequisiteSummary,
    EligibilityReason,
    EligibilityResult,
    EligibilityWarningResult,
)
from app.services.course_state.engine import effective_student_course_attempts
from app.services.reviewed_rules.contracts import CatalogRuleSet, CourseDefinition
from app.services.reviewed_rules.resolution import RuleResolution, RuleResolutionState


class EligibilityContextLike(Protocol):
    @property
    def student(self) -> StudentProfile: ...

    @property
    def course(self) -> Course: ...

    @property
    def catalog_courses(self) -> list[Course]: ...


def _course_definition(
    rule_set: CatalogRuleSet,
    course_id: UUID,
    subject_code: str,
    course_number: str,
) -> CourseDefinition | None:
    identifiers = {
        str(course_id),
        f"{subject_code} {course_number}".upper(),
        f"{subject_code}{course_number}".upper(),
    }
    return next(
        (
            definition
            for definition in rule_set.courses
            if definition.course_id in identifiers or definition.code.upper() in identifiers
        ),
        None,
    )


def evaluate_reviewed_prerequisites(
    db: Session,
    context: EligibilityContextLike,
    resolution: RuleResolution,
) -> EligibilityResult | None:
    """Evaluate the bounded prerequisite/corequisite declarations from 10A."""

    if resolution.state is RuleResolutionState.MISSING:
        return None
    source_reference = (
        resolution.rule_set.source.source_url_or_document_id
        if resolution.rule_set is not None
        else None
    )
    catalog_year = resolution.rule_set.source.catalog_year if resolution.rule_set else None
    reviewed_id = resolution.record.id if resolution.record else None
    if resolution.state is RuleResolutionState.CONFLICT or resolution.rule_set is None:
        return EligibilityResult(
            overall_result=EligibilityOverallResult.UNKNOWN,
            academic_eligibility_result=EligibilityOverallResult.UNKNOWN,
            source_snapshot_hash=sha256(str(reviewed_id or "conflict").encode()).hexdigest(),
            rule_evaluations=[],
            expression_evaluations=[],
            manual_review_reasons=[
                EligibilityReason(
                    reason_code="REVIEWED_RULE_CONFLICT",
                    explanation=resolution.explanation,
                    reviewed_rule_set_id=reviewed_id,
                    rule_source_reference=source_reference,
                    rule_catalog_year=catalog_year,
                )
            ],
            reviewed_rule_reasons=[
                EligibilityReason(
                    reason_code="REVIEWED_RULE_CONFLICT",
                    explanation=resolution.explanation,
                    reviewed_rule_set_id=reviewed_id,
                    rule_source_reference=source_reference,
                    rule_catalog_year=catalog_year,
                )
            ],
            warnings=[
                EligibilityWarningResult(
                    warning_code="REVIEWED_RULE_CONFLICT",
                    severity=AuditWarningSeverity.ERROR,
                    message=resolution.explanation,
                    requires_advisor_confirmation=True,
                )
            ],
            reviewed_rule_set_id=reviewed_id,
            rule_resolution_state=resolution.state.value,
            rule_source_reference=source_reference,
            rule_catalog_year=catalog_year,
            rule_resolution_explanation=resolution.explanation,
        )

    # The concrete context type is kept structural to avoid coupling the
    # reviewed-rule adapter to the legacy engine's private context class.
    course = context.course
    definition = _course_definition(
        resolution.rule_set,
        course.id,
        course.subject_code,
        course.course_number,
    )
    if definition is None:
        reason = EligibilityReason(
            reason_code="REVIEWED_COURSE_RULE_MISSING",
            explanation=(
                f"No reviewed catalog definition exists for {course.subject_code} "
                f"{course.course_number}. Eligibility is UNKNOWN."
            ),
            reviewed_rule_set_id=reviewed_id,
            rule_source_reference=source_reference,
            rule_catalog_year=catalog_year,
        )
        return EligibilityResult(
            overall_result=EligibilityOverallResult.UNKNOWN,
            academic_eligibility_result=EligibilityOverallResult.UNKNOWN,
            source_snapshot_hash=sha256(str(reviewed_id).encode()).hexdigest(),
            rule_evaluations=[],
            expression_evaluations=[],
            manual_review_reasons=[reason],
            reviewed_rule_reasons=[reason],
            warnings=[
                EligibilityWarningResult(
                    warning_code="REVIEWED_COURSE_RULE_MISSING",
                    severity=AuditWarningSeverity.WARNING,
                    message=reason.explanation,
                    requires_advisor_confirmation=True,
                )
            ],
            reviewed_rule_set_id=reviewed_id,
            rule_resolution_state=resolution.state.value,
            rule_source_reference=source_reference,
            rule_catalog_year=catalog_year,
            rule_resolution_explanation=resolution.explanation,
        )

    attempts = effective_student_course_attempts(db, context.student.id)
    attempts_by_course: dict[UUID, list[StudentCourseAttempt]] = {}
    for attempt in attempts:
        attempts_by_course.setdefault(attempt.course_id, []).append(attempt)
    reasons: list[EligibilityReason] = []
    blocking: list[EligibilityReason] = []
    conditional: list[EligibilityReason] = []
    manual: list[EligibilityReason] = []
    corequisites: list[UUID] = []
    completed_corequisites: list[UUID] = []
    in_progress_corequisites: list[UUID] = []
    for prerequisite_identifier in definition.prerequisite_ids:
        prerequisite = next(
            (
                candidate
                for candidate in context.catalog_courses
                if str(candidate.id) == prerequisite_identifier
                or f"{candidate.subject_code} {candidate.course_number}".upper()
                == prerequisite_identifier.upper()
                or candidate.subject_code.upper() + candidate.course_number.upper()
                == prerequisite_identifier.upper()
            ),
            None,
        )
        if prerequisite is None:
            reason = EligibilityReason(
                reason_code="REVIEWED_PREREQUISITE_UNKNOWN",
                explanation=f"Reviewed prerequisite {prerequisite_identifier} cannot be resolved.",
                reviewed_rule_set_id=reviewed_id,
                rule_source_reference=source_reference,
                rule_catalog_year=catalog_year,
            )
            manual.append(reason)
            continue
        course_attempts = attempts_by_course.get(prerequisite.id, [])
        if any(
            attempt.status is StudentCourseAttemptStatus.COMPLETED for attempt in course_attempts
        ):
            result = EligibilityRuleResult.SATISFIED
            reason_code = "REVIEWED_PREREQUISITE_SATISFIED"
            target = reasons
        elif any(
            attempt.status
            in {
                StudentCourseAttemptStatus.IN_PROGRESS,
                StudentCourseAttemptStatus.PLANNED,
            }
            for attempt in course_attempts
        ):
            result = EligibilityRuleResult.CONDITIONALLY_SATISFIED
            reason_code = "REVIEWED_PREREQUISITE_CONDITIONAL"
            target = conditional
        else:
            result = EligibilityRuleResult.NOT_SATISFIED
            reason_code = "REVIEWED_PREREQUISITE_NOT_SATISFIED"
            target = blocking
        reason = EligibilityReason(
            reason_code=reason_code,
            explanation=(
                f"{prerequisite.subject_code} {prerequisite.course_number} is "
                f"{result.value.lower().replace('_', ' ')} under the reviewed catalog rule."
            ),
            referenced_entity_type="COURSE",
            referenced_entity_id=prerequisite.id,
            reviewed_rule_set_id=reviewed_id,
            rule_source_reference=source_reference,
            rule_catalog_year=catalog_year,
        )
        target.append(reason)
    for corequisite_identifier in definition.corequisite_ids:
        corequisite = next(
            (
                candidate
                for candidate in context.catalog_courses
                if str(candidate.id) == corequisite_identifier
                or f"{candidate.subject_code} {candidate.course_number}".upper()
                == corequisite_identifier.upper()
            ),
            None,
        )
        if corequisite is None:
            manual.append(
                EligibilityReason(
                    reason_code="REVIEWED_COREQUISITE_UNKNOWN",
                    explanation=(
                        f"Reviewed corequisite {corequisite_identifier} cannot be resolved."
                    ),
                    reviewed_rule_set_id=reviewed_id,
                    rule_source_reference=source_reference,
                    rule_catalog_year=catalog_year,
                )
            )
            continue
        corequisites.append(corequisite.id)
        matching = attempts_by_course.get(corequisite.id, [])
        if any(attempt.status is StudentCourseAttemptStatus.COMPLETED for attempt in matching):
            completed_corequisites.append(corequisite.id)
        elif any(attempt.status is StudentCourseAttemptStatus.IN_PROGRESS for attempt in matching):
            in_progress_corequisites.append(corequisite.id)

    if manual:
        overall = EligibilityOverallResult.UNKNOWN
    elif blocking:
        overall = EligibilityOverallResult.NOT_ELIGIBLE
    elif conditional:
        overall = EligibilityOverallResult.CONDITIONALLY_ELIGIBLE
    else:
        overall = EligibilityOverallResult.ELIGIBLE
    all_reasons = [*reasons, *blocking, *conditional, *manual]
    return EligibilityResult(
        overall_result=overall,
        academic_eligibility_result=overall,
        source_snapshot_hash=sha256(
            "|".join([str(reviewed_id), *(reason.reason_code for reason in all_reasons)]).encode()
        ).hexdigest(),
        rule_evaluations=[],
        expression_evaluations=[],
        blocking_reasons=blocking,
        conditional_reasons=conditional,
        manual_review_reasons=manual,
        reviewed_rule_reasons=[*reasons, *blocking, *conditional, *manual],
        corequisites_to_add=[
            course_id
            for course_id in corequisites
            if course_id not in completed_corequisites and course_id not in in_progress_corequisites
        ],
        corequisite_summary=CorequisiteSummary(
            required_corequisite_courses=corequisites,
            already_completed=completed_corequisites,
            currently_in_progress=in_progress_corequisites,
            must_enroll_concurrently=[
                course_id
                for course_id in corequisites
                if course_id not in completed_corequisites
                and course_id not in in_progress_corequisites
            ],
        )
        if corequisites
        else None,
        warnings=[
            EligibilityWarningResult(
                warning_code="REVIEWED_RULE_SOURCE",
                severity=AuditWarningSeverity.INFO,
                message=(
                    "Eligibility uses an exact active reviewed catalog rule set and remains "
                    "advisory; confirm with the school or advisor."
                ),
                requires_advisor_confirmation=True,
            )
        ],
        reviewed_rule_set_id=reviewed_id,
        rule_resolution_state=resolution.state.value,
        rule_source_reference=source_reference,
        rule_catalog_year=catalog_year,
        rule_resolution_explanation=resolution.explanation,
    )
