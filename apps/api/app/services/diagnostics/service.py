from __future__ import annotations

import platform
import sys
from datetime import UTC, datetime

from sqlalchemy.engine import Engine

from app.config import Settings, settings
from app.services.diagnostics.collectors import (
    APPLICATION_VERSION,
    collect_api,
    collect_database,
    collect_migration,
    collect_pairing,
    collect_restore,
    collect_runtime,
    collect_startup,
)
from app.services.diagnostics.models import (
    ApiHealth,
    DatabaseHealth,
    DiagnosticsCapabilities,
    DiagnosticsSnapshot,
    DiagnosticStatus,
    MigrationHealth,
    OverallStatus,
    PairingHealth,
    PlatformSummary,
    RestoreHealth,
    RuntimeHealth,
    StartupHealth,
)


def _overall_status(values: list[str]) -> OverallStatus:
    if "BLOCKED" in values:
        return OverallStatus.BLOCKED
    if "ACTION_REQUIRED" in values:
        return OverallStatus.ACTION_REQUIRED
    if "DEGRADED" in values:
        return OverallStatus.DEGRADED
    if any(value in {"UNKNOWN", "NOT_RUN", "TIMED_OUT", "ERROR"} for value in values):
        return OverallStatus.UNKNOWN
    return OverallStatus.HEALTHY


def _collector_failure(component: str) -> str:
    return f"{component}:collector_failed:unknown"


def _runtime_failure(settings_value: Settings) -> RuntimeHealth:
    return RuntimeHealth(
        status=DiagnosticStatus.ERROR,
        reason_code="collector_failed",
        summary=_collector_failure("runtime"),
        current_mode=settings_value.product_mode,
        manifest_present=False,
        manifest_contract_supported=None,
        manifest_parseable=None,
        pid_valid=None,
        api_base_url_loopback=None,
        port_valid=None,
        stale=None,
        process_consistent=None,
        conflict_detected=False,
    )


def _database_failure() -> DatabaseHealth:
    return DatabaseHealth(
        status=DiagnosticStatus.ERROR,
        reason_code="collector_failed",
        summary=_collector_failure("database"),
        present=False,
        readable=False,
        sqlite_header_valid=None,
        foreign_keys_status=DiagnosticStatus.UNKNOWN,
        integrity_check_status=DiagnosticStatus.UNKNOWN,
        foreign_key_check_status=DiagnosticStatus.UNKNOWN,
        schema_version=None,
        supported_schema_version=0,
        schema_version_supported=None,
        journal_mode=None,
        sidecar_wal_present=False,
        sidecar_shm_present=False,
        sidecar_journal_present=False,
        operation_state="UNKNOWN",
        size_bucket="UNKNOWN",
    )


def _migration_failure() -> MigrationHealth:
    return MigrationHealth(
        status=DiagnosticStatus.ERROR,
        reason_code="collector_failed",
        summary=_collector_failure("migration"),
        current_schema_version=None,
        supported_schema_version=0,
        schema_status="UNKNOWN",
        migration_required=None,
        migration_in_progress=False,
        last_attempt_status=None,
        last_successful_migration=None,
        last_rollback_status="UNKNOWN",
        interrupted_attempt_detected=False,
        safety_backup_reference_exists=None,
        blocking_reason_code=None,
        recovery_action_category="UNKNOWN",
    )


def _restore_failure() -> RestoreHealth:
    return RestoreHealth(
        status=DiagnosticStatus.ERROR,
        reason_code="collector_failed",
        summary=_collector_failure("restore"),
        backup_capability_available=False,
        last_manual_backup_result="UNKNOWN",
        pending_restore_detected=False,
        restore_validation_state="UNKNOWN",
        restore_staged=False,
        restore_confirmation_state="UNKNOWN",
        last_restore_result="UNKNOWN",
        last_restore_rollback_result="UNKNOWN",
        restore_replay_blocked=False,
        unresolved_restore_state=True,
        backup_archive_format_version=None,
        same_schema_only=True,
    )


