"""Resolve real inputs without ever falling back to development fixtures."""

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import (
    AcademicProgram,
    AcademicTerm,
    AppliedImportedRecord,
    AppliedImportStatus,
    AppliedImportTargetEntityType,
    Course,
    CourseStateRecord,
    DataApplicationRun,
    DataImportReviewSession,
    DataImportRun,
    ImportedRecordReview,
    ProgramVersion,
    Section,
    SourceMetadataMixin,
    SourceType,
    StudentAcademicProgram,
    StudentAcademicProgramStatus,
    StudentProfile,
)
from app.schemas.academic import SourceMetadataResponse
from app.schemas.academic_workflow import (
    AcademicWorkflowResponse,
    WorkflowCourse,
    WorkflowIssue,
    WorkflowProgram,
    WorkflowTerm,
)
from app.services.course_state.engine import (
    active_course_state_snapshot,
    effective_student_course_attempts,
)
from app.services.reviewed_rules.resolution import RuleResolutionState, resolve_for_program_version
from app.services.schedule_optimizer.real_sections import (
    APPLIED_REVIEW_STATUSES,
    APPLIED_RUN_STATUSES,
    REVIEWED_DECISIONS,
    evaluate_reviewed_section,
)

REAL_SOURCES = {SourceType.OFFICIAL, SourceType.IMPORTED, SourceType.BROWSER_EXTENSION}


def source_metadata(record: SourceMetadataMixin) -> SourceMetadataResponse:
    return SourceMetadataResponse(
        source_type=record.source_type.value,
        is_official=record.is_official,
        source_reference=record.source_reference,
        source_retrieved_at=record.source_retrieved_at,
        source_confidence=record.source_confidence,
    )


