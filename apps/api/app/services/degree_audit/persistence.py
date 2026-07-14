from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import (
    AuditCourseApplication,
    AuditMode,
    AuditRunStatus,
    DegreeAuditRun,
    DegreeAuditWarning,
    ProgramVersion,
    RequirementEvaluation,
    StudentAcademicProgram,
    StudentAcademicProgramStatus,
    StudentProfile,
)
from app.services.degree_audit.engine import DegreeAuditEngine, utc_now
from app.services.degree_audit.exceptions import DegreeAuditValidationError
from app.services.degree_audit.result import DegreeAuditResult


class DegreeAuditApplicationService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_audit(
        self,
        student_profile_id: UUID,
        program_version_id: UUID,
        mode: AuditMode,
    ) -> DegreeAuditRun:
        student, program_version = self._validate_request(student_profile_id, program_version_id)
        run = DegreeAuditRun(
            id=uuid4(),
            student_profile_id=student.id,
            program_version_id=program_version.id,
            status=AuditRunStatus.RUNNING,
            engine_version="phase-3a-degree-audit-v1",
            calculation_mode=mode,
            started_at=utc_now(),
            total_required_credits=Decimal("0.0"),
            completed_credits=Decimal("0.0"),
            in_progress_credits=Decimal("0.0"),
            planned_credits=Decimal("0.0"),
            remaining_credits=Decimal("0.0"),
            completion_percentage=Decimal("0.00"),
            source_snapshot_hash="pending",
            rule_resolution_state="MISSING",
            rule_resolution_explanation="No reviewed rule set was selected.",
        )
        self._db.add(run)
        self._db.flush()
        try:
            result = DegreeAuditEngine(self._db).evaluate(student.id, program_version.id, mode)
            self._persist_success(run, result)
            self._db.commit()
        except Exception:
            self._db.rollback()
            run = DegreeAuditRun(
                id=run.id,
                student_profile_id=student.id,
                program_version_id=program_version.id,
                status=AuditRunStatus.FAILED,
                engine_version="phase-3a-degree-audit-v1",
                calculation_mode=mode,
                started_at=run.started_at,
                completed_at=utc_now(),
                total_required_credits=Decimal("0.0"),
                completed_credits=Decimal("0.0"),
                in_progress_credits=Decimal("0.0"),
                planned_credits=Decimal("0.0"),
                remaining_credits=Decimal("0.0"),
                completion_percentage=Decimal("0.00"),
                source_snapshot_hash="failed",
                rule_resolution_state="MISSING",
                rule_resolution_explanation=(
                    "The degree audit failed before rule resolution completed."
                ),
            )
            self._db.add(run)
            self._db.commit()
            raise
        self._db.refresh(run)
        return run

    def _validate_request(
        self,
        student_profile_id: UUID,
        program_version_id: UUID,
    ) -> tuple[StudentProfile, ProgramVersion]:
        student = self._db.get(StudentProfile, student_profile_id)
        if student is None:
            raise DegreeAuditValidationError(
                "not_found", f"StudentProfile {student_profile_id} was not found."
            )
        program_version = self._db.get(ProgramVersion, program_version_id)
        if program_version is None:
            raise DegreeAuditValidationError(
                "not_found", f"ProgramVersion {program_version_id} was not found."
            )
        if student.home_institution_id != program_version.institution_id:
            raise DegreeAuditValidationError(
                "institution_scope_mismatch",
                "Student and ProgramVersion must belong to the same institution.",
            )
        active_program = self._db.scalar(
            select(StudentAcademicProgram).where(
                StudentAcademicProgram.student_profile_id == student.id,
                StudentAcademicProgram.program_version_id == program_version.id,
                StudentAcademicProgram.status == StudentAcademicProgramStatus.ACTIVE,
            )
        )
        if active_program is None:
            raise DegreeAuditValidationError(
                "program_not_declared",
                "Student is not actively associated with this ProgramVersion.",
            )
        return student, program_version

    def _persist_success(self, run: DegreeAuditRun, result: DegreeAuditResult) -> None:
        persist_degree_audit_success(self._db, run, result)


def persist_degree_audit_success(
    db: Session, run: DegreeAuditRun, result: DegreeAuditResult
) -> None:
    run.status = result.status
    run.engine_version = result.engine_version
    run.calculation_mode = result.calculation_mode
    run.completed_at = utc_now()
    run.total_required_credits = result.total_required_credits
    run.completed_credits = result.completed_credits
    run.in_progress_credits = result.in_progress_credits
    run.planned_credits = result.planned_credits
    run.remaining_credits = result.remaining_credits
    run.completion_percentage = result.completion_percentage
    run.source_snapshot_hash = result.source_snapshot_hash
    run.reviewed_rule_set_id = result.reviewed_rule_set_id
    run.rule_resolution_state = result.rule_resolution_state
    run.rule_source_reference = result.rule_source_reference
    run.rule_catalog_year = result.rule_catalog_year
    run.rule_resolution_explanation = result.rule_resolution_explanation

    evaluation_ids: dict[UUID, UUID] = {}
    for requirement in result.requirements:
        evaluation_id = uuid4()
        evaluation_ids[requirement.requirement_node_id] = evaluation_id
        db.add(
            RequirementEvaluation(
                id=evaluation_id,
                degree_audit_run_id=run.id,
                requirement_node_id=requirement.requirement_node_id,
                status=requirement.status,
                required_credits=requirement.required_credits,
                satisfied_credits=requirement.satisfied_credits,
                remaining_credits=requirement.remaining_credits,
                required_courses=requirement.required_courses,
                satisfied_courses=requirement.satisfied_courses,
                remaining_courses=requirement.remaining_courses,
                minimum_grade=requirement.minimum_grade,
                explanation=requirement.explanation,
                display_order=requirement.display_order,
            )
        )

    db.flush()

    for requirement in result.requirements:
        evaluation_id = evaluation_ids[requirement.requirement_node_id]
        for application in requirement.applications:
            db.add(
                AuditCourseApplication(
                    id=uuid4(),
                    degree_audit_run_id=run.id,
                    requirement_evaluation_id=evaluation_id,
                    course_id=application.course_id,
                    student_course_attempt_id=application.student_course_attempt_id,
                    transfer_credit_id=application.transfer_credit_id,
                    course_waiver_id=application.course_waiver_id,
                    course_substitution_id=application.course_substitution_id,
                    application_type=application.application_type,
                    credit_amount=application.credit_amount,
                    grade=application.grade,
                    is_completed=application.is_completed,
                    is_in_progress=application.is_in_progress,
                    is_planned=application.is_planned,
                    is_shared=application.is_shared,
                    explanation=application.explanation,
                )
            )

    for warning in result.warnings:
        db.add(
            DegreeAuditWarning(
                id=uuid4(),
                degree_audit_run_id=run.id,
                requirement_evaluation_id=(
                    evaluation_ids.get(warning.requirement_node_id)
                    if warning.requirement_node_id
                    else None
                ),
                warning_code=warning.warning_code,
                severity=warning.severity,
                message=warning.message,
                requires_advisor_confirmation=warning.requires_advisor_confirmation,
            )
        )
