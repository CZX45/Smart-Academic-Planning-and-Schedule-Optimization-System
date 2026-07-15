from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import (
    AppliedImportedRecord,
    AppliedImportStatus,
    AppliedImportTargetEntityType,
    DataApplicationRun,
    DataApplicationStatus,
    DataImportReviewSession,
    DataImportReviewStatus,
    DataImportRun,
    DataImportStatus,
    DataImportType,
    ImportedRecord,
    ImportedRecordReview,
    ImportedRecordReviewDecision,
    ImportedRecordStatus,
    ImportedRecordType,
    Section,
    SectionMeeting,
    SectionModality,
    SectionStatus,
    StudentProfile,
)

REVIEWED_DECISIONS = {
    ImportedRecordReviewDecision.CONFIRMED,
    ImportedRecordReviewDecision.EDITED_AND_CONFIRMED,
}
APPLIED_RUN_STATUSES = {
    DataApplicationStatus.APPLIED,
    DataApplicationStatus.APPLIED_WITH_WARNINGS,
}
APPLIED_REVIEW_STATUSES = {
    DataImportReviewStatus.APPLIED,
    DataImportReviewStatus.APPLIED_WITH_WARNINGS,
}


@dataclass(frozen=True)
class SectionProvenance:
    import_id: UUID
    application_run_id: UUID
    review_session_id: UUID
    imported_record_id: UUID
    extraction_at: datetime | None
    import_created_at: datetime
    review_completed_at: datetime | None
    application_completed_at: datetime | None


@dataclass(frozen=True)
class SectionEligibility:
    eligible: bool
    reason_codes: tuple[str, ...]
    warnings: tuple[str, ...]
    provenance: SectionProvenance | None
    meetings_complete: bool
    has_tba_or_arranged: bool
    source_age_minutes: int | None


