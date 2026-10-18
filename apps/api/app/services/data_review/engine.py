from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from urllib.parse import quote, urlparse
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
    DataImportType,
    DataReviewWarning,
    DayOfWeek,
    ImportedRecord,
    ImportedRecordReview,
    ImportedRecordReviewDecision,
    ImportedRecordStatus,
    ImportedRecordType,
    ImportMappingCandidate,
    ImportMatchType,
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
    StudentProfile,
)
from app.services.course_state.engine import CourseStateApplicationService
from app.services.data_imports.normalizers import (
    canonical_section_source_locator,
    normalize_course_code,
    split_course_code,
)
from app.services.data_review.exceptions import DataReviewValidationError
from app.services.data_review.result import (
    AppliedImportedRecordResult,
    CatalogBatchProcessingResult,
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
CATALOG_BATCH_UNSAFE_WARNING_REASONS = {
    "EXTRACTION_LIMIT_REACHED": "BATCH_CATALOG_TRUNCATED_PAGE",
    "BATCH_CATALOG_TRUNCATED_PAGE": "BATCH_CATALOG_TRUNCATED_PAGE",
    "BATCH_CATALOG_RATE_LIMIT": "BATCH_CATALOG_RATE_LIMIT",
    "BATCH_CATALOG_PROVIDER_ERROR": "BATCH_CATALOG_PROVIDER_ERROR",
    "BATCH_CATALOG_PAGE_TIMEOUT": "BATCH_CATALOG_PAGE_TIMEOUT",
    "NO_IMPORTABLE_ROWS": "BATCH_CATALOG_PARSER_DRIFT",
    "MALFORMED_ROW": "BATCH_CATALOG_PARSER_DRIFT",
    "UNKNOWN_COLUMNS_REDACTED": "BATCH_CATALOG_PARSER_DRIFT",
    "MISSING_EXPECTED_FIELD": "BATCH_CATALOG_PARSER_DRIFT",
}
CATALOG_BATCH_DRY_RUN_SUCCESS_REASONS = {
    "WOULD_CREATE_IMPORTED_COURSE",
    "WOULD_UPDATE_IMPORTED_COURSE",
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
        self._db.flush()
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

    def process_catalog_batch_import(
        self,
        data_import_run_id: UUID,
    ) -> CatalogBatchProcessingResult:
        run = self._get_run(data_import_run_id)
        _, mapped_before_count, _ = self._latest_myprogress_mapping_counts(run.student_profile_id)
        review = self._latest_review_for_run(run.id)
        if review is not None and review.status in {
            DataImportReviewStatus.APPLIED,
            DataImportReviewStatus.APPLIED_WITH_WARNINGS,
        }:
            application = self._existing_application_result(review)
            replay_blockers = (
                ["BATCH_CATALOG_APPLICATION_EVIDENCE_MISSING"]
                if application is None
                else sorted(
                    {
                        result.reason_code
                        for result in application.applied_records
                        if result.status is not AppliedImportStatus.SUCCESS
                    }
                )
            )
            replay_blocked_count = (
                self._confirmed_review_record_count(review.id)
                if application is None
                else sum(
                    result.status is not AppliedImportStatus.SUCCESS
                    for result in application.applied_records
                )
            )
            myprogress_remap_executed = (
                self._execute_myprogress_remap(run, application)
                if application is not None
                else False
            )
            myprogress_run_id, mapped_count, unmatched_count = (
                self._latest_myprogress_mapping_counts(run.student_profile_id)
            )
            return CatalogBatchProcessingResult(
                status="BLOCKED" if replay_blockers else "APPLIED",
                review_session=review,
                dry_run=None,
                application=application,
                confirmed_record_count=self._confirmed_review_record_count(review.id),
                blocked_record_count=replay_blocked_count,
                reason_codes=replay_blockers,
                myprogress_run_id=myprogress_run_id,
                myprogress_mapped_count=mapped_count,
                myprogress_unmatched_count=unmatched_count,
                processing_stages_completed=[
                    "LOCAL_STAGING",
                    "LOCAL_VALIDATION",
                    "LOCAL_REVIEW",
                    "LOCAL_DRY_RUN",
                    "LOCAL_APPLY",
                    "MYPROGRESS_REMAP",
                ],
                staged_record_count=len(self._record_reviews_for_batch(review.id)),
                review_valid_count=self._confirmed_review_record_count(review.id),
                review_warning_count=self._review_warning_record_count(review.id),
                applied_record_count=(
                    sum(
                        result.status is AppliedImportStatus.SUCCESS
                        for result in application.applied_records
                    )
                    if application
                    else 0
                ),
                myprogress_total_count=mapped_count + unmatched_count,
                myprogress_mapped_before_count=mapped_before_count,
                myprogress_remap_executed=myprogress_remap_executed,
                already_processed=True,
            )

        if review is None or review.status not in ACTIVE_REVIEW_STATUSES:
            review = self.create_review_session(
                data_import_run_id=run.id,
                reviewer_label="SAPSOS deterministic Course Catalog batch",
            )

        record_reviews = self._record_reviews_for_batch(review.id)
        blocked_reasons = self._catalog_batch_capture_reasons(run, record_reviews)
        if blocked_reasons:
            myprogress_run_id, mapped_count, unmatched_count = (
                self._latest_myprogress_mapping_counts(run.student_profile_id)
            )
            return CatalogBatchProcessingResult(
                status="BLOCKED",
                review_session=review,
                dry_run=None,
                application=None,
                confirmed_record_count=0,
                blocked_record_count=len(record_reviews),
                reason_codes=blocked_reasons,
                myprogress_run_id=myprogress_run_id,
                myprogress_mapped_count=mapped_count,
                myprogress_unmatched_count=unmatched_count,
                processing_stages_completed=[
                    "LOCAL_STAGING",
                    "LOCAL_VALIDATION",
                    "LOCAL_REVIEW",
                ],
                staged_record_count=len(record_reviews),
                review_valid_count=0,
                review_warning_count=self._review_warning_record_count(review.id),
                applied_record_count=0,
                myprogress_total_count=mapped_count + unmatched_count,
                myprogress_mapped_before_count=mapped_before_count,
            )

        for record_review in record_reviews:
            if record_review.decision is ImportedRecordReviewDecision.CONFIRMED:
                continue
            record = self._get_imported_record(record_review.imported_record_id)
            requisite_review_required = record.normalized_payload.get("rule_review_status") in {
                "MANUAL_CONFIRMATION_REQUIRED",
                "REVIEW_REQUIRED",
            }
            self.update_record_review(
                review_session_id=review.id,
                record_review_id=record_review.id,
                decision=ImportedRecordReviewDecision.CONFIRMED,
                review_note=(
                    "Deterministically confirmed exact visible Course identity, title, and "
                    "positive credits from the user-initiated Kean Catalog batch; requisite "
                    "policy remains raw review-required text."
                ),
                requires_advisor_confirmation=requisite_review_required,
            )

        dry_run = self.apply_review_session(review.id, dry_run=True)
        dry_run_blockers = sorted(
            {
                result.reason_code
                for result in dry_run.applied_records
                if result.status is not AppliedImportStatus.SUCCESS
                or result.reason_code not in CATALOG_BATCH_DRY_RUN_SUCCESS_REASONS
            }
        )
        dry_run_blocked_count = sum(
            result.status is not AppliedImportStatus.SUCCESS
            or result.reason_code not in CATALOG_BATCH_DRY_RUN_SUCCESS_REASONS
            for result in dry_run.applied_records
        )
        if dry_run_blockers:
            self._db.refresh(review)
            myprogress_run_id, mapped_count, unmatched_count = (
                self._latest_myprogress_mapping_counts(run.student_profile_id)
            )
            return CatalogBatchProcessingResult(
                status="BLOCKED",
                review_session=review,
                dry_run=dry_run,
                application=None,
                confirmed_record_count=self._confirmed_review_record_count(review.id),
                blocked_record_count=dry_run_blocked_count,
                reason_codes=dry_run_blockers,
                myprogress_run_id=myprogress_run_id,
                myprogress_mapped_count=mapped_count,
                myprogress_unmatched_count=unmatched_count,
                processing_stages_completed=[
                    "LOCAL_STAGING",
                    "LOCAL_VALIDATION",
                    "LOCAL_REVIEW",
                    "LOCAL_DRY_RUN",
                ],
                staged_record_count=len(record_reviews),
                review_valid_count=self._confirmed_review_record_count(review.id),
                review_warning_count=self._review_warning_record_count(review.id),
                applied_record_count=0,
                myprogress_total_count=mapped_count + unmatched_count,
                myprogress_mapped_before_count=mapped_before_count,
            )

        application = self.apply_review_session(review.id)
        actual_blockers = sorted(
            {
                result.reason_code
                for result in application.applied_records
                if result.status is not AppliedImportStatus.SUCCESS
            }
        )
        actual_blocked_count = sum(
            result.status is not AppliedImportStatus.SUCCESS
            for result in application.applied_records
        )
        myprogress_remap_executed = self._execute_myprogress_remap(run, application)
        myprogress_run_id, mapped_count, unmatched_count = self._latest_myprogress_mapping_counts(
            run.student_profile_id
        )
        return CatalogBatchProcessingResult(
            status="BLOCKED" if actual_blockers else "APPLIED",
            review_session=application.review_session,
            dry_run=dry_run,
            application=application,
            confirmed_record_count=self._confirmed_review_record_count(review.id),
            blocked_record_count=actual_blocked_count,
            reason_codes=actual_blockers,
            myprogress_run_id=myprogress_run_id,
            myprogress_mapped_count=mapped_count,
            myprogress_unmatched_count=unmatched_count,
            processing_stages_completed=[
                "LOCAL_STAGING",
                "LOCAL_VALIDATION",
                "LOCAL_REVIEW",
                "LOCAL_DRY_RUN",
                "LOCAL_APPLY",
                "MYPROGRESS_REMAP",
            ],
            staged_record_count=len(record_reviews),
            review_valid_count=self._confirmed_review_record_count(review.id),
            review_warning_count=self._review_warning_record_count(review.id),
            applied_record_count=sum(
                result.status is AppliedImportStatus.SUCCESS
                for result in application.applied_records
            ),
            myprogress_total_count=mapped_count + unmatched_count,
            myprogress_mapped_before_count=mapped_before_count,
            myprogress_remap_executed=myprogress_remap_executed,
        )

    def _catalog_batch_capture_reasons(
        self,
        run: DataImportRun,
        record_reviews: list[ImportedRecordReview],
    ) -> list[str]:
        reasons: set[str] = set()
        if (
            run.import_type is not DataImportType.COURSE_CATALOG
            or run.source_type is not SourceType.BROWSER_EXTENSION
            or not (run.source_reference or "").startswith(
                "KEAN_STUDENT_PORTAL browser extension import: "
            )
        ):
            reasons.add("BATCH_CATALOG_SOURCE_NOT_AUTHORIZED")
        warning_codes = self._db.scalars(
            select(ImportValidationWarning.warning_code).where(
                ImportValidationWarning.data_import_run_id == run.id
            )
        ).all()
        reasons.update(
            CATALOG_BATCH_UNSAFE_WARNING_REASONS[code]
            for code in warning_codes
            if code in CATALOG_BATCH_UNSAFE_WARNING_REASONS
        )
        if not record_reviews:
            reasons.add("BATCH_CATALOG_PARSER_DRIFT")
        if any(
            not self._catalog_batch_record_is_safe(record_review)
            for record_review in record_reviews
        ):
            reasons.add("BATCH_CATALOG_PROVENANCE_INVALID")
        return sorted(reasons)

    def _catalog_batch_record_is_safe(
        self,
        record_review: ImportedRecordReview,
    ) -> bool:
        record = self._get_imported_record(record_review.imported_record_id)
        payload = record.normalized_payload
        normalized_code = normalize_course_code(str(payload.get("course_code") or ""))
        raw_visible_code = normalize_course_code(str(payload.get("raw_visible_course_code") or ""))
        explicit_optional_fields = (
            "course_level",
            "department",
            "description",
            "prerequisites",
            "corequisites",
            "minimum_grade",
            "standing_requirements",
            "restrictions",
            "raw_requisites",
        )
        if (
            record.record_type is not ImportedRecordType.COURSE
            or record.status
            not in {ImportedRecordStatus.VALID, ImportedRecordStatus.VALID_WITH_WARNINGS}
            or normalized_code is None
            or normalized_code != str(payload.get("normalized_code") or "").strip()
            or raw_visible_code != normalized_code
            or any(not str(payload.get(field) or "").strip() for field in explicit_optional_fields)
            or str(payload.get("source_label") or "").strip() != "Visible course catalog cards"
        ):
            return False
        title = str(payload.get("course_title") or payload.get("title") or "").strip()
        raw_title = str(payload.get("raw_visible_title") or "").strip()
        if not title or title != raw_title:
            return False
        credits = self._parse_credits(payload.get("credits"))
        if credits is None or credits <= 0:
            return False
        source_page = urlparse(str(payload.get("source_page") or ""))
        if (
            source_page.scheme != "https"
            or source_page.netloc != "kean-ss.colleague.elluciancloud.com"
            or source_page.path
            not in {
                "/Student/Courses/SearchResult",
                "/Student/Student/Courses/SearchResult",
            }
            or source_page.params
            or source_page.query
            or source_page.fragment
        ):
            return False
        captured_at = str(payload.get("capture_timestamp") or "").strip()
        try:
            parsed_capture_time = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        if parsed_capture_time.tzinfo is None:
            return False
        subject_code = normalized_code.split(" ", 1)[0]
        if str(payload.get("source_subject") or "").strip() != subject_code:
            return False
        try:
            page_number = int(str(payload.get("source_page_number") or ""))
            if page_number < 1 or page_number > 50:
                return False
        except ValueError:
            return False
        return str(payload.get("rule_review_status") or "") in {
            "NO_REQUISITES_VISIBLE",
            "MANUAL_CONFIRMATION_REQUIRED",
            "REVIEW_REQUIRED",
        }

    def _latest_review_for_run(self, run_id: UUID) -> DataImportReviewSession | None:
        return self._db.scalar(
            select(DataImportReviewSession)
            .where(DataImportReviewSession.data_import_run_id == run_id)
            .order_by(
                DataImportReviewSession.created_at.desc(),
                DataImportReviewSession.id.desc(),
            )
        )

    def _record_reviews_for_batch(
        self,
        review_id: UUID,
    ) -> list[ImportedRecordReview]:
        return list(
            self._db.scalars(
                select(ImportedRecordReview)
                .join(
                    ImportedRecord,
                    ImportedRecordReview.imported_record_id == ImportedRecord.id,
                )
                .where(ImportedRecordReview.review_session_id == review_id)
                .order_by(ImportedRecord.row_number, ImportedRecordReview.id)
            ).all()
        )

    def _confirmed_review_record_count(self, review_id: UUID) -> int:
        return int(
            self._db.scalar(
                select(func.count())
                .select_from(ImportedRecordReview)
                .where(
                    ImportedRecordReview.review_session_id == review_id,
                    ImportedRecordReview.decision.in_(APPLY_DECISIONS),
                )
            )
            or 0
        )

    def _review_warning_record_count(self, review_id: UUID) -> int:
        return int(
            self._db.scalar(
                select(func.count())
                .select_from(ImportedRecordReview)
                .where(
                    ImportedRecordReview.review_session_id == review_id,
                    ImportedRecordReview.requires_advisor_confirmation.is_(True),
                )
            )
            or 0
        )

    def _existing_application_result(
        self,
        review: DataImportReviewSession,
    ) -> DataReviewApplicationResult | None:
        application = self._db.scalar(
            select(DataApplicationRun)
            .where(DataApplicationRun.review_session_id == review.id)
            .order_by(DataApplicationRun.created_at.desc(), DataApplicationRun.id.desc())
        )
        if application is None:
            return None
        rows = self._db.scalars(
            select(AppliedImportedRecord)
            .where(AppliedImportedRecord.data_application_run_id == application.id)
            .order_by(AppliedImportedRecord.created_at, AppliedImportedRecord.id)
        ).all()
        return DataReviewApplicationResult(
            review_session=review,
            dry_run=False,
            application=application,
            applied_records=[self._result_from_row(row) for row in rows],
            warnings=self._review_warnings(review.id),
        )

    def _latest_myprogress_mapping_counts(
        self,
        student_profile_id: UUID,
    ) -> tuple[UUID | None, int, int]:
        runs = self._db.scalars(
            select(DataImportRun)
            .where(
                DataImportRun.student_profile_id == student_profile_id,
                DataImportRun.import_type == DataImportType.DEGREE_AUDIT_EXPORT,
            )
            .order_by(DataImportRun.created_at.desc(), DataImportRun.id.desc())
        ).all()
        for run in runs:
            course_rows = [
                record
                for record in self._db.scalars(
                    select(ImportedRecord)
                    .where(ImportedRecord.data_import_run_id == run.id)
                    .order_by(ImportedRecord.row_number, ImportedRecord.id)
                ).all()
                if record.normalized_payload.get("record_kind") == "MY_PROGRESS_COURSE_ROW"
            ]
            if not course_rows:
                continue
            mapped_count = sum(
                1
                for record in course_rows
                if self._db.scalar(
                    select(func.count())
                    .select_from(ImportMappingCandidate)
                    .where(
                        ImportMappingCandidate.imported_record_id == record.id,
                        ImportMappingCandidate.target_entity_type == ImportTargetEntityType.COURSE,
                        ImportMappingCandidate.target_entity_id.is_not(None),
                        ImportMappingCandidate.is_selected.is_(True),
                    )
                )
            )
            return run.id, mapped_count, len(course_rows) - mapped_count
        return None, 0, 0

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
        catalog_course_result = self._catalog_course_application_result(
            application_id,
            run,
            record_review,
            record,
            dry_run=dry_run,
        )
        if catalog_course_result is not None:
            return catalog_course_result
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

    def _catalog_course_application_result(
        self,
        application_id: UUID | None,
        run: DataImportRun,
        record_review: ImportedRecordReview,
        record: ImportedRecord,
        *,
        dry_run: bool,
    ) -> AppliedImportedRecordResult | None:
        if (
            run.import_type is not DataImportType.COURSE_CATALOG
            or record.record_type is not ImportedRecordType.COURSE
        ):
            return None
        payload = self._review_payload(record_review, record)
        normalized_code = normalize_course_code(str(payload.get("course_code") or ""))
        split = split_course_code(normalized_code)
        if split is None:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "CATALOG_COURSE_IDENTITY_INVALID",
                "Reviewed Catalog row does not contain a valid source Course code.",
                target_entity_type=AppliedImportTargetEntityType.COURSE,
            )
        subject_code, course_number = split
        normalized_code = f"{subject_code} {course_number}"
        title = str(payload.get("course_title") or payload.get("title") or "").strip()
        if not title:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "CATALOG_COURSE_TITLE_MISSING",
                "Reviewed Catalog row is missing the source Course title.",
                target_entity_type=AppliedImportTargetEntityType.COURSE,
            )
        credits = self._parse_credits(payload.get("credits"))
        if credits is None or credits <= 0:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "CATALOG_COURSE_CREDITS_INVALID",
                "Reviewed Catalog row is missing a positive source credit value.",
                target_entity_type=AppliedImportTargetEntityType.COURSE,
            )

        student = self._db.get(StudentProfile, run.student_profile_id)
        if student is None:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.FAILED,
                "CATALOG_STUDENT_CONTEXT_MISSING",
                "Catalog Course provisioning requires an existing student institution context.",
                target_entity_type=AppliedImportTargetEntityType.COURSE,
            )
        course = self._db.scalar(
            select(Course).where(
                Course.institution_id == student.home_institution_id,
                Course.subject_code == subject_code,
                Course.course_number == course_number,
            )
        )
        if course is not None and (course.is_official or course.source_type is SourceType.MOCK):
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "CONFLICT_OFFICIAL_OR_MOCK_COURSE",
                "Reviewed Catalog Apply never overwrites an official or mock Course.",
                course.id,
                target_entity_type=AppliedImportTargetEntityType.COURSE,
            )
        if course is not None and course.source_type not in {
            SourceType.BROWSER_EXTENSION,
            SourceType.IMPORTED,
        }:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "CONFLICT_UNRELATED_COURSE_SOURCE",
                "An unrelated Course source requires explicit conflict review.",
                course.id,
                target_entity_type=AppliedImportTargetEntityType.COURSE,
            )

        description = self._catalog_optional_text(payload.get("description"))
        course_level = self._catalog_course_level(payload)
        repeatable = self._catalog_repeatable(payload)
        conflicting_fields: list[str] = []
        if course is not None:
            if course.title != title:
                conflicting_fields.append("title")
            if course.credits_min != credits or course.credits_max != credits:
                conflicting_fields.append("credits")
            if description is not None and course.description != description:
                conflicting_fields.append("description")
            if (
                course_level is not None
                and course.course_level_verified
                and course.course_level != course_level
            ):
                conflicting_fields.append("course_level")
            if (
                repeatable is not None
                and course.repeatable_verified
                and course.repeatable != repeatable
            ):
                conflicting_fields.append("repeatable")
        if conflicting_fields:
            return self._outcome(
                application_id,
                record_review,
                AppliedImportAction.SKIPPED_UNSUPPORTED,
                AppliedImportStatus.SKIPPED,
                "CONFLICT_CATALOG_COURSE_EVIDENCE",
                (
                    "Reviewed Catalog evidence conflicts with the existing Course fields: "
                    f"{', '.join(conflicting_fields)}. Catalog version evidence or explicit "
                    "conflict resolution is required before an update."
                ),
                course.id if course is not None else None,
                target_entity_type=AppliedImportTargetEntityType.COURSE,
            )

        action = AppliedImportAction.CREATED if course is None else AppliedImportAction.UPDATED
        if dry_run:
            reason = (
                "WOULD_CREATE_IMPORTED_COURSE" if course is None else "WOULD_UPDATE_IMPORTED_COURSE"
            )
            return self._outcome(
                application_id,
                record_review,
                action,
                AppliedImportStatus.SUCCESS,
                reason,
                (
                    "Dry run would provision the exact reviewed Catalog Course identity. "
                    "Requisite text remains manual-confirmation evidence and is not activated."
                ),
                course.id if course is not None else None,
                target_entity_type=AppliedImportTargetEntityType.COURSE,
            )

        source_reference = self._catalog_course_source_reference(run, normalized_code)
        if course is None:
            course = Course(
                id=uuid4(),
                institution_id=student.home_institution_id,
                subject_code=subject_code,
                course_number=course_number,
                title=title,
                description=description,
                credits_min=credits,
                credits_max=credits,
                course_level=course_level if course_level is not None else 0,
                repeatable=repeatable if repeatable is not None else False,
                course_level_verified=course_level is not None,
                repeatable_verified=repeatable is not None,
                source_type=run.source_type,
                is_official=False,
                source_reference=source_reference,
                source_retrieved_at=run.source_retrieved_at or run.created_at,
                source_confidence=(
                    "reviewed_catalog"
                    if course_level is not None and repeatable is not None
                    else "reviewed_catalog_partial"
                ),
            )
            self._db.add(course)
            self._db.flush()
            reason = "CREATED_IMPORTED_COURSE"
        else:
            course.title = title
            if description is not None:
                course.description = description
            course.credits_min = credits
            course.credits_max = credits
            if course_level is not None:
                course.course_level = course_level
                course.course_level_verified = True
            if repeatable is not None:
                course.repeatable = repeatable
                course.repeatable_verified = True
            course.source_reference = source_reference
            course.source_retrieved_at = run.source_retrieved_at or run.created_at
            course.source_confidence = (
                "reviewed_catalog"
                if course.course_level_verified and course.repeatable_verified
                else "reviewed_catalog_partial"
            )
            reason = "UPDATED_IMPORTED_COURSE"
        self._reconcile_exact_course_mappings(run, course)
        return self._outcome(
            application_id,
            record_review,
            action,
            AppliedImportStatus.SUCCESS,
            reason,
            (
                "Provisioned one non-official internal Course from an explicitly reviewed Catalog "
                "identity; unsupported requisite text remains manual-confirmation evidence."
            ),
            course.id,
            target_entity_type=AppliedImportTargetEntityType.COURSE,
        )

    def _catalog_course_level(self, payload: dict[str, object]) -> int | None:
        raw = str(payload.get("course_level") or "").strip()
        try:
            level = int(raw)
        except ValueError:
            return None
        return level if level >= 0 else None

    def _catalog_optional_text(self, value: object) -> str | None:
        text = self._optional_text(value)
        return None if text == "NOT_PROVIDED" else text

    def _catalog_repeatable(self, payload: dict[str, object]) -> bool | None:
        value = payload.get("repeatable")
        if isinstance(value, bool):
            return value
        normalized = str(value or "").strip().casefold()
        if normalized in {"true", "yes", "1", "repeatable"}:
            return True
        if normalized in {"false", "no", "0", "not repeatable"}:
            return False
        return None

    def _catalog_course_source_reference(self, run: DataImportRun, course_code: str) -> str:
        source = (run.source_reference or "reviewed Catalog import")[:430]
        return f"{source}#course={quote(course_code, safe='')}"

    def _execute_myprogress_remap(
        self,
        run: DataImportRun,
        application: DataReviewApplicationResult,
    ) -> bool:
        course_ids = sorted(
            {
                result.target_entity_id
                for result in application.applied_records
                if result.status is AppliedImportStatus.SUCCESS
                and result.target_entity_type is AppliedImportTargetEntityType.COURSE
                and result.target_entity_id is not None
            },
            key=str,
        )
        courses = [
            course
            for course_id in course_ids
            if (course := self._db.get(Course, course_id)) is not None
        ]
        latest_myprogress_run = self._db.scalar(
            select(DataImportRun)
            .where(
                DataImportRun.student_profile_id == run.student_profile_id,
                DataImportRun.import_type == DataImportType.DEGREE_AUDIT_EXPORT,
            )
            .order_by(DataImportRun.created_at.desc(), DataImportRun.id.desc())
        )
        if latest_myprogress_run is None or not courses:
            return True

        records = self._db.scalars(
            select(ImportedRecord)
            .where(ImportedRecord.data_import_run_id == latest_myprogress_run.id)
            .order_by(ImportedRecord.row_number, ImportedRecord.id)
        ).all()
        courses_by_identity = {
            (course.subject_code, course.course_number): course for course in courses
        }
        for record in records:
            if record.normalized_payload.get("record_kind") != "MY_PROGRESS_COURSE_ROW":
                continue
            identity = split_course_code(str(record.normalized_payload.get("course_code") or ""))
            course = courses_by_identity.get(identity) if identity is not None else None
            if course is not None:
                self._select_exact_course_mapping(record, course)
        self._db.flush()
        return True

    def _reconcile_exact_course_mappings(self, run: DataImportRun, course: Course) -> None:
        records = self._db.scalars(
            select(ImportedRecord)
            .join(DataImportRun, ImportedRecord.data_import_run_id == DataImportRun.id)
            .where(DataImportRun.student_profile_id == run.student_profile_id)
            .order_by(ImportedRecord.created_at, ImportedRecord.id)
        ).all()
        expected_identity = (course.subject_code, course.course_number)
        for record in records:
            if split_course_code(str(record.normalized_payload.get("course_code") or "")) != (
                expected_identity
            ):
                continue
            self._select_exact_course_mapping(record, course)

    def _select_exact_course_mapping(self, record: ImportedRecord, course: Course) -> None:
        candidates = self._db.scalars(
            select(ImportMappingCandidate)
            .where(ImportMappingCandidate.imported_record_id == record.id)
            .order_by(ImportMappingCandidate.created_at, ImportMappingCandidate.id)
        ).all()
        selected = next((candidate for candidate in candidates if candidate.is_selected), None)
        if (
            selected is not None
            and selected.target_entity_type is ImportTargetEntityType.COURSE
            and selected.target_entity_id not in {None, course.id}
        ):
            return
        mapping = next(
            (
                candidate
                for candidate in candidates
                if candidate.target_entity_type is ImportTargetEntityType.COURSE
                and candidate.target_entity_id == course.id
            ),
            None,
        )
        if mapping is None:
            mapping = ImportMappingCandidate(
                id=uuid4(),
                imported_record_id=record.id,
                target_entity_type=ImportTargetEntityType.COURSE,
                target_entity_id=course.id,
                match_type=ImportMatchType.EXACT_CODE,
                confidence_score=Decimal("1.00"),
                is_selected=True,
                reason_code="REVIEWED_CATALOG_COURSE_IDENTITY",
                explanation=(
                    f"{course.subject_code} {course.course_number} exactly matches the "
                    "explicitly reviewed Catalog Course identity."
                ),
            )
            self._db.add(mapping)
            self._db.flush()
        else:
            mapping.is_selected = True
        for candidate in candidates:
            if candidate.id != mapping.id:
                candidate.is_selected = False
        if record.status is ImportedRecordStatus.AMBIGUOUS:
            record.status = ImportedRecordStatus.VALID_WITH_WARNINGS

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
                    source_reference=self._section_source_reference(run, payload),
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
                section.source_reference = self._section_source_reference(run, payload)
                section.source_retrieved_at = run.created_at
                section.source_confidence = "reviewed_import"
                action = AppliedImportAction.UPDATED
                reason = "UPDATED_IMPORTED_SECTION"
                message_prefix = "Updated same-source non-official imported Section."
            meeting_message = self._apply_section_meetings(section, payload, run)
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

    def _section_source_reference(
        self,
        run: DataImportRun,
        payload: dict[str, object],
    ) -> str:
        term_code = str(payload.get("term") or payload.get("term_code") or "").strip()
        course_code = str(payload.get("course_code") or "")
        section_code = str(payload.get("section_code") or "").strip()
        suffix = canonical_section_source_locator(
            term_code=term_code,
            course_code=course_code,
            section_code=section_code,
        )
        source = run.source_reference or "reviewed Section import"
        return f"{source[: max(0, 500 - len(suffix))]}{suffix}"

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
                        f"{self._section_source_reference(run, payload)}#meeting={index}"
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
