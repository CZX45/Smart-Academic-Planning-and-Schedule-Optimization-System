from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from app.models.academic import (
    ApprovalStatus,
    AuditApplicationType,
    AuditMode,
    AuditWarningSeverity,
    Course,
    CourseEquivalency,
    CourseSubstitution,
    CourseWaiver,
    RequirementCourseOption,
    RequirementNode,
    RequirementType,
    SourceType,
    StudentCourseAttempt,
    StudentCourseAttemptStatus,
    TransferCredit,
)
from app.services.degree_audit.allocator import SourceKey
from app.services.degree_audit.grade_policy import GradePolicy
from app.services.degree_audit.result import AuditWarningResult

ZERO = Decimal("0.0")


@dataclass(frozen=True)
class CourseCandidate:
    source_key: SourceKey
    course_id: UUID | None
    application_type: AuditApplicationType
    credits: Decimal
    grade: str | None
    is_completed: bool
    is_in_progress: bool
    is_planned: bool
    is_resident: bool
    explanation: str
    course_level: int | None = None
    student_course_attempt_id: UUID | None = None
    transfer_credit_id: UUID | None = None
    course_waiver_id: UUID | None = None
    course_substitution_id: UUID | None = None


@dataclass
class AuditContext:
    student_profile_id: UUID
    program_version_id: UUID
    mode: AuditMode
    institution_id: UUID
    total_required_credits: Decimal
    nodes_by_id: dict[UUID, RequirementNode]
    children_by_parent: dict[UUID | None, list[RequirementNode]]
    options_by_node: dict[UUID, list[RequirementCourseOption]]
    courses_by_id: dict[UUID, Course]
    grade_policy: GradePolicy
    warnings: list[AuditWarningResult] = field(default_factory=list)
    attempts_by_course: dict[UUID, list[StudentCourseAttempt]] = field(default_factory=dict)
    transfers_by_course: dict[UUID, list[TransferCredit]] = field(default_factory=dict)
    waivers_by_requirement: dict[UUID, list[CourseWaiver]] = field(default_factory=dict)
    substitutions_by_requirement: dict[UUID, list[CourseSubstitution]] = field(default_factory=dict)
    equivalencies_by_equivalent: dict[UUID, list[CourseEquivalency]] = field(default_factory=dict)
    reviewed_rule_set_id: UUID | None = None
    rule_resolution_state: str = "MISSING"
    rule_source_reference: str | None = None
    rule_catalog_year: str | None = None
    rule_resolution_explanation: str = "No reviewed rule set was selected."

    def waiver_candidates(self, node: RequirementNode) -> list[CourseCandidate]:
        candidates: list[CourseCandidate] = []
        for waiver in self.waivers_by_requirement.get(node.id, []):
            if waiver.status is not ApprovalStatus.APPROVED:
                continue
            candidates.append(
                CourseCandidate(
                    source_key=("waiver", waiver.id),
                    course_id=None,
                    application_type=AuditApplicationType.WAIVER,
                    credits=ZERO,
                    grade=None,
                    is_completed=True,
                    is_in_progress=False,
                    is_planned=False,
                    is_resident=False,
                    explanation=(
                        "Approved waiver satisfies this requirement but does not "
                        "add earned credits."
                    ),
                    course_waiver_id=waiver.id,
                )
            )
        return candidates

    def course_candidates(
        self,
        node: RequirementNode,
        course_id: UUID,
        minimum_grade: str | None,
    ) -> list[CourseCandidate]:
        candidates = self._direct_course_candidates(node, course_id, minimum_grade)
        candidates.extend(self._equivalency_candidates(node, course_id, minimum_grade))
        candidates.extend(self._substitution_candidates(node, course_id, minimum_grade))
        return sorted(candidates, key=candidate_sort_key)

    def all_course_candidates(
        self,
        node: RequirementNode,
        minimum_grade: str | None,
    ) -> list[CourseCandidate]:
        candidates: list[CourseCandidate] = []
        for course_id in sorted(self.courses_by_id):
            candidates.extend(self._direct_course_candidates(node, course_id, minimum_grade))
        return sorted(candidates, key=candidate_sort_key)

    def credit_summary(self) -> tuple[Decimal, Decimal, Decimal]:
        completed = ZERO
        in_progress = ZERO
        planned = ZERO
        seen_courses: set[UUID] = set()
        for candidate in self.all_course_candidates(
            RequirementNode(
                id=UUID("00000000-0000-0000-0000-000000000000"),
                institution_id=self.institution_id,
                program_version_id=self.program_version_id,
                code="SUMMARY",
                name="Summary",
                requirement_type=RequirementType.TOTAL_CREDITS,
                source_type=SourceType.MOCK,
                is_official=False,
            ),
            None,
        ):
            if candidate.course_id is None or candidate.course_id in seen_courses:
                continue
            seen_courses.add(candidate.course_id)
            if candidate.is_completed:
                completed += candidate.credits
            elif candidate.is_in_progress:
                in_progress += candidate.credits
            elif candidate.is_planned:
                planned += candidate.credits
        return completed, in_progress, planned

    def _direct_course_candidates(
        self,
        node: RequirementNode,
        course_id: UUID,
        minimum_grade: str | None,
    ) -> list[CourseCandidate]:
        candidates: list[CourseCandidate] = []
        for attempt in self.attempts_by_course.get(course_id, []):
            candidate = self._attempt_candidate(node, attempt, course_id, minimum_grade)
            if candidate is not None:
                candidates.append(candidate)
        for transfer in self.transfers_by_course.get(course_id, []):
            candidate = self._transfer_candidate(node, transfer, minimum_grade)
            if candidate is not None:
                candidates.append(candidate)
        return candidates

    def _equivalency_candidates(
        self,
        node: RequirementNode,
        target_course_id: UUID,
        minimum_grade: str | None,
    ) -> list[CourseCandidate]:
        candidates: list[CourseCandidate] = []
        for equivalency in self.equivalencies_by_equivalent.get(target_course_id, []):
            for attempt in self.attempts_by_course.get(equivalency.source_course_id, []):
                candidate = self._attempt_candidate(
                    node,
                    attempt,
                    target_course_id,
                    minimum_grade,
                    application_type=AuditApplicationType.EQUIVALENCY,
                    explanation_prefix="Direct course equivalency applies",
                )
                if candidate is not None:
                    candidates.append(candidate)
        return candidates

    def _substitution_candidates(
        self,
        node: RequirementNode,
        target_course_id: UUID,
        minimum_grade: str | None,
    ) -> list[CourseCandidate]:
        candidates: list[CourseCandidate] = []
        for substitution in self.substitutions_by_requirement.get(node.id, []):
            if substitution.status is not ApprovalStatus.APPROVED:
                continue
            if substitution.original_course_id != target_course_id:
                continue
            for attempt in self.attempts_by_course.get(substitution.substitute_course_id, []):
                if attempt.status is not StudentCourseAttemptStatus.COMPLETED:
                    continue
                candidate = self._attempt_candidate(
                    node,
                    attempt,
                    substitution.substitute_course_id,
                    minimum_grade,
                    application_type=AuditApplicationType.SUBSTITUTION,
                    course_substitution_id=substitution.id,
                    source_key=("substitution", substitution.id),
                    explanation_prefix="Approved substitution applies",
                )
                if candidate is not None:
                    candidates.append(candidate)
        return candidates

    def _attempt_candidate(
        self,
        node: RequirementNode,
        attempt: StudentCourseAttempt,
        applied_course_id: UUID,
        minimum_grade: str | None,
        *,
        application_type: AuditApplicationType = AuditApplicationType.COURSE_ATTEMPT,
        course_substitution_id: UUID | None = None,
        source_key: SourceKey | None = None,
        explanation_prefix: str = "Student course attempt applies",
    ) -> CourseCandidate | None:
        course = self.courses_by_id[applied_course_id]
        if attempt.status is StudentCourseAttemptStatus.COMPLETED:
            grade_result = self.grade_policy.satisfies_minimum(attempt.grade, minimum_grade)
            if grade_result.warning_code is not None:
                self.warnings.append(
                    AuditWarningResult(
                        warning_code=grade_result.warning_code,
                        severity=AuditWarningSeverity.WARNING,
                        message=grade_result.message or "Grade requires advisor confirmation.",
                        requires_advisor_confirmation=True,
                        requirement_node_id=node.id,
                    )
                )
            if not grade_result.is_satisfied:
                return None
            return CourseCandidate(
                source_key=source_key or ("attempt", attempt.id),
                course_id=applied_course_id,
                application_type=application_type,
                credits=attempt.credits_earned,
                grade=attempt.grade,
                is_completed=True,
                is_in_progress=False,
                is_planned=False,
                is_resident=True,
                explanation=(
                    f"{explanation_prefix}: {course.subject_code} {course.course_number} "
                    f"completed with grade {attempt.grade or 'unknown'}."
                ),
                course_level=course.course_level,
                student_course_attempt_id=attempt.id,
                course_substitution_id=course_substitution_id,
            )
        if attempt.status is StudentCourseAttemptStatus.IN_PROGRESS:
            return CourseCandidate(
                source_key=source_key or ("attempt", attempt.id),
                course_id=applied_course_id,
                application_type=application_type,
                credits=attempt.credits_attempted,
                grade=attempt.grade,
                is_completed=False,
                is_in_progress=True,
                is_planned=False,
                is_resident=True,
                explanation=(
                    f"{course.subject_code} {course.course_number} is in progress and is "
                    "shown as a potential contribution only."
                ),
                course_level=course.course_level,
                student_course_attempt_id=attempt.id,
                course_substitution_id=course_substitution_id,
            )
        if attempt.status is StudentCourseAttemptStatus.PLANNED:
            return CourseCandidate(
                source_key=source_key or ("attempt", attempt.id),
                course_id=applied_course_id,
                application_type=application_type,
                credits=attempt.credits_attempted,
                grade=attempt.grade,
                is_completed=False,
                is_in_progress=False,
                is_planned=True,
                is_resident=True,
                explanation=(
                    f"{course.subject_code} {course.course_number} is planned and is not "
                    "treated as completed."
                ),
                course_level=course.course_level,
                student_course_attempt_id=attempt.id,
                course_substitution_id=course_substitution_id,
            )
        if attempt.status is StudentCourseAttemptStatus.INCOMPLETE:
            self.warnings.append(
                AuditWarningResult(
                    warning_code="INCOMPLETE_ATTEMPT",
                    severity=AuditWarningSeverity.WARNING,
                    message="Incomplete attempts are not applied as completed in Phase 3A.",
                    requires_advisor_confirmation=True,
                    requirement_node_id=node.id,
                )
            )
        return None

    def _transfer_candidate(
        self,
        node: RequirementNode,
        transfer: TransferCredit,
        minimum_grade: str | None,
    ) -> CourseCandidate | None:
        if transfer.status is not ApprovalStatus.APPROVED:
            return None
        if transfer.equivalent_course_id is None:
            self.warnings.append(
                AuditWarningResult(
                    warning_code="TRANSFER_WITHOUT_EQUIVALENCY",
                    severity=AuditWarningSeverity.WARNING,
                    message="Approved transfer credit has no equivalent course and needs review.",
                    requires_advisor_confirmation=True,
                    requirement_node_id=node.id,
                )
            )
            return None
        if minimum_grade is not None:
            grade_result = self.grade_policy.satisfies_minimum(transfer.grade, minimum_grade)
            if grade_result.warning_code is not None:
                self.warnings.append(
                    AuditWarningResult(
                        warning_code=grade_result.warning_code,
                        severity=AuditWarningSeverity.WARNING,
                        message=grade_result.message or "Transfer grade requires advisor review.",
                        requires_advisor_confirmation=True,
                        requirement_node_id=node.id,
                    )
                )
            if not grade_result.is_satisfied:
                return None
        course = self.courses_by_id[transfer.equivalent_course_id]
        return CourseCandidate(
            source_key=("transfer", transfer.id),
            course_id=transfer.equivalent_course_id,
            application_type=AuditApplicationType.TRANSFER_CREDIT,
            credits=transfer.credits_earned,
            grade=transfer.grade,
            is_completed=True,
            is_in_progress=False,
            is_planned=False,
            is_resident=False,
            explanation=(
                f"Approved transfer {transfer.source_course_code} applies as "
                f"{course.subject_code} {course.course_number}."
            ),
            course_level=course.course_level,
            transfer_credit_id=transfer.id,
        )

    def source_snapshot_hash(self) -> str:
        payload = {
            "student_profile_id": str(self.student_profile_id),
            "program_version_id": str(self.program_version_id),
            "mode": self.mode.value,
            "reviewed_rule_set_id": str(self.reviewed_rule_set_id or ""),
            "rule_resolution_state": self.rule_resolution_state,
            "nodes": sorted(str(node_id) for node_id in self.nodes_by_id),
            "attempts": [
                [str(attempt.id), str(attempt.course_id), attempt.status.value, attempt.grade]
                for attempts in self.attempts_by_course.values()
                for attempt in attempts
            ],
            "transfers": [
                [str(transfer.id), str(transfer.equivalent_course_id), transfer.status.value]
                for transfers in self.transfers_by_course.values()
                for transfer in transfers
            ],
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def sorted_nodes(nodes: list[RequirementNode]) -> list[RequirementNode]:
    return sorted(nodes, key=lambda node: (node.display_order, node.code, str(node.id)))


def build_children_by_parent(
    nodes: list[RequirementNode],
) -> dict[UUID | None, list[RequirementNode]]:
    children_by_parent: dict[UUID | None, list[RequirementNode]] = defaultdict(list)
    for node in nodes:
        children_by_parent[node.parent_id].append(node)
    return {parent_id: sorted_nodes(children) for parent_id, children in children_by_parent.items()}


def candidate_sort_key(candidate: CourseCandidate) -> tuple[int, int, str]:
    if candidate.is_completed:
        state_rank = 0
    elif candidate.is_in_progress:
        state_rank = 1
    elif candidate.is_planned:
        state_rank = 2
    else:
        state_rank = 3
    type_rank = 0 if candidate.application_type is AuditApplicationType.WAIVER else 1
    return (state_rank, type_rank, str(candidate.source_key[1]))


def build_options_by_node(
    options: list[RequirementCourseOption],
) -> dict[UUID, list[RequirementCourseOption]]:
    options_by_node: dict[UUID, list[RequirementCourseOption]] = defaultdict(list)
    for option in options:
        options_by_node[option.requirement_node_id].append(option)
    return {
        node_id: sorted(records, key=lambda option: (option.display_order, str(option.course_id)))
        for node_id, records in options_by_node.items()
    }


def build_attempts_by_course(
    attempts: list[StudentCourseAttempt],
) -> dict[UUID, list[StudentCourseAttempt]]:
    attempts_by_course: dict[UUID, list[StudentCourseAttempt]] = defaultdict(list)
    for attempt in attempts:
        attempts_by_course[attempt.course_id].append(attempt)
    return {
        course_id: sorted(records, key=lambda attempt: (attempt.attempt_number, str(attempt.id)))
        for course_id, records in attempts_by_course.items()
    }


def build_transfers_by_course(transfers: list[TransferCredit]) -> dict[UUID, list[TransferCredit]]:
    transfers_by_course: dict[UUID, list[TransferCredit]] = defaultdict(list)
    for transfer in transfers:
        if transfer.equivalent_course_id is not None:
            transfers_by_course[transfer.equivalent_course_id].append(transfer)
    return {
        course_id: sorted(records, key=lambda transfer: str(transfer.id))
        for course_id, records in transfers_by_course.items()
    }


def build_waivers_by_requirement(waivers: list[CourseWaiver]) -> dict[UUID, list[CourseWaiver]]:
    waivers_by_requirement: dict[UUID, list[CourseWaiver]] = defaultdict(list)
    for waiver in waivers:
        if waiver.requirement_node_id is not None:
            waivers_by_requirement[waiver.requirement_node_id].append(waiver)
    return {
        requirement_id: sorted(records, key=lambda waiver: str(waiver.id))
        for requirement_id, records in waivers_by_requirement.items()
    }


def build_substitutions_by_requirement(
    substitutions: list[CourseSubstitution],
) -> dict[UUID, list[CourseSubstitution]]:
    substitutions_by_requirement: dict[UUID, list[CourseSubstitution]] = defaultdict(list)
    for substitution in substitutions:
        if substitution.requirement_node_id is not None:
            substitutions_by_requirement[substitution.requirement_node_id].append(substitution)
    return {
        requirement_id: sorted(records, key=lambda substitution: str(substitution.id))
        for requirement_id, records in substitutions_by_requirement.items()
    }


def build_equivalencies_by_equivalent(
    equivalencies: list[CourseEquivalency],
) -> dict[UUID, list[CourseEquivalency]]:
    by_equivalent: dict[UUID, list[CourseEquivalency]] = defaultdict(list)
    for equivalency in equivalencies:
        by_equivalent[equivalency.equivalent_course_id].append(equivalency)
    return {
        course_id: sorted(records, key=lambda equivalency: str(equivalency.id))
        for course_id, records in by_equivalent.items()
    }


def add_pending_record_warnings(
    context: AuditContext,
    transfers: list[TransferCredit],
    waivers: list[CourseWaiver],
    substitutions: list[CourseSubstitution],
) -> None:
    for transfer in transfers:
        if transfer.status is ApprovalStatus.PENDING:
            context.warnings.append(
                AuditWarningResult(
                    warning_code="PENDING_TRANSFER",
                    severity=AuditWarningSeverity.WARNING,
                    message=(
                        f"Pending transfer {transfer.source_course_code} is stored but not "
                        "applied to this audit."
                    ),
                    requires_advisor_confirmation=True,
                )
            )
    for waiver in waivers:
        if waiver.status is ApprovalStatus.PENDING:
            context.warnings.append(
                AuditWarningResult(
                    warning_code="PENDING_WAIVER",
                    severity=AuditWarningSeverity.WARNING,
                    message="Pending waiver is stored but not applied to this audit.",
                    requires_advisor_confirmation=True,
                    requirement_node_id=waiver.requirement_node_id,
                )
            )
    for substitution in substitutions:
        if substitution.status is ApprovalStatus.PENDING:
            context.warnings.append(
                AuditWarningResult(
                    warning_code="PENDING_SUBSTITUTION",
                    severity=AuditWarningSeverity.WARNING,
                    message="Pending substitution is stored but not applied to this audit.",
                    requires_advisor_confirmation=True,
                    requirement_node_id=substitution.requirement_node_id,
                )
            )
