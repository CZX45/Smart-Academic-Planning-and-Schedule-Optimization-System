from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.academic import (
    AcademicTerm,
    AuditWarningSeverity,
    Course,
    DataImportFile,
    DataImportRun,
    DataImportStatus,
    DataImportStorageStrategy,
    DataImportType,
    ImportedRecord,
    ImportedRecordStatus,
    ImportedRecordType,
    ImportMappingCandidate,
    ImportMatchType,
    ImportPreviewSummary,
    ImportTargetEntityType,
    ImportValidationWarning,
    SourceType,
    StudentProfile,
)
from app.services.data_imports.exceptions import DataImportValidationError
from app.services.data_imports.normalizers import split_course_code
from app.services.data_imports.parsers import ParsedImportRecord, parse_import_content

ENGINE_VERSION = "phase7a-data-import-v1"
MAX_IMPORT_CONTENT_BYTES = 64 * 1024
MAX_BROWSER_EXTENSION_IMPORT_CONTENT_BYTES = 512 * 1024
STAGING_DISCLAIMERS = [
    "This import preview is staging-only and is not official school policy.",
    (
        "Imported records are mock, student-provided, or otherwise unreviewed "
        "until a school or advisor confirms them."
    ),
    (
        "Phase 7A does not change official course, section, requirement, "
        "transcript, registration, seat, waitlist, or advisor-approval records."
    ),
]
BROWSER_EXTENSION_STAGING_DISCLAIMERS = [
    (
        "Browser extension imports are staging-only visible-page extracts and are not official "
        "school policy."
    ),
    (
        "Browser extension imports are user-triggered and cannot bypass Phase 7B review before "
        "application."
    ),
    (
        "Phase 7B review is required before any browser-extension import can update internal "
        "planning records."
    ),
]
KEAN_SOURCE_LABEL = "KEAN_STUDENT_PORTAL"
KEAN_STUDENT_PORTAL_PREFIX = "https://kean-ss.colleague.elluciancloud.com/Student"
KEAN_STUDENT_PORTAL_DISCLAIMERS = [
    (
        "Kean Student Portal browser-extension imports are user-authorized, "
        "non-official academic-planning extracts."
    ),
    (
        "Kean Student Portal import rows still require Phase 7B review before "
        "they can be used by planning workflows."
    ),
]
logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class DataImportApplicationService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_import(
        self,
        *,
        student_profile_id: UUID,
        import_type: DataImportType,
        file_name: str,
        file_mime_type: str,
        content: str,
        source_type: SourceType = SourceType.STUDENT_PROVIDED,
        source_reference: str | None = None,
    ) -> DataImportRun:
        student = self._validate_import_request(
            student_profile_id=student_profile_id,
            source_type=source_type,
            file_name=file_name,
            file_mime_type=file_mime_type,
            content=content,
        )
        encoded = content.encode("utf-8")
        parsed_records = parse_import_content(
            import_type=import_type,
            file_name=file_name,
            file_mime_type=file_mime_type,
            content=content,
        )
        run = DataImportRun(
            id=uuid4(),
            student_profile_id=student.id,
            import_type=import_type,
            status=DataImportStatus.PARSING,
            storage_strategy=DataImportStorageStrategy.METADATA_ONLY,
            file_name=file_name,
            file_mime_type=file_mime_type,
            file_size_bytes=len(encoded),
            file_sha256=hashlib.sha256(encoded).hexdigest(),
            parser_version=ENGINE_VERSION,
            record_count=0,
            valid_record_count=0,
            warning_count=0,
            error_count=0,
            official_application_ready=False,
            started_at=utc_now(),
            source_type=source_type,
            is_official=False,
            source_reference=source_reference,
            source_confidence=source_type.value.lower(),
        )
        self._db.add(run)
        self._db.flush()
        self._db.add(
            DataImportFile(
                id=uuid4(),
                data_import_run_id=run.id,
                storage_strategy=DataImportStorageStrategy.METADATA_ONLY,
                file_name=file_name,
                file_mime_type=file_mime_type,
                file_size_bytes=len(encoded),
                file_sha256=run.file_sha256,
                content_preview=content[:500],
            )
        )
        if not self._is_auto_verified_myprogress_import(parsed_records):
            self._add_warning(
                run.id,
                None,
                "STAGING_ONLY_NOT_OFFICIAL",
                AuditWarningSeverity.WARNING,
                (
                    "Phase 7A imports are preview-only staging records and are not official school "
                    "policy or transcript data."
                ),
            )

        for parsed_record in parsed_records:
            record_status, confidence = self._record_status(parsed_record)

            imported_record = ImportedRecord(
                id=uuid4(),
                data_import_run_id=run.id,
                record_type=parsed_record.record_type,
                row_number=parsed_record.row_number,
                status=record_status,
                external_identifier=parsed_record.external_identifier,
                raw_label=parsed_record.raw_label,
                normalized_payload=parsed_record.normalized_payload,
                confidence_score=confidence,
            )
            self._db.add(imported_record)
            self._db.flush()
            if self._should_match_course_candidate(parsed_record):
                self._persist_mapping_candidates(student, imported_record, parsed_record)
            if self._is_myprogress_record(parsed_record):
                self._persist_myprogress_mapping_candidate(
                    student,
                    imported_record,
                    parsed_record,
                )
                self._add_myprogress_record_warnings(imported_record, parsed_record)

        if not parsed_records:
            self._add_warning(
                run.id,
                None,
                "NO_IMPORT_RECORDS",
                AuditWarningSeverity.WARNING,
                "No importable records were found in the uploaded content.",
            )

        self._db.flush()
        warning_count = self._warning_count(run.id)
        run.record_count = len(parsed_records)
        run.valid_record_count = self._record_count(
            run.id,
            {ImportedRecordStatus.VALID, ImportedRecordStatus.VALID_WITH_WARNINGS},
        )
        run.warning_count = warning_count
        run.error_count = self._record_count(run.id, {ImportedRecordStatus.INVALID})
        run.status = (
            DataImportStatus.PARSED_WITH_WARNINGS if warning_count else DataImportStatus.PARSED
        )
        run.completed_at = utc_now()
        self._persist_preview(run)
        self._db.commit()
        self._db.refresh(run)
        logger.info(
            "data_import.created",
            extra={
                "data_import_run_id": str(run.id),
                "student_profile_id": str(run.student_profile_id),
                "source_type": run.source_type.value,
                "import_type": run.import_type.value,
                "record_count": run.record_count,
                "warning_count": run.warning_count,
                "error_count": run.error_count,
                "file_size_bytes": run.file_size_bytes,
            },
        )
        return run

    def validate_import(self, data_import_run_id: UUID) -> ImportPreviewSummary:
        run = self._get_run(data_import_run_id)
        summary = self._db.scalar(
            select(ImportPreviewSummary).where(
                ImportPreviewSummary.data_import_run_id == data_import_run_id
            )
        )
        if summary is None:
            summary = self._persist_preview(run)
            self._db.commit()
            self._db.refresh(summary)
        return summary

    def _validate_import_request(
        self,
        *,
        student_profile_id: UUID,
        source_type: SourceType,
        file_name: str,
        file_mime_type: str,
        content: str,
    ) -> StudentProfile:
        student = self._db.get(StudentProfile, student_profile_id)
        if student is None:
            raise DataImportValidationError(
                "not_found",
                f"StudentProfile {student_profile_id} was not found.",
            )
        if source_type is SourceType.OFFICIAL:
            raise DataImportValidationError(
                "read_only_source",
                "Phase 7A data import is read-only and cannot accept official-source imports.",
            )
        if not file_name.strip():
            raise DataImportValidationError("invalid_file_name", "file_name cannot be empty.")
        if not file_mime_type.strip():
            raise DataImportValidationError("invalid_file_mime_type", "file_mime_type is required.")
        max_content_bytes = (
            MAX_BROWSER_EXTENSION_IMPORT_CONTENT_BYTES
            if source_type is SourceType.BROWSER_EXTENSION
            else MAX_IMPORT_CONTENT_BYTES
        )
        if len(content.encode("utf-8")) > max_content_bytes:
            raise DataImportValidationError(
                "import_too_large",
                "Phase 7A import content exceeded the safe staging size limit.",
            )
        if not content.strip():
            raise DataImportValidationError("empty_import", "Import content cannot be empty.")
        return student

    def _record_status(
        self,
        parsed_record: ParsedImportRecord,
    ) -> tuple[ImportedRecordStatus, Decimal]:
        if self._is_myprogress_record(parsed_record):
            if parsed_record.requires_review:
                has_error = self._myprogress_record_has_error(parsed_record)
                return (
                    ImportedRecordStatus.INVALID
                    if has_error
                    else ImportedRecordStatus.VALID_WITH_WARNINGS,
                    parsed_record.confidence_score,
                )
            return ImportedRecordStatus.VALID, parsed_record.confidence_score
        if not parsed_record.normalized_payload.get("course_code"):
            return ImportedRecordStatus.INVALID, Decimal("0.00")
        return ImportedRecordStatus.VALID_WITH_WARNINGS, Decimal("0.80")

    def _is_myprogress_record(self, parsed_record: ParsedImportRecord) -> bool:
        return parsed_record.normalized_payload.get("source_page_type") == "KEAN_MY_PROGRESS_PAGE"

    def _myprogress_record_has_error(self, parsed_record: ParsedImportRecord) -> bool:
        validation = parsed_record.normalized_payload.get("validation")
        if isinstance(validation, dict) and validation.get("status") == "FAILED":
            return True
        row_validation = parsed_record.normalized_payload.get("row_validation")
        if isinstance(row_validation, dict) and row_validation.get("reason_codes"):
            return True
        return False

    def _should_match_course_candidate(self, parsed_record: ParsedImportRecord) -> bool:
        return not self._is_myprogress_record(parsed_record)

    def _persist_myprogress_mapping_candidate(
        self,
        student: StudentProfile,
        imported_record: ImportedRecord,
        parsed_record: ParsedImportRecord,
    ) -> None:
        payload = parsed_record.normalized_payload
        if payload.get("record_kind") != "MY_PROGRESS_COURSE_ROW":
            return
        course_code = str(payload.get("course_code") or "").strip() or None
        split = split_course_code(course_code)
        if split is None:
            self._add_no_match(imported_record, course_code, "COURSE_CODE_MISSING")
            return
        subject_code, course_number = split
        course = self._db.scalar(
            select(Course).where(
                Course.institution_id == student.home_institution_id,
                Course.subject_code == subject_code,
                Course.course_number == course_number,
            )
        )
        if course is None:
            self._add_no_match(imported_record, course_code, "COURSE_CODE_UNMATCHED")
            return
        self._db.add(
            ImportMappingCandidate(
                id=uuid4(),
                imported_record_id=imported_record.id,
                target_entity_type=ImportTargetEntityType.COURSE,
                target_entity_id=course.id,
                match_type=ImportMatchType.EXACT_CODE,
                confidence_score=Decimal("1.00"),
                is_selected=True,
                reason_code="EXACT_COURSE_CODE",
                explanation=(
                    f"{course_code} exactly matches reviewed internal catalog course "
                    f"{course.subject_code} {course.course_number}."
                ),
            )
        )

    def _is_auto_verified_myprogress_import(
        self,
        parsed_records: list[ParsedImportRecord],
    ) -> bool:
        if not parsed_records:
            return False
        first = parsed_records[0]
        validation = first.normalized_payload.get("validation")
        return (
            self._is_myprogress_record(first)
            and isinstance(validation, dict)
            and validation.get("status") == "AUTO_VERIFIED"
        )

    def _persist_mapping_candidates(
        self,
        student: StudentProfile,
        imported_record: ImportedRecord,
        parsed_record: ParsedImportRecord,
    ) -> None:
        course_code = parsed_record.normalized_payload.get("course_code")
        split = split_course_code(course_code)
        if split is None:
            self._add_no_match(imported_record, course_code, "MISSING_COURSE_CODE")
            self._add_warning(
                imported_record.data_import_run_id,
                imported_record.id,
                "MISSING_COURSE_CODE",
                AuditWarningSeverity.ERROR,
                "The imported row did not include a recognizable course code.",
            )
            imported_record.status = ImportedRecordStatus.INVALID
            imported_record.confidence_score = Decimal("0.00")
            return

        subject_code, course_number = split
        course = self._db.scalar(
            select(Course).where(
                Course.institution_id == student.home_institution_id,
                Course.subject_code == subject_code,
                Course.course_number == course_number,
            )
        )
        if course is None:
            self._add_no_match(imported_record, course_code, "UNMATCHED_COURSE_CODE")
            self._add_warning(
                imported_record.data_import_run_id,
                imported_record.id,
                "UNMATCHED_COURSE_CODE",
                AuditWarningSeverity.WARNING,
                f"{course_code} is staged but did not match a reviewed course in the mock catalog.",
            )
            imported_record.status = ImportedRecordStatus.AMBIGUOUS
            imported_record.confidence_score = Decimal("0.35")
            return

        self._db.add(
            ImportMappingCandidate(
                id=uuid4(),
                imported_record_id=imported_record.id,
                target_entity_type=ImportTargetEntityType.COURSE,
                target_entity_id=course.id,
                match_type=ImportMatchType.EXACT_CODE,
                confidence_score=Decimal("1.00"),
                is_selected=True,
                reason_code="EXACT_COURSE_CODE",
                explanation=(
                    f"{course_code} exactly matches mock catalog course "
                    f"{course.subject_code} {course.course_number}."
                ),
            )
        )
        self._add_term_warning_if_needed(imported_record, parsed_record)

    def _add_term_warning_if_needed(
        self,
        imported_record: ImportedRecord,
        parsed_record: ParsedImportRecord,
    ) -> None:
        term_code = parsed_record.normalized_payload.get("term")
        if not term_code:
            return
        term = self._db.scalar(select(AcademicTerm).where(AcademicTerm.term_code == term_code))
        if term is None:
            self._add_warning(
                imported_record.data_import_run_id,
                imported_record.id,
                "UNMATCHED_TERM_CODE",
                AuditWarningSeverity.WARNING,
                f"{term_code} is staged but did not match a known mock academic term.",
            )

    def _add_no_match(
        self,
        imported_record: ImportedRecord,
        course_code: str | None,
        reason_code: str,
    ) -> None:
        label = course_code or "the imported row"
        self._db.add(
            ImportMappingCandidate(
                id=uuid4(),
                imported_record_id=imported_record.id,
                target_entity_type=ImportTargetEntityType.UNKNOWN,
                target_entity_id=None,
                match_type=ImportMatchType.NO_MATCH,
                confidence_score=Decimal("0.00"),
                is_selected=False,
                reason_code=reason_code,
                explanation=(
                    f"{label} did not match a reviewed internal catalog record and requires manual "
                    "review before academic use."
                ),
            )
        )

    def _add_warning(
        self,
        data_import_run_id: UUID,
        imported_record_id: UUID | None,
        warning_code: str,
        severity: AuditWarningSeverity,
        message: str,
    ) -> None:
        self._db.add(
            ImportValidationWarning(
                id=uuid4(),
                data_import_run_id=data_import_run_id,
                imported_record_id=imported_record_id,
                warning_code=warning_code,
                severity=severity,
                message=message,
                requires_advisor_confirmation=True,
            )
        )

    def _add_myprogress_record_warnings(
        self,
        imported_record: ImportedRecord,
        parsed_record: ParsedImportRecord,
    ) -> None:
        payload = parsed_record.normalized_payload
        extraction_warnings = payload.get("extractionWarnings")
        if isinstance(extraction_warnings, list):
            for warning in extraction_warnings:
                if not isinstance(warning, dict):
                    continue
                self._add_warning(
                    imported_record.data_import_run_id,
                    imported_record.id,
                    str(warning.get("code") or "MY_PROGRESS_IMPORT_WARNING"),
                    self._warning_severity(warning.get("severity")),
                    str(warning.get("message") or "MyProgress import warning."),
                )

        row_validation = payload.get("row_validation")
        if not isinstance(row_validation, dict):
            return
        for reason_code in row_validation.get("reason_codes") or []:
            self._add_warning(
                imported_record.data_import_run_id,
                imported_record.id,
                str(reason_code),
                AuditWarningSeverity.ERROR,
                f"MyProgress row {imported_record.row_number} requires review: {reason_code}.",
            )
        for warning_code in row_validation.get("warnings") or []:
            if warning_code == "BOUNDED_OR_TRUNCATED_EXTRACTION":
                continue
            self._add_warning(
                imported_record.data_import_run_id,
                imported_record.id,
                str(warning_code),
                AuditWarningSeverity.WARNING,
                f"MyProgress row {imported_record.row_number} has warning {warning_code}.",
            )

    def _warning_severity(self, value: object) -> AuditWarningSeverity:
        try:
            return AuditWarningSeverity(str(value))
        except ValueError:
            return AuditWarningSeverity.WARNING

    def _warning_count(self, data_import_run_id: UUID) -> int:
        return (
            self._db.scalar(
                select(func.count())
                .select_from(ImportValidationWarning)
                .where(ImportValidationWarning.data_import_run_id == data_import_run_id)
            )
            or 0
        )

    def _record_count(
        self,
        data_import_run_id: UUID,
        statuses: set[ImportedRecordStatus],
    ) -> int:
        return (
            self._db.scalar(
                select(func.count())
                .select_from(ImportedRecord)
                .where(
                    ImportedRecord.data_import_run_id == data_import_run_id,
                    ImportedRecord.status.in_(statuses),
                )
            )
            or 0
        )

    def _persist_preview(self, run: DataImportRun) -> ImportPreviewSummary:
        disclaimers = list(STAGING_DISCLAIMERS)
        if run.source_type is SourceType.BROWSER_EXTENSION:
            disclaimers.extend(BROWSER_EXTENSION_STAGING_DISCLAIMERS)
        source_label = self._source_label(run)
        if source_label == KEAN_SOURCE_LABEL:
            disclaimers.extend(KEAN_STUDENT_PORTAL_DISCLAIMERS)
        summary_payload: dict[str, object] = {
            "disclaimers": disclaimers,
            "supported_import_type": run.import_type.value,
            "storage_strategy": run.storage_strategy.value,
            "source_type": run.source_type.value,
            "staging_only": True,
        }
        if source_label is not None:
            summary_payload["source_label"] = source_label
        myprogress_payload = self._myprogress_preview_payload(run)
        if myprogress_payload is not None:
            summary_payload.update(myprogress_payload)
        summary = ImportPreviewSummary(
            id=uuid4(),
            data_import_run_id=run.id,
            record_count=run.record_count,
            valid_record_count=run.valid_record_count,
            warning_count=run.warning_count,
            error_count=run.error_count,
            official_application_ready=False,
            summary_payload=summary_payload,
        )
        self._db.add(summary)
        self._db.flush()
        return summary

    def _myprogress_preview_payload(self, run: DataImportRun) -> dict[str, object] | None:
        if run.import_type is not DataImportType.DEGREE_AUDIT_EXPORT:
            return None
        record = self._db.scalar(
            select(ImportedRecord)
            .where(
                ImportedRecord.data_import_run_id == run.id,
                ImportedRecord.record_type == ImportedRecordType.PROGRAM,
            )
            .order_by(ImportedRecord.row_number, ImportedRecord.id)
        )
        if record is None:
            return None
        payload = record.normalized_payload
        if payload.get("source_page_type") != "KEAN_MY_PROGRESS_PAGE":
            return None
        validation = payload.get("validation")
        validation_payload = validation if isinstance(validation, dict) else {}
        status = str(validation_payload.get("status") or "FAILED")
        exception_count = int(validation_payload.get("exceptionCount") or 0)
        downstream_allowed = bool(validation_payload.get("downstreamAnalysisAllowed"))
        real_import_status = (
            "REAL_IMPORTED_DATA_AUTO_VERIFIED"
            if status == "AUTO_VERIFIED"
            else "REAL_IMPORTED_DATA_REQUIRES_EXCEPTION_REVIEW"
            if exception_count > 0
            else "REAL_IMPORTED_DATA_PENDING_REVIEW"
        )
        return {
            "real_import_status": real_import_status,
            "mock_data_mixed_with_real_import": False,
            "can_apply_verified_import": status == "AUTO_VERIFIED",
            "downstream_analysis_allowed": downstream_allowed,
            "exception_count": exception_count,
            "exceptions": validation_payload.get("exceptions") or [],
            "auto_confirmed_field_count": int(
                validation_payload.get("autoConfirmedFieldCount") or 0
            ),
            "auto_confirmed_course_row_count": int(
                validation_payload.get("autoConfirmedCourseRowCount") or 0
            ),
            "overall_confidence_score": float(
                validation_payload.get("overallConfidenceScore") or 0
            ),
            "program_summary": payload.get("programSummary") or {},
            "credit_summary": payload.get("creditSummary") or {},
            "field_provenance": payload.get("fieldProvenance") or {},
            "progress_bar_segments": payload.get("progressBarSegments") or [],
            "requirement_groups": self._myprogress_requirement_groups(run),
            **self._myprogress_row_preview_payload(run, payload),
            "raw_snapshot": payload.get("rawSnapshot") or {},
        }

    def _myprogress_requirement_groups(self, run: DataImportRun) -> list[object]:
        records = self._db.scalars(
            select(ImportedRecord)
            .where(
                ImportedRecord.data_import_run_id == run.id,
                ImportedRecord.record_type == ImportedRecordType.REQUIREMENT,
            )
            .order_by(ImportedRecord.row_number, ImportedRecord.id)
        ).all()
        groups: list[object] = []
        for record in records:
            payload = record.normalized_payload
            if payload.get("source_page_type") != "KEAN_MY_PROGRESS_PAGE":
                continue
            group = payload.get("requirementGroup")
            if group is not None:
                groups.append(group)
        return groups

    def _myprogress_row_preview_payload(
        self,
        run: DataImportRun,
        program_payload: dict[str, object],
    ) -> dict[str, object]:
        raw_snapshot = program_payload.get("rawSnapshot")
        raw_snapshot_payload = raw_snapshot if isinstance(raw_snapshot, dict) else {}
        diagnostics = raw_snapshot_payload.get("diagnostics")
        diagnostics_payload = diagnostics if isinstance(diagnostics, dict) else {}
        course_rows = self._myprogress_course_rows(run)
        course_record_count = len(course_rows)
        exception_row_count = sum(1 for row in course_rows if row.get("requires_review") is True)
        parsed_course_like_row_count = course_record_count - exception_row_count
        extracted_row_count = self._int_value(
            diagnostics_payload.get("courseLikeRowCount"),
            fallback=self._int_value(
                diagnostics_payload.get("rowCount"), fallback=course_record_count
            ),
        )
        ignored_row_count = max(extracted_row_count - course_record_count, 0)
        extraction_bounded = bool(
            program_payload.get("extractionBounded") or diagnostics_payload.get("bounded")
        )
        extraction_truncated = bool(
            program_payload.get("extractionTruncated") or diagnostics_payload.get("truncated")
        )
        requirement_count = len(self._myprogress_requirement_groups(run))
        return {
            "extracted_degree_audit_row_count": extracted_row_count,
            "parsed_course_like_row_count": parsed_course_like_row_count,
            "parsed_requirement_row_count": requirement_count,
            "ignored_row_count": ignored_row_count,
            "exception_row_count": exception_row_count,
            "extraction_bounded": extraction_bounded,
            "extraction_truncated": extraction_truncated,
            "course_rows": course_rows,
            "readiness": self._myprogress_readiness(
                summary_auto_verified=self._myprogress_summary_auto_verified(program_payload),
                requirement_count=requirement_count,
                parsed_course_like_row_count=parsed_course_like_row_count,
                exception_row_count=exception_row_count,
                extraction_bounded=extraction_bounded,
                extraction_truncated=extraction_truncated,
            ),
        }

    def _myprogress_course_rows(self, run: DataImportRun) -> list[dict[str, object]]:
        records = self._db.scalars(
            select(ImportedRecord)
            .where(
                ImportedRecord.data_import_run_id == run.id,
                ImportedRecord.record_type == ImportedRecordType.REQUIREMENT,
            )
            .order_by(ImportedRecord.row_number, ImportedRecord.id)
        ).all()
        rows: list[dict[str, object]] = []
        for record in records:
            payload = record.normalized_payload
            if payload.get("record_kind") != "MY_PROGRESS_COURSE_ROW":
                continue
            row_validation = payload.get("row_validation")
            rows.append(
                {
                    "row_number": record.row_number,
                    "course_code": payload.get("course_code") or "",
                    "course_title": payload.get("title") or "",
                    "term": payload.get("term") or "",
                    "status": payload.get("status") or "",
                    "requirement_group_context": payload.get("requirement_group_context") or "",
                    "raw_row_text": payload.get("raw_row_text") or "",
                    "source_table_index": payload.get("source_table_index") or "",
                    "source_row_index": payload.get("source_row_index") or "",
                    "source_field_provenance": payload.get("source_field_provenance") or {},
                    "confidence": str(record.confidence_score),
                    "warnings": payload.get("row_warnings") or [],
                    "requires_review": payload.get("requiresReview") is True,
                    "reason_codes": row_validation.get("reason_codes", [])
                    if isinstance(row_validation, dict)
                    else [],
                }
            )
        return rows

    def _myprogress_readiness(
        self,
        *,
        summary_auto_verified: bool,
        requirement_count: int,
        parsed_course_like_row_count: int,
        exception_row_count: int,
        extraction_bounded: bool,
        extraction_truncated: bool,
    ) -> dict[str, object]:
        course_rows_partial = (
            parsed_course_like_row_count == 0
            or exception_row_count > 0
            or extraction_bounded
            or extraction_truncated
        )
        return {
            "summary": {
                "status": "AUTO_VERIFIED" if summary_auto_verified else "REQUIRES_REVIEW",
                "reason_codes": []
                if summary_auto_verified
                else ["MY_PROGRESS_SUMMARY_NOT_VERIFIED"],
            },
            "requirement_summary": {
                "status": "APPLIED_OR_READY" if requirement_count > 0 else "MISSING",
                "reason_codes": []
                if requirement_count > 0
                else ["MY_PROGRESS_REQUIREMENTS_MISSING"],
            },
            "course_rows": {
                "status": "PARTIAL_REQUIRES_REVIEW" if course_rows_partial else "READY",
                "reason_codes": [
                    *(
                        ["BOUNDED_OR_TRUNCATED_EXTRACTION"]
                        if extraction_bounded or extraction_truncated
                        else []
                    ),
                    *(["COURSE_ROW_EXCEPTIONS_PRESENT"] if exception_row_count > 0 else []),
                    *(["NO_COURSE_ROWS_PARSED"] if parsed_course_like_row_count == 0 else []),
                ],
            },
            "planner": {
                "status": "BLOCKED" if course_rows_partial else "WARNING",
                "reason_codes": ["WAITING_FOR_RELIABLE_MYPROGRESS_COURSE_ROWS"]
                if course_rows_partial
                else ["IMPORTED_ROWS_NEED_ADVISOR_CONFIRMATION"],
            },
            "course_eligibility": {
                "status": "DEMO_ONLY",
                "reason_codes": ["REAL_COURSE_HISTORY_NOT_READY"],
            },
            "schedule_builder": {
                "status": "DEMO_ONLY",
                "reason_codes": ["REAL_SECTION_SEARCH_DATA_NOT_IMPORTED"],
            },
        }

    def _myprogress_summary_auto_verified(self, payload: dict[str, object]) -> bool:
        validation = payload.get("validation")
        return isinstance(validation, dict) and validation.get("status") == "AUTO_VERIFIED"

    def _int_value(self, value: object, *, fallback: int) -> int:
        if value is None:
            return fallback
        if isinstance(value, int):
            return value
        if isinstance(value, float | str | bytes | bytearray):
            candidate: float | str | bytes | bytearray = value
        else:
            return fallback
        try:
            return int(candidate)
        except (TypeError, ValueError):
            return fallback

    def _source_label(self, run: DataImportRun) -> str | None:
        reference = run.source_reference or ""
        if KEAN_SOURCE_LABEL in reference or KEAN_STUDENT_PORTAL_PREFIX in reference:
            return KEAN_SOURCE_LABEL
        return None

    def _get_run(self, data_import_run_id: UUID) -> DataImportRun:
        run = self._db.get(DataImportRun, data_import_run_id)
        if run is None:
            raise DataImportValidationError(
                "not_found",
                f"DataImportRun {data_import_run_id} was not found.",
            )
        return run
