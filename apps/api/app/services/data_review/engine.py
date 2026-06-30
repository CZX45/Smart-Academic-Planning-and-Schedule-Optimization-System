from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.academic import (
    AcademicTerm,
    AppliedImportAction,
    AppliedImportedRecord,
    AppliedImportStatus,
    AppliedImportTargetEntityType,
    AuditWarningSeverity,
    Course,
    DataApplicationRun,
    DataApplicationStatus,
    DataImportReviewSession,
    DataImportReviewStatus,
    DataImportRun,
    DataReviewWarning,
    ImportedRecord,
    ImportedRecordReview,
    ImportedRecordReviewDecision,
    ImportedRecordStatus,
    ImportedRecordType,
    ImportMappingCandidate,
    ImportTargetEntityType,
    ImportValidationWarning,
    SourceType,
    StudentCourseAttempt,
    StudentCourseAttemptStatus,
)
from app.services.data_review.exceptions import DataReviewValidationError
from app.services.data_review.result import (
    AppliedImportedRecordResult,
    DataReviewApplicationResult,
)

ACTIVE_REVIEW_STATUSES = {
    DataImportReviewStatus.DRAFT,
    DataImportReviewStatus.IN_REVIEW,
    DataImportReviewStatus.READY_TO_APPLY,
    DataImportReviewStatus.APPLYING,
}
APPLY_DECISIONS = {
    ImportedRecordReviewDecision.CONFIRMED,
    ImportedRecordReviewDecision.EDITED_AND_CONFIRMED,
}
SUPPORTED_GRADES = {
    "",
    "A+",
    "A",
    "A-",
    "B+",
    "B",
    "B-",
    "C+",
    "C",
    "C-",
    "D+",
    "D",
    "D-",
    "F",
    "P",
    "S",
    "U",
    "W",
    "WF",
    "I",
}


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class DataReviewApplicationService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_review_session(
        self,
        *,
        data_import_run_id: UUID,
        reviewer_label: str,
    ) -> DataImportReviewSession:
        run = self._get_run(data_import_run_id)
        if not reviewer_label.strip():
            raise DataReviewValidationError("invalid_reviewer", "reviewer_label cannot be empty.")
        existing = self._db.scalar(
            select(DataImportReviewSession).where(
                DataImportReviewSession.data_import_run_id == run.id,
                DataImportReviewSession.status.in_(ACTIVE_REVIEW_STATUSES),
            )
        )
        if existing is not None:
            raise DataReviewValidationError(
                "active_review_exists",
                "An active review session already exists for this data import run.",
            )

        review = DataImportReviewSession(
            id=uuid4(),
            data_import_run_id=run.id,
            student_profile_id=run.student_profile_id,
            status=DataImportReviewStatus.IN_REVIEW,
            reviewer_label=reviewer_label.strip(),
            started_at=utc_now(),
        )
        self._db.add(review)
        self._db.flush()

        record_reviews_by_record_id: dict[UUID, ImportedRecordReview] = {}
        records = self._db.scalars(
            select(ImportedRecord)
            .where(ImportedRecord.data_import_run_id == run.id)
            .order_by(ImportedRecord.row_number, ImportedRecord.id)
        ).all()
        for record in records:
            candidate = self._selected_candidate(record.id)
            requires_advisor_confirmation = self._record_requires_advisor_review(
                record,
                candidate,
            )
            record_review = ImportedRecordReview(
                id=uuid4(),
                review_session_id=review.id,
                imported_record_id=record.id,
                selected_mapping_candidate_id=candidate.id if candidate is not None else None,
                decision=ImportedRecordReviewDecision.UNREVIEWED,
                edited_normalized_payload=None,
                review_note=None,
                requires_advisor_confirmation=requires_advisor_confirmation,
            )
            self._db.add(record_review)
            self._db.flush()
            record_reviews_by_record_id[record.id] = record_review
            if requires_advisor_confirmation:
                self._add_warning(
                    review.id,
                    record_review.id,
                    None,
                    "RECORD_REQUIRES_REVIEW",
                    AuditWarningSeverity.WARNING,
                    (
                        f"Imported row {record.row_number} is ambiguous, unsupported, "
                        "or lacks a safe mapping and needs human confirmation."
                    ),
                    True,
                )

        self._add_warning(
            review.id,
            None,
            None,
            "STAGING_ONLY_NOT_OFFICIAL",
            AuditWarningSeverity.WARNING,
            (
                "Phase 7B review applies only to internal planning records. Imported data remains "
                "unofficial until the school or advisor confirms it."
            ),
            True,
        )
        self._copy_import_warnings(review.id, record_reviews_by_record_id)
        self._db.commit()
        self._db.refresh(review)
        return review

    def update_record_review(
        self,
        *,
        review_session_id: UUID,
        record_review_id: UUID,
        decision: ImportedRecordReviewDecision,
        selected_mapping_candidate_id: UUID | None = None,
        edited_normalized_payload: dict[str, object] | None = None,
        review_note: str | None = None,
        requires_advisor_confirmation: bool | None = None,
    ) -> ImportedRecordReview:
        review = self._get_review(review_session_id)
        record_review = self._get_record_review(review.id, record_review_id)
        record = self._get_imported_record(record_review.imported_record_id)

        candidate = self._candidate_for_review(record_review, selected_mapping_candidate_id)
        if (
            decision is ImportedRecordReviewDecision.EDITED_AND_CONFIRMED
            and not edited_normalized_payload
        ):
            raise DataReviewValidationError(
                "missing_edited_payload",
                "EDITED_AND_CONFIRMED requires edited_normalized_payload.",
            )

        record_review.selected_mapping_candidate_id = (
            candidate.id if candidate is not None else None
        )
        record_review.decision = decision
        record_review.edited_normalized_payload = edited_normalized_payload
        record_review.review_note = review_note
        record_review.requires_advisor_confirmation = (
            decision is ImportedRecordReviewDecision.NEEDS_ADVISOR_REVIEW
            or bool(requires_advisor_confirmation)
            or self._record_requires_advisor_review(record, candidate)
        )
        if decision is ImportedRecordReviewDecision.EDITED_AND_CONFIRMED:
            self._add_warning(
                review.id,
                record_review.id,
                None,
                "EDITED_IMPORTED_RECORD",
                AuditWarningSeverity.WARNING,
                "The reviewer edited normalized import data before confirming it.",
                True,
            )
        self._sync_review_status(review)
        self._db.commit()
        self._db.refresh(record_review)
        return record_review

    def apply_review_session(
        self,
        review_session_id: UUID,
        *,
        allow_advisor_review_records: bool = False,
        dry_run: bool = False,
    ) -> DataReviewApplicationResult:
        review = self._get_review(review_session_id)
        run = self._get_run(review.data_import_run_id)
        record_reviews = self._record_reviews_for_application(review.id)

        if dry_run:
            dry_run_records = [
                self._build_application_result(
                    review,
                    run,
                    record_review,
                    allow_advisor_review_records=allow_advisor_review_records,
                    application_id=None,
                    dry_run=True,
                )
                for record_review in record_reviews
            ]
            warnings = self._review_warnings(review.id)
            return DataReviewApplicationResult(
                review_session=review,
                dry_run=True,
                application=None,
                applied_records=dry_run_records,
                warnings=warnings,
            )

        application = DataApplicationRun(
            id=uuid4(),
            review_session_id=review.id,
            status=DataApplicationStatus.APPLYING,
            applied_count=0,
            skipped_count=0,
            warning_count=0,
            error_count=0,
            started_at=utc_now(),
        )
        review.status = DataImportReviewStatus.APPLYING
        self._db.add(application)
        self._db.flush()

        results: list[AppliedImportedRecordResult] = []
        for record_review in record_reviews:
            result = self._build_application_result(
                review,
                run,
                record_review,
                allow_advisor_review_records=allow_advisor_review_records,
                application_id=application.id,
                dry_run=False,
            )
            applied_row = AppliedImportedRecord(
                id=uuid4(),
                data_application_run_id=application.id,
                imported_record_review_id=result.imported_record_review_id,
                imported_record_id=result.imported_record_id,
                target_entity_type=result.target_entity_type,
                target_entity_id=result.target_entity_id,
                action=result.action,
                status=result.status,
                reason_code=result.reason_code,
                message=result.message,
            )
            self._db.add(applied_row)
            self._db.flush()
            if result.status is not AppliedImportStatus.SUCCESS:
                self._add_warning(
                    review.id,
                    record_review.id,
                    application.id,
                    result.reason_code,
                    AuditWarningSeverity.WARNING,
                    result.message,
                    result.action is AppliedImportAction.SKIPPED_ADVISOR_REVIEW,
                )
            results.append(self._result_from_row(applied_row))

        application.applied_count = sum(
            1 for result in results if result.status is AppliedImportStatus.SUCCESS
        )
        application.skipped_count = sum(
            1 for result in results if result.status is AppliedImportStatus.SKIPPED
        )
        application.warning_count = sum(
            1 for result in results if result.status is AppliedImportStatus.WARNING
        )
        application.error_count = sum(
            1 for result in results if result.status is AppliedImportStatus.FAILED
        )
        application.status = self._application_status(application)
        application.completed_at = utc_now()
        review.status = (
            DataImportReviewStatus.APPLIED
            if application.status is DataApplicationStatus.APPLIED
            else DataImportReviewStatus.APPLIED_WITH_WARNINGS
        )
        review.completed_at = application.completed_at
        self._db.commit()
        self._db.refresh(application)
        self._db.refresh(review)
        return DataReviewApplicationResult(
            review_session=review,
            dry_run=False,
            application=application,
            applied_records=results,
            warnings=self._review_warnings(review.id),
        )

    def _build_application_result(
        self,
        review: DataImportReviewSession,
        run: DataImportRun,
        record_review: ImportedRecordReview,
        *,
        allow_advisor_review_records: bool,
        application_id: UUID | None,
        dry_run: bool,
    ) -> AppliedImportedRecordResult:
        record = self._get_imported_record(record_review.imported_record_id)
        if record_review.decision is ImportedRecordReviewDecision.REJECTED:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_REJECTED,
                AppliedImportStatus.SKIPPED,
                "RECORD_REJECTED",
                "Reviewer rejected this imported record; nothing was applied.",
            )
        if record_review.decision is ImportedRecordReviewDecision.DEFERRED:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_DEFERRED,
                AppliedImportStatus.SKIPPED,
                "RECORD_DEFERRED",
                "Reviewer deferred this imported record for a later decision.",
            )
        if record_review.decision is ImportedRecordReviewDecision.UNREVIEWED:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_DEFERRED,
                AppliedImportStatus.SKIPPED,
                "RECORD_UNREVIEWED",
                "Imported record has not been confirmed, rejected, or deferred.",
            )
        if (
            record_review.decision is ImportedRecordReviewDecision.NEEDS_ADVISOR_REVIEW
            and not allow_advisor_review_records
        ):
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_ADVISOR_REVIEW,
                AppliedImportStatus.SKIPPED,
                "ADVISOR_REVIEW_REQUIRED",
                "Imported record requires advisor review before it can be applied.",
            )
        if record_review.decision not in APPLY_DECISIONS and not allow_advisor_review_records:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "UNSUPPORTED_REVIEW_DECISION",
                f"Decision {record_review.decision.value} is not applyable.",
            )
        if record.record_type is not ImportedRecordType.COURSE_ATTEMPT:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "UNSUPPORTED_TARGET_TYPE",
                (
                    f"{record.record_type.value} records are reviewable in Phase 7B "
                    "but are not automatically applied."
                ),
            )

        previous_application = self._previous_successful_application(record.id)
        if previous_application is not None:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_DUPLICATE,
                AppliedImportStatus.SKIPPED,
                "ALREADY_APPLIED_IMPORTED_RECORD",
                "This imported record was already applied by an earlier application run.",
                previous_application.target_entity_id,
            )

        candidate = self._candidate_for_review(record_review, None)
        if candidate is None or candidate.target_entity_type is not ImportTargetEntityType.COURSE:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "NO_SAFE_COURSE_MAPPING",
                "No selected course mapping was available for this imported course attempt.",
            )
        if candidate.target_entity_id is None:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "MISSING_TARGET_COURSE",
                "Selected mapping did not include a target course id.",
            )
        course = self._db.get(Course, candidate.target_entity_id)
        if course is None:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "TARGET_COURSE_NOT_FOUND",
                "Selected target course could not be found.",
            )

        payload = self._review_payload(record_review, record)
        term_code = str(payload.get("term") or "").strip()
        term = self._db.scalar(
            select(AcademicTerm).where(
                AcademicTerm.institution_id == course.institution_id,
                AcademicTerm.term_code == term_code,
            )
        )
        if term is None:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "UNMATCHED_TERM_CODE",
                f"{term_code or 'Missing term'} could not be matched to a known term.",
            )

        grade = str(payload.get("grade") or "").strip().upper()
        if grade not in SUPPORTED_GRADES:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "UNSUPPORTED_GRADE_FORMAT",
                f"Grade {grade} is not supported by Phase 7B automatic application.",
            )
        credits = self._parse_credits(payload.get("credits"))
        if credits is None:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "INVALID_CREDIT_AMOUNT",
                "Imported credit amount was missing or invalid.",
            )

        existing_attempt = self._existing_course_attempt(
            review.student_profile_id,
            course.id,
            term.id,
            grade or None,
            credits,
        )
        if existing_attempt is not None:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_DUPLICATE,
                AppliedImportStatus.SKIPPED,
                "DUPLICATE_COURSE_ATTEMPT",
                "A matching internal course attempt already exists.",
                existing_attempt.id,
            )

        if dry_run:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.CREATED,
                AppliedImportStatus.SUCCESS,
                "WOULD_CREATE_STUDENT_COURSE_ATTEMPT",
                "Dry run would create an internal student course attempt.",
            )

        next_attempt_number = self._next_attempt_number(review.student_profile_id, course.id)
        status = self._attempt_status(payload, grade)
        attempt = StudentCourseAttempt(
            id=uuid4(),
            student_profile_id=review.student_profile_id,
            course_id=course.id,
            term_id=term.id,
            attempt_number=next_attempt_number,
            status=status,
            grade=grade or None,
            credits_attempted=credits,
            credits_earned=self._credits_earned(status, grade, credits),
            is_repeat=next_attempt_number > 1,
            source_type=run.source_type,
            is_official=False,
            source_reference=(
                "Phase 7B data review applied internal planning record; "
                f"review_session={review.id}; data_import_run={run.id}; "
                f"imported_record={record.id}"
            ),
            source_retrieved_at=run.source_retrieved_at,
            source_confidence=run.source_confidence,
        )
        self._db.add(attempt)
        self._db.flush()
        return self._outcome(
            application_id,
            record_review,
            AppliedImportAction.CREATED,
            AppliedImportStatus.SUCCESS,
            "CREATED_STUDENT_COURSE_ATTEMPT",
            "Created an internal student course attempt from a confirmed imported record.",
            attempt.id,
        )

    def _record_requires_advisor_review(
        self,
        record: ImportedRecord,
        candidate: ImportMappingCandidate | None,
    ) -> bool:
        if record.status not in {
            ImportedRecordStatus.VALID,
            ImportedRecordStatus.VALID_WITH_WARNINGS,
        }:
            return True
        if candidate is None:
            return True
        return candidate.target_entity_type is ImportTargetEntityType.UNKNOWN

    def _sync_review_status(self, review: DataImportReviewSession) -> None:
        unreviewed_count = (
            self._db.scalar(
                select(func.count())
                .select_from(ImportedRecordReview)
                .where(
                    ImportedRecordReview.review_session_id == review.id,
                    ImportedRecordReview.decision == ImportedRecordReviewDecision.UNREVIEWED,
                )
            )
            or 0
        )
        applyable_count = (
            self._db.scalar(
                select(func.count())
                .select_from(ImportedRecordReview)
                .where(
                    ImportedRecordReview.review_session_id == review.id,
                    ImportedRecordReview.decision.in_(APPLY_DECISIONS),
                )
            )
            or 0
        )
        review.status = (
            DataImportReviewStatus.READY_TO_APPLY
            if unreviewed_count == 0 and applyable_count > 0
            else DataImportReviewStatus.IN_REVIEW
        )

    def _copy_import_warnings(
        self,
        review_session_id: UUID,
        record_reviews_by_record_id: dict[UUID, ImportedRecordReview],
    ) -> None:
        review = self._get_review(review_session_id)
        warnings = self._db.scalars(
            select(ImportValidationWarning).where(
                ImportValidationWarning.data_import_run_id == review.data_import_run_id
            )
        ).all()
        for warning in warnings:
            review_record = (
                record_reviews_by_record_id.get(warning.imported_record_id)
                if warning.imported_record_id is not None
                else None
            )
            self._add_warning(
                review_session_id,
                review_record.id if review_record is not None else None,
                None,
                warning.warning_code,
                warning.severity,
                warning.message,
                warning.requires_advisor_confirmation,
            )

    def _record_reviews_for_application(
        self,
        review_session_id: UUID,
    ) -> list[ImportedRecordReview]:
        return list(
            self._db.scalars(
                select(ImportedRecordReview)
                .join(ImportedRecord, ImportedRecordReview.imported_record_id == ImportedRecord.id)
                .where(ImportedRecordReview.review_session_id == review_session_id)
                .order_by(ImportedRecord.row_number, ImportedRecordReview.id)
            ).all()
        )

    def _candidate_for_review(
        self,
        record_review: ImportedRecordReview,
        selected_mapping_candidate_id: UUID | None,
    ) -> ImportMappingCandidate | None:
        candidate_id = selected_mapping_candidate_id or record_review.selected_mapping_candidate_id
        if candidate_id is not None:
            candidate = self._db.get(ImportMappingCandidate, candidate_id)
            if candidate is None:
                raise DataReviewValidationError(
                    "mapping_candidate_not_found",
                    f"ImportMappingCandidate {candidate_id} was not found.",
                )
            if candidate.imported_record_id != record_review.imported_record_id:
                raise DataReviewValidationError(
                    "mapping_candidate_mismatch",
                    "Selected mapping candidate does not belong to the reviewed record.",
                )
            return candidate
        return self._selected_candidate(record_review.imported_record_id)

    def _selected_candidate(self, imported_record_id: UUID) -> ImportMappingCandidate | None:
        return self._db.scalar(
            select(ImportMappingCandidate)
            .where(ImportMappingCandidate.imported_record_id == imported_record_id)
            .order_by(
                ImportMappingCandidate.is_selected.desc(),
                ImportMappingCandidate.confidence_score.desc(),
                ImportMappingCandidate.id,
            )
        )

    def _previous_successful_application(
        self,
        imported_record_id: UUID,
    ) -> AppliedImportedRecord | None:
        return self._db.scalar(
            select(AppliedImportedRecord)
            .where(
                AppliedImportedRecord.imported_record_id == imported_record_id,
                AppliedImportedRecord.status == AppliedImportStatus.SUCCESS,
                AppliedImportedRecord.target_entity_id.is_not(None),
            )
            .order_by(AppliedImportedRecord.created_at.desc(), AppliedImportedRecord.id.desc())
        )

    def _review_payload(
        self,
        record_review: ImportedRecordReview,
        record: ImportedRecord,
    ) -> dict[str, object]:
        if record_review.edited_normalized_payload is None:
            return dict(record.normalized_payload)
        return {**record.normalized_payload, **record_review.edited_normalized_payload}

    def _parse_credits(self, value: object) -> Decimal | None:
        try:
            credits = Decimal(str(value or "").strip())
        except (InvalidOperation, ValueError):
            return None
        return credits if credits >= 0 else None

    def _attempt_status(
        self,
        payload: dict[str, object],
        grade: str,
    ) -> StudentCourseAttemptStatus:
        status = str(payload.get("status") or "").strip().upper()
        if status in {"IN_PROGRESS", "CURRENT"}:
            return StudentCourseAttemptStatus.IN_PROGRESS
        if status == "PLANNED":
            return StudentCourseAttemptStatus.PLANNED
        if status == "TRANSFERRED":
            return StudentCourseAttemptStatus.TRANSFERRED
        if status in {"WITHDRAWN", "W"} or grade in {"W", "WF"}:
            return StudentCourseAttemptStatus.WITHDRAWN
        if status == "INCOMPLETE" or grade == "I":
            return StudentCourseAttemptStatus.INCOMPLETE
        if status == "FAILED" or grade in {"F", "U"}:
            return StudentCourseAttemptStatus.FAILED
        return StudentCourseAttemptStatus.COMPLETED

    def _credits_earned(
        self,
        status: StudentCourseAttemptStatus,
        grade: str,
        credits: Decimal,
    ) -> Decimal:
        if status in {
            StudentCourseAttemptStatus.FAILED,
            StudentCourseAttemptStatus.WITHDRAWN,
            StudentCourseAttemptStatus.INCOMPLETE,
            StudentCourseAttemptStatus.IN_PROGRESS,
            StudentCourseAttemptStatus.PLANNED,
        }:
            return Decimal("0.0")
        if grade in {"F", "U", "W", "WF", "I"}:
            return Decimal("0.0")
        return credits

    def _existing_course_attempt(
        self,
        student_profile_id: UUID,
        course_id: UUID,
        term_id: UUID,
        grade: str | None,
        credits_attempted: Decimal,
    ) -> StudentCourseAttempt | None:
        return self._db.scalar(
            select(StudentCourseAttempt)
            .where(
                StudentCourseAttempt.student_profile_id == student_profile_id,
                StudentCourseAttempt.course_id == course_id,
                StudentCourseAttempt.term_id == term_id,
                StudentCourseAttempt.grade == grade,
                StudentCourseAttempt.credits_attempted == credits_attempted,
            )
            .order_by(StudentCourseAttempt.attempt_number)
        )

    def _next_attempt_number(self, student_profile_id: UUID, course_id: UUID) -> int:
        current_max = self._db.scalar(
            select(func.max(StudentCourseAttempt.attempt_number)).where(
                StudentCourseAttempt.student_profile_id == student_profile_id,
                StudentCourseAttempt.course_id == course_id,
            )
        )
        return int(current_max or 0) + 1

    def _application_status(self, application: DataApplicationRun) -> DataApplicationStatus:
        if application.error_count > 0:
            return DataApplicationStatus.FAILED
        if application.warning_count > 0 or application.skipped_count > 0:
            return DataApplicationStatus.APPLIED_WITH_WARNINGS
        return DataApplicationStatus.APPLIED

    def _outcome(
        self,
        application_id: UUID | None,
        record_review: ImportedRecordReview,
        action: AppliedImportAction,
        status: AppliedImportStatus,
        reason_code: str,
        message: str,
        target_entity_id: UUID | None = None,
    ) -> AppliedImportedRecordResult:
        target_entity_type = (
            AppliedImportTargetEntityType.STUDENT_COURSE_ATTEMPT
            if target_entity_id is not None or action is AppliedImportAction.CREATED
            else AppliedImportTargetEntityType.UNKNOWN
        )
        return AppliedImportedRecordResult(
            id=None,
            data_application_run_id=application_id,
            imported_record_review_id=record_review.id,
            imported_record_id=record_review.imported_record_id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            action=action,
            status=status,
            reason_code=reason_code,
            message=message,
            created_at=None,
        )

    def _result_from_row(self, row: AppliedImportedRecord) -> AppliedImportedRecordResult:
        return AppliedImportedRecordResult(
            id=row.id,
            data_application_run_id=row.data_application_run_id,
            imported_record_review_id=row.imported_record_review_id,
            imported_record_id=row.imported_record_id,
            target_entity_type=row.target_entity_type,
            target_entity_id=row.target_entity_id,
            action=row.action,
            status=row.status,
            reason_code=row.reason_code,
            message=row.message,
            created_at=row.created_at,
        )

    def _add_warning(
        self,
        review_session_id: UUID,
        imported_record_review_id: UUID | None,
        data_application_run_id: UUID | None,
        warning_code: str,
        severity: AuditWarningSeverity,
        message: str,
        requires_advisor_confirmation: bool,
    ) -> None:
        self._db.add(
            DataReviewWarning(
                id=uuid4(),
                review_session_id=review_session_id,
                imported_record_review_id=imported_record_review_id,
                data_application_run_id=data_application_run_id,
                warning_code=warning_code,
                severity=severity,
                message=message,
                requires_advisor_confirmation=requires_advisor_confirmation,
            )
        )

    def _review_warnings(self, review_session_id: UUID) -> list[DataReviewWarning]:
        return list(
            self._db.scalars(
                select(DataReviewWarning)
                .where(DataReviewWarning.review_session_id == review_session_id)
                .order_by(DataReviewWarning.created_at, DataReviewWarning.id)
            ).all()
        )

    def _get_run(self, data_import_run_id: UUID) -> DataImportRun:
        run = self._db.get(DataImportRun, data_import_run_id)
        if run is None:
            raise DataReviewValidationError(
                "not_found",
                f"DataImportRun {data_import_run_id} was not found.",
            )
        if run.source_type is SourceType.OFFICIAL or run.is_official:
            raise DataReviewValidationError(
                "official_source_blocked",
                "Phase 7B cannot review or apply official-source imports.",
            )
        return run

    def _get_review(self, review_session_id: UUID) -> DataImportReviewSession:
        review = self._db.get(DataImportReviewSession, review_session_id)
        if review is None:
            raise DataReviewValidationError(
                "not_found",
                f"DataImportReviewSession {review_session_id} was not found.",
            )
        return review

    def _get_record_review(
        self,
        review_session_id: UUID,
        record_review_id: UUID,
    ) -> ImportedRecordReview:
        record_review = self._db.scalar(
            select(ImportedRecordReview).where(
                ImportedRecordReview.id == record_review_id,
                ImportedRecordReview.review_session_id == review_session_id,
            )
        )
        if record_review is None:
            raise DataReviewValidationError(
                "not_found",
                f"ImportedRecordReview {record_review_id} was not found.",
            )
        return record_review

    def _get_imported_record(self, imported_record_id: UUID) -> ImportedRecord:
        record = self._db.get(ImportedRecord, imported_record_id)
        if record is None:
            raise DataReviewValidationError(
                "not_found",
                f"ImportedRecord {imported_record_id} was not found.",
            )
        return record