def _pairing_failure() -> PairingHealth:
    return PairingHealth(
        status="UNKNOWN",
        reason_code="collector_failed",
        summary=_collector_failure("pairing"),
        capability_available=False,
        paired=None,
        record_version=None,
        record_parseable=False,
        localhost_proof_contract_available=False,
        replay_protection_enabled=False,
        repair_required=False,
    )


def _startup_failure() -> StartupHealth:
    return StartupHealth(
        status=DiagnosticStatus.ERROR,
        reason_code="collector_failed",
        summary=_collector_failure("startup"),
        source_available=False,
    )


def collect_snapshot(
    engine: Engine,
    *,
    settings_value: Settings = settings,
    generated_at: datetime | None = None,
) -> DiagnosticsSnapshot:
    try:
        runtime = collect_runtime(settings_value)
    except Exception:
        runtime = _runtime_failure(settings_value)
    try:
        database = collect_database(engine, settings_value=settings_value)
    except Exception:
        database = _database_failure()
    try:
        migration = collect_migration(engine, settings_value=settings_value)
    except Exception:
        migration = _migration_failure()
    try:
        restore = collect_restore(engine, settings_value=settings_value, database_health=database)
    except Exception:
        restore = _restore_failure()
    try:
        api = collect_api(
            engine,
            settings_value=settings_value,
            database_health=database,
            runtime_health=runtime,
        )
    except Exception:
        api = ApiHealth(
            status=DiagnosticStatus.ERROR,
            reason_code="collector_failed",
            summary=_collector_failure("api"),
            process_status="UNKNOWN",
            readiness_status="UNKNOWN",
            health_status="UNKNOWN",
            api_contract_version=APPLICATION_VERSION,
            application_mode=settings_value.product_mode,
            loopback_bound=False,
            expected_database="UNKNOWN",
            schema_match=None,
            recent_child_process_exit=None,
        )
    try:
        pairing = collect_pairing(settings_value)
    except Exception:
        pairing = _pairing_failure()
    try:
        startup = collect_startup(settings_value)
    except Exception:
        startup = _startup_failure()
    statuses = [
        runtime.status.value,
        api.status.value,
        database.status.value,
        migration.status.value,
        restore.status.value,
        startup.status.value,
    ]
    warnings: list[str] = [
        "Diagnostics is a read-only LOCAL_DESKTOP snapshot.",
        "Diagnostics never includes student records, credentials, or database content.",
    ]
    if runtime.status.value != "HEALTHY":
        warnings.append("Runtime status requires review.")
    if database.integrity_check_status.value in {"TIMED_OUT", "ERROR"}:
        warnings.append("Database integrity check did not complete.")
    if migration.status.value not in {"HEALTHY", "UNKNOWN"}:
        warnings.append("Migration status requires review before recovery.")
    if restore.pending_restore_detected:
        warnings.append("A pending restore requires the normal startup recovery flow.")
    if pairing.repair_required:
        warnings.append("Extension pairing requires repair.")
    return DiagnosticsSnapshot(
        contract_version=1,
        generated_at=generated_at or datetime.now(UTC),
        application_mode=settings_value.product_mode,
        application_version=APPLICATION_VERSION,
        platform_summary=PlatformSummary(
            operating_system=platform.system() or "UNKNOWN",
            architecture=platform.machine() or "UNKNOWN",
            python_major_minor=f"{sys.version_info.major}.{sys.version_info.minor}",
        ),
        overall_status=_overall_status(statuses),
        runtime_health=runtime,
        api_health=api,
        database_health=database,
        schema_status=migration,
        migration_status=migration,
        restore_status=restore,
        pairing_status=pairing,
        recent_startup_status=startup,
        warnings=warnings,
        capabilities=DiagnosticsCapabilities(bundle_export=True),
    )
