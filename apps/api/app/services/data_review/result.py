from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.models.academic import (
    AppliedImportAction,
    AppliedImportStatus,
    AppliedImportTargetEntityType,
    CourseStateSnapshot,
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
    course_state_snapshot: CourseStateSnapshot | None = None


@dataclass(frozen=True)
class CatalogBatchProcessingResult:
    status: Literal["APPLIED", "BLOCKED"]
    review_session: DataImportReviewSession
    dry_run: DataReviewApplicationResult | None
    application: DataReviewApplicationResult | None
    confirmed_record_count: int
    blocked_record_count: int
    reason_codes: list[str]
    myprogress_run_id: UUID | None
    myprogress_mapped_count: int
    myprogress_unmatched_count: int
    processing_stages_completed: list[str]
    staged_record_count: int
    review_valid_count: int
    review_warning_count: int
    applied_record_count: int
    myprogress_total_count: int
    myprogress_mapped_before_count: int
    myprogress_remap_executed: bool = False
    already_processed: bool = False
    provider_actions_written: Literal["NO"] = "NO"
