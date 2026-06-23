from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from app.models.academic import (
    AuditApplicationType,
    AuditMode,
    AuditRunStatus,
    AuditWarningSeverity,
    RequirementEvaluationStatus,
    RequirementType,
)


@dataclass(frozen=True)
class AuditWarningResult:
    warning_code: str
    severity: AuditWarningSeverity
    message: str
    requires_advisor_confirmation: bool
    requirement_node_id: UUID | None = None


@dataclass(frozen=True)
class CourseApplicationResult:
    requirement_node_id: UUID
    application_type: AuditApplicationType
    credit_amount: Decimal
    is_completed: bool
    is_in_progress: bool
    is_planned: bool
    is_shared: bool
    explanation: str
    course_id: UUID | None = None
    student_course_attempt_id: UUID | None = None
    transfer_credit_id: UUID | None = None
    course_waiver_id: UUID | None = None
    course_substitution_id: UUID | None = None
    grade: str | None = None


@dataclass(frozen=True)
class RequirementResult:
    requirement_node_id: UUID
    requirement_code: str
    requirement_name: str
    requirement_type: RequirementType
    status: RequirementEvaluationStatus
    required_credits: Decimal | None
    satisfied_credits: Decimal
    remaining_credits: Decimal
    required_courses: int | None
    satisfied_courses: int
    remaining_courses: int
    minimum_grade: str | None
    explanation: str
    display_order: int
    applications: list[CourseApplicationResult] = field(default_factory=list)
    warnings: list[AuditWarningResult] = field(default_factory=list)


@dataclass(frozen=True)
class DegreeAuditResult:
    student_profile_id: UUID
    program_version_id: UUID
    status: AuditRunStatus
    engine_version: str
    calculation_mode: AuditMode
    total_required_credits: Decimal
    completed_credits: Decimal
    in_progress_credits: Decimal
    planned_credits: Decimal
    remaining_credits: Decimal
    completion_percentage: Decimal
    source_snapshot_hash: str
    requirements: list[RequirementResult]
    warnings: list[AuditWarningResult]
