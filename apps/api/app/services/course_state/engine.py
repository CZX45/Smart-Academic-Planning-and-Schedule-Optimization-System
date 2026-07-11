from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.academic import (
    AcademicProgram,
    AcademicTerm,
    AppliedImportAction,
    AppliedImportStatus,
    AppliedImportTargetEntityType,
    Course,
    CourseStateRecord,
    CourseStateSnapshot,
    CourseStateStatus,
    CourseStateValidationState,
    DataApplicationRun,
    DataImportReviewSession,
    DataImportRun,
    ImportedRecord,
    ImportedRecordReview,
    ImportMappingCandidate,
    ImportTargetEntityType,
    ProgramVersion,
    SourceType,
    StudentAcademicProgram,
    StudentAcademicProgramStatus,
    StudentCourseAttempt,
    StudentCourseAttemptStatus,
)

MYPROGRESS_PAGE_TYPE = "KEAN_MY_PROGRESS_PAGE"
RELIABLE_ATTEMPT_STATUSES = {
    CourseStateStatus.COMPLETED,
    CourseStateStatus.IN_PROGRESS,
    CourseStateStatus.PLANNED,
}


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True)
class CourseStateApplicationOutcome:
    target_entity_type: AppliedImportTargetEntityType
    target_entity_id: UUID | None
    action: AppliedImportAction
    status: AppliedImportStatus
    reason_code: str
    message: str


def active_course_state_snapshot(
    db: Session,
    student_profile_id: UUID,
) -> CourseStateSnapshot | None:
    return db.scalar(
        select(CourseStateSnapshot)
        .where(
            CourseStateSnapshot.student_profile_id == student_profile_id,
            CourseStateSnapshot.is_active.is_(True),
        )
        .order_by(CourseStateSnapshot.applied_at.desc(), CourseStateSnapshot.id.desc())
    )


def effective_student_course_attempts(
    db: Session,
    student_profile_id: UUID,
    *,
    course_id: UUID | None = None,
    statuses: set[StudentCourseAttemptStatus] | None = None,
) -> list[StudentCourseAttempt]:
    snapshot = active_course_state_snapshot(db, student_profile_id)
    statement = select(StudentCourseAttempt).where(
        StudentCourseAttempt.student_profile_id == student_profile_id
    )
    if snapshot is not None:
        statement = statement.where(
            or_(
                StudentCourseAttempt.course_state_snapshot_id == snapshot.id,
                (
                    StudentCourseAttempt.course_state_snapshot_id.is_(None)
                    & (StudentCourseAttempt.source_type != SourceType.MOCK)
                ),
            )
        )
    if course_id is not None:
        statement = statement.where(StudentCourseAttempt.course_id == course_id)
    if statuses:
        statement = statement.where(StudentCourseAttempt.status.in_(statuses))
    return list(
        db.scalars(
            statement.order_by(
                StudentCourseAttempt.course_id,
                StudentCourseAttempt.attempt_number.desc(),
                StudentCourseAttempt.id,
            )
        ).all()
    )


