from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.models.academic import (
    AppliedImportAction,
    AppliedImportStatus,
    AppliedImportTargetEntityType,
    DataApplicationRun,
    DataImportReviewSession,
    DataReviewWarning,
)


@dataclass(frozen=True)
class AppliedImportedRecordResult:
    id: UUID | None
    data_application_run_id: UUID | None
    imported_record_review_id: UUID
    imported_record_id: UUID
    target_entity_type: AppliedImportTargetEntityType
    target_entity_id: UUID | None
    action: AppliedImportAction
    status: AppliedImportStatus
    reason_code: str
    message: str
    created_at: datetime | None


@dataclass(frozen=True)
class DataReviewApplicationResult:
    review_session: DataImportReviewSession
    dry_run: bool
    application: DataApplicationRun | None
    applied_records: list[AppliedImportedRecordResult]
    warnings: list[DataReviewWarning]
