from __future__ import annotations

from datetime import UTC, date, datetime, time
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
    Campus,
    Course,
    CourseStateSnapshot,
    DataApplicationRun,
    DataApplicationStatus,
    DataImportReviewSession,
    DataImportReviewStatus,
    DataImportRun,
    DataReviewWarning,
    DayOfWeek,
    ImportedRecord,
    ImportedRecordReview,
    ImportedRecordReviewDecision,
    ImportedRecordStatus,
    ImportedRecordType,
    ImportMappingCandidate,
    ImportTargetEntityType,
    ImportValidationWarning,
    MeetingType,
    Section,
    SectionMeeting,
    SectionModality,
    SectionStatus,
    SourceType,
    StudentCourseAttempt,
    StudentCourseAttemptStatus,
)
from app.services.course_state.engine import CourseStateApplicationService
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
        self._course_states = CourseStateApplicationService(db)

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
            decision = (
                ImportedRecordReviewDecision.CONFIRMED
                if self._record_auto_confirmed(record)
                else ImportedRecordReviewDecision.UNREVIEWED
            )
            record_review = ImportedRecordReview(
                id=uuid4(),
                review_session_id=review.id,
                imported_record_id=record.id,
                selected_mapping_candidate_id=candidate.id if candidate is not None else None,
                decision=decision,
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
        self._sync_review_status(review)
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
                    course_state_snapshot=None,
                    course_state_snapshot_reused=False,
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
                course_state_snapshot=self._course_states.snapshot_for_import(run.id),
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
        course_state_snapshot, course_state_snapshot_reused = self._course_states.prepare_snapshot(
            review=review,
            run=run,
            application=application,
        )

        results: list[AppliedImportedRecordResult] = []
        for record_review in record_reviews:
            result = self._build_application_result(
                review,
                run,
                record_review,
                allow_advisor_review_records=allow_advisor_review_records,
                application_id=application.id,
                dry_run=False,
                course_state_snapshot=course_state_snapshot,
                course_state_snapshot_reused=course_state_snapshot_reused,
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

        if course_state_snapshot is not None and not course_state_snapshot_reused:
            self._course_states.finalize_snapshot(course_state_snapshot)

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
            course_state_snapshot=course_state_snapshot,
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
        course_state_snapshot: CourseStateSnapshot | None,
        course_state_snapshot_reused: bool,
    ) -> AppliedImportedRecordResult:
        record = self._get_imported_record(record_review.imported_record_id)
        if self._run_blocks_downstream(run):
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_DEFERRED,
                AppliedImportStatus.FAILED,
                "IMPORT_VALIDATION_FAILED",
                (
                    "The imported MyProgress snapshot failed validation and cannot be used "
                    "for downstream academic analysis."
                ),
            )
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
        section_result = self._section_application_result(
            application_id,
            run,
            record_review,
            record,
            dry_run=dry_run,
        )
        if section_result is not None:
            return section_result
        myprogress_result = self._myprogress_application_result(
            application_id,
            review,
            run,
            record_review,
            record,
            dry_run=dry_run,
            course_state_snapshot=course_state_snapshot,
            course_state_snapshot_reused=course_state_snapshot_reused,
        )
        if myprogress_result is not None:
            return myprogress_result
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

        candidate = self._db.scalar(
            select(ImportMappingCandidate)
            .where(
                ImportMappingCandidate.imported_record_id == record.id,
                ImportMappingCandidate.target_entity_type == ImportTargetEntityType.COURSE,
                ImportMappingCandidate.is_selected.is_(True),
            )
            .order_by(ImportMappingCandidate.confidence_score.desc())
        )
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

    def _section_application_result(
        self,
        application_id: UUID | None,
        run: DataImportRun,
        record_review: ImportedRecordReview,
        record: ImportedRecord,
        *,
        dry_run: bool,
    ) -> AppliedImportedRecordResult | None:
        if record.record_type is not ImportedRecordType.SECTION:
            return None
        payload = self._review_payload(record_review, record)
        validation_state = str(
            payload.get("section_validation_state") or payload.get("validation_state") or ""
        ).upper()
        if validation_state == "FAILED":
            return self._section_outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "SKIP_FAILED_VALIDATION",
                "Failed Section validation cannot be applied.",
            )
        if str(payload.get("completeness") or "").upper() == "UNCERTAIN":
            return self._section_outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "SKIP_TRUNCATED_IMPORT",
                "A bounded or incomplete Section snapshot cannot be applied as complete.",
            )

        candidate = self._db.scalar(
            select(ImportMappingCandidate)
            .where(
                ImportMappingCandidate.imported_record_id == record.id,
                ImportMappingCandidate.target_entity_type == ImportTargetEntityType.COURSE,
                ImportMappingCandidate.is_selected.is_(True),
            )
            .order_by(ImportMappingCandidate.confidence_score.desc())
        )
        if candidate is None or candidate.target_entity_type is not ImportTargetEntityType.COURSE:
            return self._section_outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "SKIP_UNKNOWN_COURSE",
                "A confirmed existing Course mapping is required before Section Apply.",
            )
        course = (
            self._db.get(Course, candidate.target_entity_id) if candidate.target_entity_id else None
        )
        if course is None:
            return self._section_outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "SKIP_UNKNOWN_COURSE",
                "The selected Course mapping no longer exists.",
            )
        term_code = str(payload.get("term") or payload.get("term_code") or "").strip()
        term = (
            self._db.scalar(
                select(AcademicTerm).where(
                    AcademicTerm.institution_id == course.institution_id,
                    AcademicTerm.term_code == term_code,
                )
            )
            if term_code
            else None
        )
        if term is None:
            return self._section_outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "SKIP_UNKNOWN_TERM",
                f"Visible term {term_code or 'missing'} is not mapped to this institution.",
            )
        campus = self._section_campus(course.institution_id, payload)
        if campus is None:
            return self._section_outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "SKIP_UNKNOWN_CAMPUS",
                "A visible or explicitly selected existing Campus mapping is required.",
            )
        section_code = str(payload.get("section_code") or "").strip()
        if not section_code:
            return self._section_outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "SKIP_AMBIGUOUS_SECTION_IDENTITY",
                "Section code is required and cannot be inferred.",
            )
        section = self._db.scalar(
            select(Section).where(
                Section.institution_id == course.institution_id,
                Section.term_id == term.id,
                Section.course_id == course.id,
                Section.section_code == section_code,
            )
        )
        if section is not None and (section.is_official or section.source_type.name == "MOCK"):
            return self._section_outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "CONFLICT_OFFICIAL_OR_MOCK_TARGET",
                "Official or MOCK Section records are never overwritten by imported data.",
            )
        if section is not None and section.source_type.name not in {
            "BROWSER_EXTENSION",
            "IMPORTED",
        }:
            return self._section_outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "CONFLICT_UNRELATED_SOURCE",
                "An unrelated Section source requires explicit conflict review.",
            )

        status = self._section_status(payload.get("status"))
        modality = self._section_modality(payload.get("modality"))
        credits = self._parse_credits(payload.get("credits"))
        if not dry_run:
            if section is None:
                section = Section(
                    id=uuid4(),
                    institution_id=course.institution_id,
                    course_id=course.id,
                    term_id=term.id,
                    campus_id=campus.id,
                    section_code=section_code,
                    external_reference=self._optional_text(payload.get("external_reference")),
                    title_override=self._optional_text(
                        payload.get("course_title") or payload.get("title")
                    ),
                    credits=credits,
                    status=status,
                    modality=modality,
                    capacity=None,
                    available_seats=None,
                    waitlist_capacity=None,
                    waitlist_available=None,
                    instructor_display=self._optional_text(payload.get("instructor_display")),
                    last_synced_at=None,
                    source_type=SourceType.BROWSER_EXTENSION,
                    is_official=False,
                    source_reference=self._section_source_reference(run, record),
                    source_retrieved_at=run.created_at,
                    source_confidence="reviewed_import",
                )
                self._db.add(section)
                self._db.flush()
                action = AppliedImportAction.CREATED
                reason = "CREATED_IMPORTED_SECTION"
                message_prefix = "Created non-official imported Section."
            else:
                section.external_reference = self._optional_text(payload.get("external_reference"))
                section.title_override = self._optional_text(
                    payload.get("course_title") or payload.get("title")
                )
                section.credits = credits
                section.status = status
                section.modality = modality
                section.campus_id = campus.id
                section.instructor_display = self._optional_text(payload.get("instructor_display"))
                section.source_reference = self._section_source_reference(run, record)
                section.source_retrieved_at = run.created_at
                section.source_confidence = "reviewed_import"
                action = AppliedImportAction.UPDATED
                reason = "UPDATED_IMPORTED_SECTION"
                message_prefix = "Updated same-source non-official imported Section."
            meeting_message = self._apply_section_meetings(section, payload, run, record)
        else:
            action = AppliedImportAction.CREATED if section is None else AppliedImportAction.UPDATED
            reason = (
                "WOULD_CREATE_IMPORTED_SECTION"
                if section is None
                else "WOULD_UPDATE_IMPORTED_SECTION"
            )
            message_prefix = (
                "Dry run would create a non-official imported Section."
                if section is None
                else "Dry run would update a same-source imported Section."
            )
            meeting_message = self._preview_section_meetings(payload)
        return self._section_outcome(
            application_id,
            record_review,
            action,
            AppliedImportStatus.SUCCESS,
            reason,
            f"{message_prefix} {meeting_message}",
            section.id if section is not None else None,
        )

    def _section_campus(self, institution_id: UUID, payload: dict[str, object]) -> Campus | None:
        raw = (
            str(
                payload.get("campus")
                or payload.get("campus_code")
                or payload.get("campus_label")
                or ""
            )
            .strip()
            .casefold()
        )
        if not raw:
            return None
        campuses = self._db.scalars(
            select(Campus).where(Campus.institution_id == institution_id)
        ).all()
        return next(
            (
                campus
                for campus in campuses
                if raw in {campus.code.casefold(), campus.name.casefold()}
            ),
            None,
        )

    def _section_status(self, value: object) -> SectionStatus:
        normalized = str(value or "").strip().upper()
        return (
            SectionStatus(normalized)
            if normalized in {item.value for item in SectionStatus}
            else SectionStatus.UNKNOWN
        )

    def _section_modality(self, value: object) -> SectionModality:
        normalized = str(value or "").strip().upper()
        return (
            SectionModality(normalized)
            if normalized in {item.value for item in SectionModality}
            else SectionModality.UNKNOWN
        )

    def _section_meeting_type(self, value: object) -> MeetingType:
        normalized = str(value or "").strip().upper()
        return (
            MeetingType(normalized)
            if normalized in {item.value for item in MeetingType}
            else MeetingType.OTHER
        )

    def _section_day(self, value: object) -> DayOfWeek | None:
        normalized = str(value or "").strip().upper()
        return DayOfWeek(normalized) if normalized in {item.value for item in DayOfWeek} else None

    def _section_time(self, value: object) -> time | None:
        raw = str(value or "").strip()
        try:
            return time.fromisoformat(raw) if raw else None
        except ValueError:
            return None

    def _section_date(self, value: object) -> date | None:
        raw = str(value or "").strip()
        try:
            return date.fromisoformat(raw) if raw else None
        except ValueError:
            return None

    def _section_source_reference(self, run: DataImportRun, record: ImportedRecord) -> str:
        return f"{(run.source_reference or 'reviewed Section import')[:430]}#record={record.id}"

    def _optional_text(self, value: object) -> str | None:
        text = str(value or "").strip()
        return text or None

    def _section_meetings(self, payload: dict[str, object]) -> list[dict[str, object]]:
        meetings = payload.get("meetings_json")
        return (
            [item for item in meetings if isinstance(item, dict)]
            if isinstance(meetings, list)
            else []
        )

    def _preview_section_meetings(self, payload: dict[str, object]) -> str:
        meetings = self._section_meetings(payload)
        return (
            f"Would reconcile {len(meetings)} confirmed meeting evidence row(s); "
            "volatile availability is not applied."
        )

    def _apply_section_meetings(
        self,
        section: Section,
        payload: dict[str, object],
        run: DataImportRun,
        record: ImportedRecord,
    ) -> str:
        meetings = self._section_meetings(payload)
        complete = str(payload.get("completeness") or "").upper() == "COMPLETE"
        existing = self._db.scalars(
            select(SectionMeeting)
            .where(SectionMeeting.section_id == section.id)
            .order_by(SectionMeeting.display_order)
        ).all()
        source_meetings = [
            meeting
            for meeting in existing
            if meeting.source_type.name in {"BROWSER_EXTENSION", "IMPORTED"}
            and not meeting.is_official
        ]
        desired: list[tuple[dict[str, object], DayOfWeek | None]] = []
        for meeting in meetings:
            days = [self._section_day(day) for day in str(meeting.get("days") or "").split(",")]
            days = [day for day in days if day is not None] or [None]
            desired.extend((meeting, day) for day in days)
        changed = 0
        for index, (meeting_payload, day) in enumerate(desired):
            identity = (
                day,
                self._section_time(meeting_payload.get("start_time")),
                self._section_time(meeting_payload.get("end_time")),
                self._optional_text(meeting_payload.get("location")),
            )
            current = next(
                (
                    item
                    for item in source_meetings
                    if (item.day_of_week, item.start_time, item.end_time, item.building) == identity
                ),
                None,
            )
            if current is None:
                current = SectionMeeting(
                    id=uuid4(),
                    section_id=section.id,
                    meeting_type=self._section_meeting_type(meeting_payload.get("component")),
                    day_of_week=day,
                    start_time=identity[1],
                    end_time=identity[2],
                    start_date=self._section_date(meeting_payload.get("start_date")),
                    end_date=self._section_date(meeting_payload.get("end_date")),
                    building=self._optional_text(meeting_payload.get("location")),
                    room=self._optional_text(meeting_payload.get("room")),
                    timezone="America/New_York",
                    is_arranged=bool(meeting_payload.get("is_arranged"))
                    or not identity[0]
                    and not identity[1]
                    and not identity[2],
                    is_online=bool(meeting_payload.get("is_async"))
                    or "ONLINE" in str(meeting_payload.get("modality") or "").upper(),
                    display_order=index,
                    source_type=SourceType.BROWSER_EXTENSION,
                    is_official=False,
                    source_reference=(
                        f"{self._section_source_reference(run, record)}#meeting={index}"
                    ),
                    source_retrieved_at=run.created_at,
                    source_confidence="reviewed_import",
                )
                self._db.add(current)
                changed += 1
        if complete:
            desired_identities = {
                (
                    day,
                    self._section_time(item.get("start_time")),
                    self._section_time(item.get("end_time")),
                    self._optional_text(item.get("location")),
                )
                for item, day in desired
            }
            for current in source_meetings:
                identity = (
                    current.day_of_week,
                    current.start_time,
                    current.end_time,
                    current.building,
                )
                if identity not in desired_identities:
                    self._db.delete(current)
                    changed += 1
        return (
            f"Reconciled {len(desired)} meeting row(s); "
            f"{changed} meeting action(s) recorded with the Section application. "
            "Volatile availability was not applied."
        )

    def _section_outcome(
        self,
        application_id: UUID | None,
        record_review: ImportedRecordReview,
        action: AppliedImportAction,
        status: AppliedImportStatus,
        reason_code: str,
        message: str,
        target_entity_id: UUID | None = None,
    ) -> AppliedImportedRecordResult:
        return self._outcome(
            application_id,
            record_review,
            action,
            status,
            reason_code,
            message,
            target_entity_id,
            target_entity_type=AppliedImportTargetEntityType.SECTION,
        )

    def _myprogress_application_result(
        self,
        application_id: UUID | None,
        review: DataImportReviewSession,
        run: DataImportRun,
        record_review: ImportedRecordReview,
        record: ImportedRecord,
        *,
        dry_run: bool,
        course_state_snapshot: CourseStateSnapshot | None,
        course_state_snapshot_reused: bool,
    ) -> AppliedImportedRecordResult | None:
        payload = record.normalized_payload
        if payload.get("source_page_type") != "KEAN_MY_PROGRESS_PAGE":
            return None
        if payload.get("record_kind") == "MY_PROGRESS_COURSE_ROW":
            outcome = (
                self._course_states.dry_run_outcome(record_review, record)
                if dry_run
                else self._course_states.apply_record(
                    snapshot=course_state_snapshot,
                    review=review,
                    run=run,
                    record_review=record_review,
                    record=record,
                )
                if course_state_snapshot is not None
                else None
            )
            if outcome is None:
                return self._outcome(
                    application_id,
                    record_review,
                    AppliedImportAction.SKIPPED_DEFERRED,
                    AppliedImportStatus.FAILED,
                    "COURSE_STATE_SNAPSHOT_NOT_AVAILABLE",
                    "A validated course-state snapshot was not available for this row.",
                    target_entity_type=AppliedImportTargetEntityType.COURSE_STATE,
                )
            return self._outcome(
                application_id,
                record_review,
                outcome.action,
                outcome.status,
                outcome.reason_code,
                outcome.message,
                outcome.target_entity_id,
                target_entity_type=outcome.target_entity_type,
            )
        if course_state_snapshot_reused:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_DUPLICATE,
                AppliedImportStatus.SKIPPED,
                "ALREADY_APPLIED_MYPROGRESS_SNAPSHOT_RECORD",
                "This MyProgress summary record already belongs to the applied snapshot.",
                target_entity_type=AppliedImportTargetEntityType.COURSE_STATE,
            )
        record_kind = str(payload.get("record_kind") or "")
        if record.record_type is ImportedRecordType.PROGRAM:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.UPDATED,
                AppliedImportStatus.SUCCESS,
                "APPLIED_MYPROGRESS_PROGRAM_SUMMARY",
                (
                    "Applied MyProgress program summary to internal imported planning snapshot; "
                    "no official school record was created or modified."
                ),
            )
        if record_kind == "MY_PROGRESS_REQUIREMENT_GROUP":
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.UPDATED,
                AppliedImportStatus.SUCCESS,
                "APPLIED_MYPROGRESS_REQUIREMENT_SUMMARY",
                (
                    "Applied MyProgress requirement summary to the internal imported audit "
                    "snapshot; detailed course-row audit remains advisory."
                ),
            )
        if record.record_type is ImportedRecordType.REQUIREMENT:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.UPDATED,
                AppliedImportStatus.WARNING,
                "APPLIED_MYPROGRESS_REQUIREMENT_PARTIAL",
                (
                    "Applied supported MyProgress requirement record partially to internal "
                    "imported audit state."
                ),
            )
        return None

    def _record_requires_advisor_review(
        self,
        record: ImportedRecord,
        candidate: ImportMappingCandidate | None,
    ) -> bool:
        if self._record_auto_confirmed(record):
            return False
        if record.status not in {
            ImportedRecordStatus.VALID,
            ImportedRecordStatus.VALID_WITH_WARNINGS,
        }:
            return True
        if candidate is None:
            return True
        return candidate.target_entity_type is ImportTargetEntityType.UNKNOWN

    def _record_auto_confirmed(self, record: ImportedRecord) -> bool:
        payload = record.normalized_payload
        if payload.get("source_page_type") != "KEAN_MY_PROGRESS_PAGE":
            return False
        if payload.get("requiresReview") is True:
            return False
        return record.status is ImportedRecordStatus.VALID

    def _run_blocks_downstream(self, run: DataImportRun) -> bool:
        record = self._db.scalar(
            select(ImportedRecord)
            .where(
                ImportedRecord.data_import_run_id == run.id,
                ImportedRecord.record_type == ImportedRecordType.PROGRAM,
            )
            .order_by(ImportedRecord.row_number, ImportedRecord.id)
        )
        if record is None or record.normalized_payload.get("source_page_type") != (
            "KEAN_MY_PROGRESS_PAGE"
        ):
            return False
        validation = record.normalized_payload.get("validation")
        if not isinstance(validation, dict):
            return True
        return validation.get("downstreamAnalysisAllowed") is not True

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
        *,
        target_entity_type: AppliedImportTargetEntityType | None = None,
    ) -> AppliedImportedRecordResult:
        resolved_target_entity_type = target_entity_type or (
            AppliedImportTargetEntityType.STUDENT_COURSE_ATTEMPT
            if target_entity_id is not None or action is AppliedImportAction.CREATED
            else AppliedImportTargetEntityType.UNKNOWN
        )
        return AppliedImportedRecordResult(
            id=None,
            data_application_run_id=application_id,
            imported_record_review_id=record_review.id,
            imported_record_id=record_review.imported_record_id,
            target_entity_type=resolved_target_entity_type,
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