def academic_workflow(db: Session, student: StudentProfile) -> AcademicWorkflowResponse:
    result = AcademicWorkflowResponse(student_profile_id=student.id, revision="")
    if student.source_type is SourceType.MOCK:
        result.issues.append(
            WorkflowIssue(reason_code="DEMO_PROFILE", message="演示档案不能作为真实学业数据来源。")
        )
        return result
    assignments = db.scalars(
        select(StudentAcademicProgram)
        .where(
            StudentAcademicProgram.student_profile_id == student.id,
            StudentAcademicProgram.status == StudentAcademicProgramStatus.ACTIVE,
            StudentAcademicProgram.source_type.in_(REAL_SOURCES),
        )
        .order_by(StudentAcademicProgram.program_type, StudentAcademicProgram.program_version_id)
    ).all()
    for assignment in assignments:
        version = db.get(ProgramVersion, assignment.program_version_id)
        if version is None or version.source_type not in REAL_SOURCES:
            continue
        if version.institution_id != student.home_institution_id:
            continue
        if student.home_campus_id and version.campus_id != student.home_campus_id:
            continue
        program = db.get(AcademicProgram, version.program_id)
        resolution = resolve_for_program_version(db, version.id)
        if program is None or program.source_type not in REAL_SOURCES:
            continue
        if resolution.state is not RuleResolutionState.ACTIVE or resolution.record is None:
            result.issues.append(
                WorkflowIssue(
                    reason_code=f"PROGRAM_RULES_{resolution.state.value}",
                    message=f"{program.name}（{version.catalog_year}）缺少唯一有效的已审核规则，请完成规则审核。",
                    evidence_reference=version.source_reference,
                )
            )
            continue
        if resolution.rule_set is None or not resolution.rule_set.requirements:
            result.issues.append(
                WorkflowIssue(
                    reason_code="PROGRAM_REQUIREMENTS_MISSING",
                    message=f"{program.name} 的已审核规则尚无毕业要求，请补全来源规则。",
                    evidence_reference=version.source_reference,
                )
            )
            continue
        result.programs.append(
            WorkflowProgram(
                id=version.id,
                name=program.name,
                catalog_year=version.catalog_year,
                relationship_type=assignment.program_type.value,
                reviewed_rule_set_id=resolution.record.id,
                source=source_metadata(version),
            )
        )

    # Successful applications must belong to this student and a completed review.
    applications = db.scalars(
        select(AppliedImportedRecord)
        .join(
            DataApplicationRun,
            AppliedImportedRecord.data_application_run_id == DataApplicationRun.id,
        )
        .join(
            ImportedRecordReview,
            AppliedImportedRecord.imported_record_review_id == ImportedRecordReview.id,
        )
        .join(
            DataImportReviewSession,
            ImportedRecordReview.review_session_id == DataImportReviewSession.id,
        )
        .join(DataImportRun, DataImportReviewSession.data_import_run_id == DataImportRun.id)
        .where(
            DataImportRun.student_profile_id == student.id,
            AppliedImportedRecord.status == AppliedImportStatus.SUCCESS,
            DataApplicationRun.status.in_(APPLIED_RUN_STATUSES),
            DataImportReviewSession.status.in_(APPLIED_REVIEW_STATUSES),
            ImportedRecordReview.decision.in_(REVIEWED_DECISIONS),
        )
    ).all()
    course_ids = {
        row.target_entity_id
        for row in applications
        if row.target_entity_type is AppliedImportTargetEntityType.COURSE
    }
    attempts = [
        attempt
        for attempt in effective_student_course_attempts(db, student.id)
        if attempt.source_type in REAL_SOURCES
        and (
            attempt.source_type is SourceType.OFFICIAL
            or attempt.course_state_snapshot_id is not None
            or any(
                row.target_entity_type is AppliedImportTargetEntityType.STUDENT_COURSE_ATTEMPT
                and row.target_entity_id == attempt.id
                for row in applications
            )
        )
    ]
    course_ids.update(attempt.course_id for attempt in attempts)
    term_ids = {attempt.term_id for attempt in attempts}
    sections = db.scalars(
        select(Section)
        .where(
            Section.id.in_(
                [
                    row.target_entity_id
                    for row in applications
                    if row.target_entity_type is AppliedImportTargetEntityType.SECTION
                ]
            ),
            Section.institution_id == student.home_institution_id,
        )
        .order_by(Section.term_id, Section.course_id, Section.section_code)
    ).all()
    for section in sections:
        check = evaluate_reviewed_section(
            db,
            section=section,
            student=student,
            target_term_id=section.term_id,
            requested_course_id=section.course_id,
            now=datetime.now(UTC),
        )
        if check.eligible:
            result.section_ids.append(section.id)
            course_ids.add(section.course_id)
            term_ids.add(section.term_id)
        else:
            result.issues.append(
                WorkflowIssue(
                    reason_code="SECTION_REVIEW_REQUIRED",
                    message=(
                        f"班次 {section.section_code} 不能用于排课：{', '.join(check.reason_codes)}"
                    ),
                    evidence_reference=section.source_reference,
                )
            )
    for course in db.scalars(
        select(Course)
        .where(
            Course.id.in_([item for item in course_ids if item is not None]),
            Course.institution_id == student.home_institution_id,
            Course.source_type.in_(REAL_SOURCES),
        )
        .order_by(Course.subject_code, Course.course_number, Course.id)
    ):
        result.courses.append(
            WorkflowCourse(
                id=course.id,
                code=f"{course.subject_code} {course.course_number}",
                title=course.title,
                credits=course.credits_min,
                source=source_metadata(course),
            )
        )
    for term in db.scalars(
        select(AcademicTerm)
        .where(
            AcademicTerm.id.in_([item for item in term_ids if item is not None]),
            AcademicTerm.institution_id == student.home_institution_id,
            AcademicTerm.source_type.in_(REAL_SOURCES),
        )
        .order_by(AcademicTerm.starts_on, AcademicTerm.term_code)
    ):
        result.terms.append(
            WorkflowTerm(
                id=term.id,
                code=term.term_code,
                starts_on=term.starts_on,
                ends_on=term.ends_on,
                source=source_metadata(term),
            )
        )
    snapshot = active_course_state_snapshot(db, student.id)
    if snapshot is not None:
        for state in db.scalars(
            select(CourseStateRecord)
            .where(
                CourseStateRecord.snapshot_id == snapshot.id,
                CourseStateRecord.student_course_attempt_id.is_(None),
            )
            .order_by(CourseStateRecord.id)
        ):
            result.issues.append(
                WorkflowIssue(
                    reason_code="COURSE_MAPPING_REVIEW_REQUIRED",
                    message=(
                        f"{state.normalized_course_code} 尚未形成可靠修读记录，"
                        "请在数据审核中核对身份和异常。"
                    ),
                    evidence_reference=f"data-import://{snapshot.data_import_run_id}/records/{state.imported_record_id}",
                )
            )
    for missing, code, message in (
        (
            not result.programs,
            "REVIEWED_PROGRAM_MISSING",
            "尚无适用于当前学生的已审核专业及 Catalog 年份，请完成培养方案映射与规则审核。",
        ),
        (
            not result.courses,
            "APPLIED_COURSES_MISSING",
            "尚无已审核应用的课程，请先导入 Catalog 并审核，再应用修读历史。",
        ),
        (
            not result.terms,
            "APPLIED_TERMS_MISSING",
            "尚无可靠学期，请导入并审核包含明确学期的修读历史或课节。",
        ),
    ):
        if missing:
            result.issues.append(WorkflowIssue(reason_code=code, message=message))
    result.revision = hashlib.sha256(result.model_dump_json().encode()).hexdigest()
    return result