def evaluate_reviewed_section(
    db: Session,
    *,
    section: Section,
    student: StudentProfile,
    target_term_id: UUID,
    requested_course_id: UUID,
    now: datetime,
    maximum_source_age_minutes: int | None = None,
) -> SectionEligibility:
    reasons: list[str] = []
    warnings: list[str] = []
    if section.institution_id != student.home_institution_id:
        reasons.append("SECTION_INSTITUTION_MISMATCH")
    if section.term_id != target_term_id:
        reasons.append("SECTION_TERM_MISMATCH")
    if section.course_id != requested_course_id:
        reasons.append("SECTION_COURSE_MISMATCH")
    if section.is_official:
        reasons.append("SECTION_OFFICIAL")
    if section.source_type.name == "MOCK":
        reasons.append("ONLY_MOCK_SECTIONS_AVAILABLE")
    if not section.section_code.strip():
        reasons.append("SECTION_IDENTITY_CONFLICT")
    if section.status is SectionStatus.CANCELLED:
        reasons.append("SECTION_CANCELLED")
    if section.source_type.name not in {"BROWSER_EXTENSION", "IMPORTED"}:
        reasons.append("SECTION_PROVENANCE_MISSING")
    if section.source_confidence != "reviewed_import":
        reasons.append("SECTION_PROVENANCE_MISSING")

    rows = db.execute(
        select(
            AppliedImportedRecord,
            DataApplicationRun,
            ImportedRecordReview,
            DataImportReviewSession,
            ImportedRecord,
            DataImportRun,
        )
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
        .join(ImportedRecord, AppliedImportedRecord.imported_record_id == ImportedRecord.id)
        .join(DataImportRun, ImportedRecord.data_import_run_id == DataImportRun.id)
        .where(
            AppliedImportedRecord.target_entity_type == AppliedImportTargetEntityType.SECTION,
            AppliedImportedRecord.target_entity_id == section.id,
            AppliedImportedRecord.status.in_({AppliedImportStatus.SUCCESS}),
            DataApplicationRun.status.in_(APPLIED_RUN_STATUSES),
            ImportedRecordReview.decision.in_(REVIEWED_DECISIONS),
            DataImportReviewSession.status.in_(APPLIED_REVIEW_STATUSES),
            DataImportRun.student_profile_id == student.id,
            DataImportRun.import_type == DataImportType.SECTION_SCHEDULE,
            DataImportRun.status != DataImportStatus.FAILED,
            ImportedRecord.record_type == ImportedRecordType.SECTION,
            ImportedRecord.status.in_(
                {ImportedRecordStatus.VALID, ImportedRecordStatus.VALID_WITH_WARNINGS}
            ),
        )
        .order_by(AppliedImportedRecord.created_at.desc(), AppliedImportedRecord.id.desc())
    ).all()
    if len(rows) != 1:
        reasons.append(
            "SECTION_IDENTITY_CONFLICT" if len(rows) > 1 else "SECTION_SOURCE_NOT_APPLIED"
        )

    provenance: SectionProvenance | None = None
    payload: dict[str, object] = {}
    if rows:
        applied, application, record_review, review, record, run = rows[0]
        provenance = SectionProvenance(
            import_id=run.id,
            application_run_id=application.id,
            review_session_id=review.id,
            imported_record_id=record.id,
            extraction_at=section.source_retrieved_at,
            import_created_at=run.created_at,
            review_completed_at=review.completed_at,
            application_completed_at=application.completed_at,
        )
        candidate_payload = (
            record_review.edited_normalized_payload
            if record_review.edited_normalized_payload is not None
            else record.normalized_payload
        )
        payload = dict(candidate_payload)
        validation = str(
            payload.get("section_validation_state") or payload.get("validation_state") or ""
        ).upper()
        completeness = str(payload.get("completeness") or "").upper()
        if validation == "FAILED":
            reasons.append("SECTION_SOURCE_FAILED_VALIDATION")
        if completeness in {"UNCERTAIN", "TRUNCATED", "PARTIAL"}:
            reasons.append("SECTION_SOURCE_TRUNCATED")
        if payload.get("unsupported_layout") is True:
            reasons.append("SECTION_SOURCE_UNSUPPORTED_LAYOUT")
        if (
            section.source_reference is None
            or f"record={record.id}" not in section.source_reference
        ):
            reasons.append("SECTION_PROVENANCE_MISSING")

    meetings = db.scalars(
        select(SectionMeeting)
        .where(SectionMeeting.section_id == section.id)
        .order_by(SectionMeeting.display_order, SectionMeeting.id)
    ).all()
    has_tba = any(meeting.is_arranged or meeting.day_of_week is None for meeting in meetings)
    fixed_valid = all(
        meeting.is_arranged
        or meeting.is_online
        or (
            meeting.day_of_week is not None
            and meeting.start_time is not None
            and meeting.end_time is not None
            and meeting.end_time > meeting.start_time
        )
        for meeting in meetings
    )
    asynchronous = section.modality is SectionModality.ONLINE_ASYNCHRONOUS
    meetings_complete = bool(meetings) or asynchronous
    if not meetings_complete:
        reasons.append("SECTION_MEETINGS_INVALID")
    if not fixed_valid:
        reasons.append("SECTION_MEETINGS_INVALID")
    if has_tba:
        warnings.append("SECTION_TBA_OR_ARRANGED")

    source_age: int | None = None
    if section.source_retrieved_at is None:
        warnings.append("SOURCE_AGE_UNKNOWN")
    else:
        retrieved_at = section.source_retrieved_at
        if retrieved_at.tzinfo is None:
            retrieved_at = retrieved_at.replace(tzinfo=UTC)
        comparison_now = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
        source_age = max(0, int((comparison_now - retrieved_at).total_seconds() // 60))
        if maximum_source_age_minutes is not None and source_age > maximum_source_age_minutes:
            reasons.append("SECTION_SOURCE_TOO_OLD")

    return SectionEligibility(
        eligible=not reasons,
        reason_codes=tuple(sorted(set(reasons))),
        warnings=tuple(sorted(set(warnings))),
        provenance=provenance,
        meetings_complete=meetings_complete,
        has_tba_or_arranged=has_tba,
        source_age_minutes=source_age,
    )


def input_snapshot_hash(
    *,
    section_data_mode: str,
    student_id: UUID,
    institution_id: UUID,
    term_id: UUID,
    course_ids: list[UUID],
    section_ids: list[UUID],
    maximum_source_age_minutes: int | None,
) -> str:
    payload = {
        "section_data_mode": section_data_mode,
        "student_id": str(student_id),
        "institution_id": str(institution_id),
        "term_id": str(term_id),
        "course_ids": sorted(str(value) for value in course_ids),
        "section_ids": sorted(str(value) for value in section_ids),
        "maximum_source_age_minutes": maximum_source_age_minutes,
    }
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