class CourseStateApplicationService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def snapshot_for_import(self, data_import_run_id: UUID) -> CourseStateSnapshot | None:
        return self._db.scalar(
            select(CourseStateSnapshot).where(
                CourseStateSnapshot.data_import_run_id == data_import_run_id
            )
        )

    def prepare_snapshot(
        self,
        *,
        review: DataImportReviewSession,
        run: DataImportRun,
        application: DataApplicationRun,
    ) -> tuple[CourseStateSnapshot | None, bool]:
        existing = self.snapshot_for_import(run.id)
        if existing is not None:
            return existing, True
        summary_record = self._myprogress_summary_record(run.id)
        if summary_record is None:
            return None, False
        payload = summary_record.normalized_payload
        validation = payload.get("validation")
        validation_payload = validation if isinstance(validation, dict) else {}
        validation_state = str(validation_payload.get("status") or "MISSING")
        if validation_state != "AUTO_VERIFIED":
            return None, False
        snapshot = CourseStateSnapshot(
            id=uuid4(),
            student_profile_id=review.student_profile_id,
            data_import_run_id=run.id,
            review_session_id=review.id,
            data_application_run_id=application.id,
            source_page_type=MYPROGRESS_PAGE_TYPE,
            source_validation_state=validation_state,
            program_mapping_state=self._program_mapping_state(review.student_profile_id, payload),
            is_active=False,
            is_advisory=True,
            official_application_ready=False,
            extraction_bounded=bool(payload.get("extractionBounded")),
            extraction_truncated=bool(payload.get("extractionTruncated")),
            completed_count=0,
            in_progress_count=0,
            planned_count=0,
            not_started_count=0,
            matched_count=0,
            unmatched_count=0,
            exception_count=0,
            program_summary=self._dict_value(payload.get("programSummary")),
            credit_summary=self._dict_value(payload.get("creditSummary")),
            requirement_summary=self._requirement_summaries(run.id),
            readiness_payload={},
            applied_at=utc_now(),
            source_type=run.source_type,
            is_official=False,
            source_reference=(
                "Reviewed MyProgress internal planning snapshot; "
                f"data_import_run={run.id}; review_session={review.id}; "
                f"data_application_run={application.id}"
            ),
            source_retrieved_at=run.source_retrieved_at,
            source_confidence=run.source_confidence,
        )
        self._db.add(snapshot)
        self._db.flush()
        return snapshot, False

    def dry_run_outcome(
        self,
        record_review: ImportedRecordReview,
        record: ImportedRecord,
    ) -> CourseStateApplicationOutcome | None:
        if not self._is_course_state_record(record):
            return None
        payload = self._review_payload(record_review, record)
        status = self._course_state_status(payload)
        reason_codes = self._string_list(self._row_validation(payload).get("reason_codes"))
        if reason_codes or status is CourseStateStatus.UNKNOWN:
            return self._outcome(
                None,
                AppliedImportStatus.WARNING,
                "COURSE_STATE_EXCEPTION",
                "Dry run would preserve this row as an exception outside reliable course history.",
            )
        if status is CourseStateStatus.NOT_STARTED:
            return self._outcome(
                None,
                AppliedImportStatus.SUCCESS,
                "WOULD_APPLY_NOT_STARTED_REQUIREMENT_OPTION",
                "Dry run would preserve NOT_STARTED as requirement context without an attempt.",
            )
        candidate = self._selected_candidate(record_review)
        if candidate is None or candidate.target_entity_id is None:
            return self._outcome(
                None,
                AppliedImportStatus.WARNING,
                "WOULD_APPLY_UNMATCHED_EXTERNAL_EVIDENCE",
                "Dry run would preserve this unmatched course as external evidence only.",
            )
        return self._outcome(
            None,
            AppliedImportStatus.SUCCESS,
            "WOULD_APPLY_COURSE_STATE",
            "Dry run would create a non-official internal course-state record.",
        )

    def apply_record(
        self,
        *,
        snapshot: CourseStateSnapshot,
        review: DataImportReviewSession,
        run: DataImportRun,
        record_review: ImportedRecordReview,
        record: ImportedRecord,
    ) -> CourseStateApplicationOutcome | None:
        if not self._is_course_state_record(record):
            return None
        existing = self._db.scalar(
            select(CourseStateRecord).where(
                CourseStateRecord.snapshot_id == snapshot.id,
                CourseStateRecord.imported_record_id == record.id,
            )
        )
        if existing is not None:
            return CourseStateApplicationOutcome(
                target_entity_type=AppliedImportTargetEntityType.COURSE_STATE,
                target_entity_id=existing.id,
                action=AppliedImportAction.SKIPPED_DUPLICATE,
                status=AppliedImportStatus.SKIPPED,
                reason_code="ALREADY_APPLIED_COURSE_STATE",
                message="This imported row already exists in the idempotent course-state snapshot.",
            )

        payload = self._review_payload(record_review, record)
        status = self._course_state_status(payload)
        course_code = str(payload.get("course_code") or "").strip()
        title = str(payload.get("title") or "").strip()
        term_code = str(payload.get("term") or "").strip()
        grade = str(payload.get("grade") or "").strip().upper() or None
        credits = self._credits(payload.get("credits"))
        validation_payload = self._row_validation(payload)
        reason_codes = self._string_list(validation_payload.get("reason_codes"))
        warnings = [
            *self._string_list(validation_payload.get("warnings")),
            *self._string_list(payload.get("row_warnings")),
        ]
        candidate = self._selected_candidate(record_review)
        matched_course = self._matched_course(candidate)
        prior_states = self._same_course_states(snapshot.id, course_code)
        conflict = any(
            state.status is not status or (state.term or "") != term_code for state in prior_states
        )
        duplicate = bool(prior_states) and not conflict
        if conflict:
            reason_codes.append("CONFLICTING_COURSE_STATUS")
            self._invalidate_conflicting_states(prior_states)
        elif duplicate:
            warnings.append("DUPLICATE_SOURCE_ROW")

        validation_state = CourseStateValidationState.RELIABLE
        application_reason_code = "APPLIED_COURSE_STATE"
        attempt: StudentCourseAttempt | None = None
        if reason_codes or status is CourseStateStatus.UNKNOWN or conflict:
            validation_state = CourseStateValidationState.EXCEPTION
            application_reason_code = "COURSE_STATE_EXCEPTION"
        elif duplicate:
            validation_state = CourseStateValidationState.RELIABLE_WITH_WARNINGS
            application_reason_code = "DUPLICATE_SOURCE_ROW"
        elif status is CourseStateStatus.NOT_STARTED:
            application_reason_code = "NOT_STARTED_REQUIREMENT_OPTION"
            if matched_course is None:
                validation_state = CourseStateValidationState.EXTERNAL_EVIDENCE
                warnings.append("COURSE_CODE_UNMATCHED")
        elif matched_course is None:
            validation_state = CourseStateValidationState.EXTERNAL_EVIDENCE
            application_reason_code = "UNMATCHED_EXTERNAL_EVIDENCE"
            warnings.append("COURSE_CODE_UNMATCHED")
        else:
            term = self._matched_term(matched_course, term_code)
            if term is None:
                validation_state = CourseStateValidationState.EXTERNAL_EVIDENCE
                application_reason_code = "TERM_UNKNOWN"
                warnings.append("TERM_UNKNOWN")
            elif credits is None:
                validation_state = CourseStateValidationState.EXTERNAL_EVIDENCE
                application_reason_code = "CREDITS_UNKNOWN"
                warnings.append("CREDITS_UNKNOWN")
            elif status is CourseStateStatus.COMPLETED and grade in {"F", "U", "W", "WF", "I"}:
                validation_state = CourseStateValidationState.EXCEPTION
                application_reason_code = "CONFLICTING_COURSE_STATUS"
                reason_codes.append("COMPLETED_STATUS_WITH_NONPASSING_GRADE")
            else:
                attempt = self._create_attempt(
                    snapshot=snapshot,
                    review=review,
                    run=run,
                    record=record,
                    course=matched_course,
                    term=term,
                    status=status,
                    grade=grade,
                    credits=credits,
                    source_table_index=str(payload.get("source_table_index") or "") or None,
                    source_row_index=str(payload.get("source_row_index") or "") or None,
                )
                if warnings:
                    validation_state = CourseStateValidationState.RELIABLE_WITH_WARNINGS

        state = CourseStateRecord(
            id=uuid4(),
            snapshot_id=snapshot.id,
            imported_record_id=record.id,
            imported_record_review_id=record_review.id,
            matched_course_id=matched_course.id if matched_course is not None else None,
            student_course_attempt_id=attempt.id if attempt is not None else None,
            normalized_course_code=course_code,
            source_course_code=course_code,
            source_course_title=title,
            status=status,
            term=term_code or None,
            credits=credits,
            grade=grade,
            requirement_context=str(payload.get("requirement_group_context") or "") or None,
            source_page_type=MYPROGRESS_PAGE_TYPE,
            source_table_index=str(payload.get("source_table_index") or "") or None,
            source_row_index=str(payload.get("source_row_index") or "") or None,
            provenance=self._dict_value(payload.get("source_field_provenance")),
            confidence_score=record.confidence_score,
            validation_state=validation_state,
            review_decision=record_review.decision,
            application_reason_code=application_reason_code,
            reason_codes=list(dict.fromkeys(reason_codes)),
            warnings=list(dict.fromkeys(warnings)),
        )
        self._db.add(state)
        self._db.flush()
        outcome_status = (
            AppliedImportStatus.SUCCESS
            if validation_state
            in {
                CourseStateValidationState.RELIABLE,
                CourseStateValidationState.RELIABLE_WITH_WARNINGS,
            }
            else AppliedImportStatus.WARNING
        )
        return CourseStateApplicationOutcome(
            target_entity_type=AppliedImportTargetEntityType.COURSE_STATE,
            target_entity_id=state.id,
            action=AppliedImportAction.CREATED,
            status=outcome_status,
            reason_code=application_reason_code,
            message=self._application_message(application_reason_code),
        )

    def finalize_snapshot(self, snapshot: CourseStateSnapshot) -> CourseStateSnapshot:
        states = list(
            self._db.scalars(
                select(CourseStateRecord)
                .where(CourseStateRecord.snapshot_id == snapshot.id)
                .order_by(CourseStateRecord.created_at, CourseStateRecord.id)
            ).all()
        )
        snapshot.completed_count = sum(
            1 for state in states if state.status is CourseStateStatus.COMPLETED
        )
        snapshot.in_progress_count = sum(
            1 for state in states if state.status is CourseStateStatus.IN_PROGRESS
        )
        snapshot.planned_count = sum(
            1 for state in states if state.status is CourseStateStatus.PLANNED
        )
        snapshot.not_started_count = sum(
            1 for state in states if state.status is CourseStateStatus.NOT_STARTED
        )
        snapshot.matched_count = sum(1 for state in states if state.matched_course_id is not None)
        snapshot.unmatched_count = sum(1 for state in states if state.matched_course_id is None)
        applied_exception_count = sum(
            1 for state in states if state.validation_state is CourseStateValidationState.EXCEPTION
        )
        source_records = self._db.scalars(
            select(ImportedRecord).where(
                ImportedRecord.data_import_run_id == snapshot.data_import_run_id
            )
        ).all()
        source_exception_count = sum(
            1
            for record in source_records
            if record.normalized_payload.get("record_kind") == "MY_PROGRESS_COURSE_ROW"
            and bool(
                self._string_list(
                    self._row_validation(record.normalized_payload).get("reason_codes")
                )
            )
        )
        snapshot.exception_count = max(applied_exception_count, source_exception_count)
        snapshot.readiness_payload = self._readiness(snapshot, states)
        can_activate = snapshot.source_validation_state == "AUTO_VERIFIED" and any(
            state.student_course_attempt_id is not None for state in states
        )
        if can_activate:
            current = active_course_state_snapshot(self._db, snapshot.student_profile_id)
            if current is not None and current.id != snapshot.id:
                current.is_active = False
                # PostgreSQL enforces one active snapshot with a partial unique index.
                # Flush the deactivation before activating its replacement; both writes
                # remain inside the caller's transaction and roll back together.
                self._db.flush([current])
            snapshot.is_active = True
        self._db.flush()
        return snapshot

    def _readiness(
        self,
        snapshot: CourseStateSnapshot,
        states: list[CourseStateRecord],
    ) -> dict[str, object]:
        reliable_attempts = [
            state for state in states if state.student_course_attempt_id is not None
        ]
        prerequisite_evidence = [
            state
            for state in reliable_attempts
            if state.status in {CourseStateStatus.COMPLETED, CourseStateStatus.IN_PROGRESS}
        ]
        common_warnings = [
            *(
                ["SOURCE_BOUNDED_OR_TRUNCATED"]
                if snapshot.extraction_bounded or snapshot.extraction_truncated
                else []
            ),
            *(["COURSE_CODE_UNMATCHED"] if snapshot.unmatched_count else []),
            *(["COURSE_STATE_EXCEPTIONS_PRESENT"] if snapshot.exception_count else []),
        ]
        summary_ready = bool(snapshot.program_summary and snapshot.credit_summary)
        requirements_ready = bool(snapshot.requirement_summary)
        course_history_status = (
            "READY_WITH_WARNINGS"
            if reliable_attempts and common_warnings
            else "READY"
            if reliable_attempts
            else "PARTIAL"
            if states
            else "MISSING"
        )
        degree_reasons: list[str] = []
        if snapshot.program_mapping_state != "EXACT":
            degree_reasons.append("PROGRAM_VERSION_UNMATCHED")
        if not requirements_ready:
            degree_reasons.append("REQUIREMENT_TREE_INCOMPLETE")
        if not reliable_attempts:
            degree_reasons.append("COURSE_HISTORY_NOT_RELIABLE")
        eligibility_reasons = (
            [] if prerequisite_evidence else ["RELIABLE_PREREQUISITE_EVIDENCE_MISSING"]
        )
        if snapshot.unmatched_count:
            eligibility_reasons.append("UNMATCHED_COURSES_LIMIT_ELIGIBILITY")
        planner_reasons = [*degree_reasons]
        if snapshot.extraction_bounded or snapshot.extraction_truncated:
            planner_reasons.append("SOURCE_BOUNDED_OR_TRUNCATED")
        if snapshot.exception_count:
            planner_reasons.append("CRITICAL_COURSE_STATE_EXCEPTIONS")
        base = {
            "source_import_id": str(snapshot.data_import_run_id),
            "source_validation_state": snapshot.source_validation_state,
            "source_bounded": snapshot.extraction_bounded,
            "source_truncated": snapshot.extraction_truncated,
            "last_applied_at": snapshot.applied_at.isoformat(),
        }

        def item(
            status: str,
            *,
            reason_codes: list[str] | None = None,
            blocking_reasons: list[str] | None = None,
            warnings: list[str] | None = None,
        ) -> dict[str, object]:
            return {
                "status": status,
                "reason_codes": list(dict.fromkeys(reason_codes or [])),
                "blocking_reasons": list(dict.fromkeys(blocking_reasons or [])),
                "warnings": list(dict.fromkeys(warnings or [])),
                **base,
            }

        return {
            "summary": item(
                "READY" if summary_ready else "NEEDS_REVIEW",
                blocking_reasons=[] if summary_ready else ["SUMMARY_FIELDS_INCOMPLETE"],
            ),
            "requirement_summary": item(
                "READY_WITH_WARNINGS"
                if requirements_ready and common_warnings
                else "READY"
                if requirements_ready
                else "MISSING",
                blocking_reasons=[] if requirements_ready else ["REQUIREMENT_TREE_INCOMPLETE"],
                warnings=common_warnings,
            ),
            "course_history": item(
                course_history_status,
                reason_codes=common_warnings,
                blocking_reasons=[] if reliable_attempts else ["NO_CATALOG_MATCHED_COURSE_HISTORY"],
                warnings=common_warnings,
            ),
            "degree_audit": item(
                "READY_WITH_WARNINGS"
                if not degree_reasons and common_warnings
                else "READY"
                if not degree_reasons
                else "BLOCKED",
                blocking_reasons=degree_reasons,
                warnings=common_warnings,
            ),
            "course_eligibility": item(
                "READY_WITH_WARNINGS" if prerequisite_evidence else "BLOCKED",
                blocking_reasons=[] if prerequisite_evidence else eligibility_reasons,
                warnings=eligibility_reasons if prerequisite_evidence else common_warnings,
            ),
            "long_term_planner": item(
                "READY_WITH_WARNINGS" if not planner_reasons else "BLOCKED",
                blocking_reasons=planner_reasons,
                warnings=common_warnings,
            ),
            "semester_schedule": item(
                "DEMO_ONLY",
                blocking_reasons=["REAL_SECTION_SEARCH_DATA_NOT_IMPORTED"],
            ),
        }

    def _myprogress_summary_record(self, run_id: UUID) -> ImportedRecord | None:
        return self._db.scalar(
            select(ImportedRecord)
            .where(ImportedRecord.data_import_run_id == run_id)
            .order_by(ImportedRecord.row_number, ImportedRecord.id)
        )

    def _requirement_summaries(self, run_id: UUID) -> list[object]:
        records = self._db.scalars(
            select(ImportedRecord)
            .where(ImportedRecord.data_import_run_id == run_id)
            .order_by(ImportedRecord.row_number, ImportedRecord.id)
        ).all()
        return [
            record.normalized_payload["requirementGroup"]
            for record in records
            if record.normalized_payload.get("record_kind") == "MY_PROGRESS_REQUIREMENT_GROUP"
            and "requirementGroup" in record.normalized_payload
        ]

    def _program_mapping_state(
        self,
        student_profile_id: UUID,
        payload: dict[str, object],
    ) -> str:
        summary = self._dict_value(payload.get("programSummary"))
        source_name = str(summary.get("programName") or "").strip().casefold()
        source_catalog = str(summary.get("catalogYear") or "").strip()
        rows = self._db.execute(
            select(AcademicProgram, ProgramVersion)
            .join(ProgramVersion, ProgramVersion.program_id == AcademicProgram.id)
            .join(
                StudentAcademicProgram,
                StudentAcademicProgram.program_version_id == ProgramVersion.id,
            )
            .where(
                StudentAcademicProgram.student_profile_id == student_profile_id,
                StudentAcademicProgram.status == StudentAcademicProgramStatus.ACTIVE,
            )
        ).all()
        for program, version in rows:
            if (
                program.name.strip().casefold() == source_name
                and version.catalog_year == source_catalog
            ):
                return "EXACT"
        return "UNMATCHED"

    def _is_course_state_record(self, record: ImportedRecord) -> bool:
        return record.normalized_payload.get("record_kind") == "MY_PROGRESS_COURSE_ROW"

    def _review_payload(
        self,
        record_review: ImportedRecordReview,
        record: ImportedRecord,
    ) -> dict[str, object]:
        if record_review.edited_normalized_payload is None:
            return dict(record.normalized_payload)
        return {**record.normalized_payload, **record_review.edited_normalized_payload}

    def _selected_candidate(
        self,
        record_review: ImportedRecordReview,
    ) -> ImportMappingCandidate | None:
        if record_review.selected_mapping_candidate_id is not None:
            return self._db.get(ImportMappingCandidate, record_review.selected_mapping_candidate_id)
        return self._db.scalar(
            select(ImportMappingCandidate)
            .where(ImportMappingCandidate.imported_record_id == record_review.imported_record_id)
            .order_by(
                ImportMappingCandidate.is_selected.desc(),
                ImportMappingCandidate.confidence_score.desc(),
                ImportMappingCandidate.id,
            )
        )

    def _matched_course(self, candidate: ImportMappingCandidate | None) -> Course | None:
        if (
            candidate is None
            or candidate.target_entity_type is not ImportTargetEntityType.COURSE
            or candidate.target_entity_id is None
        ):
            return None
        return self._db.get(Course, candidate.target_entity_id)

    def _matched_term(self, course: Course, term_code: str) -> AcademicTerm | None:
        if not term_code:
            return None
        return self._db.scalar(
            select(AcademicTerm).where(
                AcademicTerm.institution_id == course.institution_id,
                AcademicTerm.term_code == term_code,
            )
        )

    def _create_attempt(
        self,
        *,
        snapshot: CourseStateSnapshot,
        review: DataImportReviewSession,
        run: DataImportRun,
        record: ImportedRecord,
        course: Course,
        term: AcademicTerm,
        status: CourseStateStatus,
        grade: str | None,
        credits: Decimal,
        source_table_index: str | None,
        source_row_index: str | None,
    ) -> StudentCourseAttempt:
        attempt_status = StudentCourseAttemptStatus(status.value)
        current_max = self._db.scalar(
            select(func.max(StudentCourseAttempt.attempt_number)).where(
                StudentCourseAttempt.student_profile_id == review.student_profile_id,
                StudentCourseAttempt.course_id == course.id,
            )
        )
        attempt = StudentCourseAttempt(
            id=uuid4(),
            student_profile_id=review.student_profile_id,
            course_id=course.id,
            term_id=term.id,
            course_state_snapshot_id=snapshot.id,
            attempt_number=int(current_max or 0) + 1,
            status=attempt_status,
            grade=grade,
            credits_attempted=credits,
            credits_earned=credits
            if attempt_status is StudentCourseAttemptStatus.COMPLETED
            else Decimal("0"),
            is_repeat=bool(current_max),
            source_type=run.source_type,
            is_official=False,
            source_reference=(
                "Reviewed MyProgress internal course-state evidence; "
                f"snapshot={snapshot.id}; import={run.id}; record={record.id}; "
                f"source_table_index={source_table_index or 'unknown'}; "
                f"source_row_index={source_row_index or 'unknown'}"
            ),
            source_retrieved_at=run.source_retrieved_at,
            source_confidence=str(record.confidence_score),
        )
        self._db.add(attempt)
        self._db.flush()
        return attempt

    def _same_course_states(self, snapshot_id: UUID, course_code: str) -> list[CourseStateRecord]:
        if not course_code:
            return []
        return list(
            self._db.scalars(
                select(CourseStateRecord).where(
                    CourseStateRecord.snapshot_id == snapshot_id,
                    CourseStateRecord.normalized_course_code == course_code,
                )
            ).all()
        )

    def _invalidate_conflicting_states(self, states: list[CourseStateRecord]) -> None:
        for state in states:
            if state.student_course_attempt_id is not None:
                attempt = self._db.get(StudentCourseAttempt, state.student_course_attempt_id)
                if attempt is not None:
                    self._db.delete(attempt)
                state.student_course_attempt_id = None
            state.validation_state = CourseStateValidationState.EXCEPTION
            state.application_reason_code = "CONFLICTING_COURSE_STATUS"
            state.reason_codes = list(
                dict.fromkeys([*self._string_list(state.reason_codes), "CONFLICTING_COURSE_STATUS"])
            )

    def _course_state_status(self, payload: dict[str, object]) -> CourseStateStatus:
        try:
            return CourseStateStatus(str(payload.get("status") or "UNKNOWN"))
        except ValueError:
            return CourseStateStatus.UNKNOWN

    def _credits(self, value: object) -> Decimal | None:
        try:
            credits = Decimal(str(value or "").strip())
        except (InvalidOperation, ValueError):
            return None
        return credits if credits >= 0 else None

    def _row_validation(self, payload: dict[str, object]) -> dict[str, object]:
        return self._dict_value(payload.get("row_validation"))

    def _dict_value(self, value: object) -> dict[str, object]:
        return dict(value) if isinstance(value, dict) else {}

    def _string_list(self, value: object) -> list[str]:
        return [str(item) for item in value] if isinstance(value, list) else []

    def _outcome(
        self,
        target_entity_id: UUID | None,
        status: AppliedImportStatus,
        reason_code: str,
        message: str,
    ) -> CourseStateApplicationOutcome:
        return CourseStateApplicationOutcome(
            target_entity_type=AppliedImportTargetEntityType.COURSE_STATE,
            target_entity_id=target_entity_id,
            action=AppliedImportAction.CREATED,
            status=status,
            reason_code=reason_code,
            message=message,
        )

    def _application_message(self, reason_code: str) -> str:
        messages = {
            "APPLIED_COURSE_STATE": (
                "Applied a reviewed row to the non-official internal course-state snapshot."
            ),
            "NOT_STARTED_REQUIREMENT_OPTION": (
                "Preserved NOT_STARTED as unmet requirement context without creating an attempt."
            ),
            "UNMATCHED_EXTERNAL_EVIDENCE": (
                "Preserved the unmatched course as external evidence without fabricating "
                "a catalog link."
            ),
            "TERM_UNKNOWN": (
                "Preserved the course state, but did not create reliable history because "
                "the term is unmatched."
            ),
            "CREDITS_UNKNOWN": (
                "Preserved the course state, but did not create reliable history because "
                "credits are missing."
            ),
            "COURSE_STATE_EXCEPTION": (
                "Preserved the row as a traceable exception outside reliable course history."
            ),
            "CONFLICTING_COURSE_STATUS": (
                "Conflicting rows were retained as exceptions and excluded from reliable "
                "course history."
            ),
            "DUPLICATE_SOURCE_ROW": (
                "Preserved a duplicate source row without creating another course attempt."
            ),
        }
        return messages.get(reason_code, "Preserved reviewed MyProgress course-state evidence.")
