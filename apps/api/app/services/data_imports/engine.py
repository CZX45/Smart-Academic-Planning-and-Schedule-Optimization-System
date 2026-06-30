from __future__ import annotations

import hashlib
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
            self._persist_mapping_candidates(student, imported_record, parsed_record)

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
        if len(content.encode("utf-8")) > MAX_IMPORT_CONTENT_BYTES:
            raise DataImportValidationError(
                "import_too_large",
                "Phase 7A mock/user-provided import content is limited to 64KB.",
            )
        if not content.strip():
            raise DataImportValidationError("empty_import", "Import content cannot be empty.")
        return student

    def _record_status(
        self,
        parsed_record: ParsedImportRecord,
    ) -> tuple[ImportedRecordStatus, Decimal]:
        if not parsed_record.normalized_payload.get("course_code"):
            return ImportedRecordStatus.INVALID, Decimal("0.00")
        return ImportedRecordStatus.VALID_WITH_WARNINGS, Decimal("0.80")

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
                    f"{label} did not match a reviewed mock catalog record and requires manual "
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
        summary = ImportPreviewSummary(
            id=uuid4(),
            data_import_run_id=run.id,
            record_count=run.record_count,
            valid_record_count=run.valid_record_count,
            warning_count=run.warning_count,
            error_count=run.error_count,
            official_application_ready=False,
            summary_payload={
                "disclaimers": disclaimers,
                "supported_import_type": run.import_type.value,
                "storage_strategy": run.storage_strategy.value,
                "source_type": run.source_type.value,
                "staging_only": True,
            },
        )
        self._db.add(summary)
        self._db.flush()
        return summary

    def _get_run(self, data_import_run_id: UUID) -> DataImportRun:
        run = self._db.get(DataImportRun, data_import_run_id)
        if run is None:
            raise DataImportValidationError(
                "not_found",
                f"DataImportRun {data_import_run_id} was not found.",
            )
        return run
