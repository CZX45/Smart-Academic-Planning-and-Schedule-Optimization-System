from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DiagnosticStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"
    NOT_RUN = "NOT_RUN"
    TIMED_OUT = "TIMED_OUT"
    ERROR = "ERROR"


class OverallStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RuntimeHealth(StrictModel):
    status: DiagnosticStatus
    reason_code: str | None = None
    summary: str
    current_mode: Literal["LOCAL_DESKTOP", "SERVER"]
    manifest_present: bool
    manifest_contract_supported: bool | None
    manifest_parseable: bool | None
    pid_valid: bool | None
    api_base_url_loopback: bool | None
    port_valid: bool | None
    stale: bool | None
    process_consistent: bool | None
    conflict_detected: bool


class ApiHealth(StrictModel):
    status: DiagnosticStatus
    reason_code: str | None = None
    summary: str
    process_status: Literal["RUNNING", "NOT_RUNNING", "UNKNOWN"]
    readiness_status: Literal["READY", "NOT_READY", "UNKNOWN"]
    health_status: Literal["HEALTHY", "UNHEALTHY", "UNKNOWN"]
    api_contract_version: str
    application_mode: Literal["LOCAL_DESKTOP", "SERVER"]
    loopback_bound: bool
    expected_database: Literal["SQLITE", "POSTGRESQL", "UNKNOWN"]
    schema_match: bool | None
    recent_child_process_exit: str | None


class DatabaseHealth(StrictModel):
    status: DiagnosticStatus
    reason_code: str | None = None
    summary: str
    present: bool
    readable: bool
    sqlite_header_valid: bool | None
    foreign_keys_status: DiagnosticStatus
    integrity_check_status: DiagnosticStatus
    foreign_key_check_status: DiagnosticStatus
    schema_version: int | None
    supported_schema_version: int
    schema_version_supported: bool | None
    journal_mode: str | None
    sidecar_wal_present: bool
    sidecar_shm_present: bool
    sidecar_journal_present: bool
    operation_state: Literal["NONE_DETECTED", "SIDECAR_PRESENT", "UNKNOWN"]
    size_bucket: Literal["<1 MB", "1-10 MB", "10-100 MB", ">100 MB", "UNKNOWN"]


class MigrationHealth(StrictModel):
    status: DiagnosticStatus
    reason_code: str | None = None
    summary: str
    current_schema_version: int | None
    supported_schema_version: int
    schema_status: str
    migration_required: bool | None
    migration_in_progress: bool
    last_attempt_status: str | None
    last_successful_migration: datetime | None
    last_rollback_status: str | None
    interrupted_attempt_detected: bool
    safety_backup_reference_exists: bool | None
    blocking_reason_code: str | None
    recovery_action_category: Literal[
        "NONE", "REVIEW", "RECOVERY_PREFLIGHT", "ADVISOR_CONFIRMATION", "UNKNOWN"
    ]


class RestoreHealth(StrictModel):
    status: DiagnosticStatus
    reason_code: str | None = None
    summary: str
    backup_capability_available: bool
    last_manual_backup_result: str
    pending_restore_detected: bool
    restore_validation_state: str
    restore_staged: bool
    restore_confirmation_state: str
    last_restore_result: str
    last_restore_rollback_result: str
    restore_replay_blocked: bool
    unresolved_restore_state: bool
    backup_archive_format_version: int | None
    same_schema_only: bool


class PairingHealth(StrictModel):
    status: Literal["NOT_PAIRED", "PAIRED", "EXPIRED", "INVALID", "REPAIR_REQUIRED", "UNKNOWN"]
    reason_code: str | None = None
    summary: str
    capability_available: bool
    paired: bool | None
    record_version: int | None
    record_parseable: bool
    localhost_proof_contract_available: bool
    replay_protection_enabled: bool
    repair_required: bool


class StartupEvent(StrictModel):
    event_code: str
    severity: Literal["INFO", "WARNING", "ERROR"]
    occurred_at: datetime
    component: str
    sanitized_summary: str
    resolved: bool
    attempt_id: str | None = None


class StartupHealth(StrictModel):
    status: DiagnosticStatus
    reason_code: str | None = None
    summary: str
    source_available: bool
    events: list[StartupEvent] = Field(default_factory=list, max_length=20)


class DiagnosticsCapabilities(StrictModel):
    read_only_snapshot: bool = True
    local_desktop_only: bool = True
    bundle_export: bool = False
    automatic_repair: bool = False
    telemetry: bool = False
    remote_upload: bool = False


class PlatformSummary(StrictModel):
    operating_system: str
    architecture: str
    python_major_minor: str


class DiagnosticsSnapshot(StrictModel):
    contract_version: int = Field(default=1, ge=1)
    generated_at: datetime
    application_mode: Literal["LOCAL_DESKTOP", "SERVER"]
    application_version: str
    platform_summary: PlatformSummary
    overall_status: OverallStatus
    runtime_health: RuntimeHealth
    api_health: ApiHealth
    database_health: DatabaseHealth
    schema_status: MigrationHealth
    migration_status: MigrationHealth
    restore_status: RestoreHealth
    pairing_status: PairingHealth
    recent_startup_status: StartupHealth
    warnings: list[str] = Field(default_factory=list, max_length=32)
    capabilities: DiagnosticsCapabilities
