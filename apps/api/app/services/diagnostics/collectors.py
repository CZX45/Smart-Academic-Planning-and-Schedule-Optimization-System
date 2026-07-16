from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

from sqlalchemy.engine import Engine, make_url

from app.config import LOCALHOST_NAMES, Settings, settings
from app.db.bootstrap import LOCAL_SCHEMA_VERSION
from app.db.local_migrations import LocalSchemaState, inspect_schema
from app.runtime.discovery import (
    RUNTIME_PROTOCOL_VERSION,
    is_runtime_manifest_stale,
    read_runtime_manifest,
)
from app.security.local_request import (
    EXTENSION_CREDENTIAL_HEADER,
    EXTENSION_NONCE_HEADER,
    EXTENSION_TIMESTAMP_HEADER,
    _is_loopback_host,
)
from app.security.pairing import PAIRING_PROTOCOL_VERSION
from app.services.diagnostics.models import (
    ApiHealth,
    DatabaseHealth,
    DiagnosticStatus,
    MigrationHealth,
    PairingHealth,
    RestoreHealth,
    RuntimeHealth,
    StartupEvent,
    StartupHealth,
)
from app.services.diagnostics.sanitization import sanitize_free_text, sanitize_structured_summary

APPLICATION_VERSION = "0.1.0"
INTEGRITY_CHECK_TIMEOUT_SECONDS = 0.75


def _now() -> datetime:
    return datetime.now(UTC)


def _component_status(
    *,
    healthy: bool,
    unknown: bool = False,
    action_required: bool = False,
    blocked: bool = False,
) -> DiagnosticStatus:
    if blocked:
        return DiagnosticStatus.BLOCKED
    if action_required:
        return DiagnosticStatus.ACTION_REQUIRED
    if unknown:
        return DiagnosticStatus.UNKNOWN
    return DiagnosticStatus.HEALTHY if healthy else DiagnosticStatus.DEGRADED


def _loopback_host(value: str) -> bool:
    return value in LOCALHOST_NAMES or _is_loopback_host(value)


def _manifest_path(settings_value: Settings) -> Path | None:
    return settings_value.runtime_manifest_path


def _data_root(settings_value: Settings, database_path: Path | None = None) -> Path:
    manifest_path = _manifest_path(settings_value)
    if manifest_path is not None:
        return manifest_path.parent.resolve()
    if database_path is not None:
        return database_path.parent.resolve()
    return Path.cwd().resolve()


def _safe_database_path(engine: Engine, settings_value: Settings) -> Path | None:
    if settings_value.product_mode != "LOCAL_DESKTOP" or engine.dialect.name != "sqlite":
        return None
    database = make_url(str(engine.url)).database
    if not database or database == ":memory:":
        return None
    path = Path(database).expanduser().resolve(strict=False)
    root = _data_root(settings_value, path)
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path


def _runtime_status(settings_value: Settings, manifest: Any) -> RuntimeHealth:
    if settings_value.product_mode != "LOCAL_DESKTOP":
        return RuntimeHealth(
            status=DiagnosticStatus.UNKNOWN,
            reason_code="server_mode",
            summary=sanitize_structured_summary("server_mode", "runtime", "unsupported"),
            current_mode="SERVER",
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
    if manifest is None:
        return RuntimeHealth(
            status=DiagnosticStatus.UNKNOWN,
            reason_code="runtime_manifest_unavailable",
            summary=sanitize_structured_summary(
                "runtime_manifest_unavailable", "runtime", "inspect"
            ),
            current_mode="LOCAL_DESKTOP",
            manifest_present=False,
            manifest_contract_supported=None,
            manifest_parseable=False,
            pid_valid=None,
            api_base_url_loopback=None,
            port_valid=None,
            stale=None,
            process_consistent=None,
            conflict_detected=False,
        )
    parsed_url = urlsplit(manifest.base_url)
    host = parsed_url.hostname or ""
    pid_valid = manifest.pid > 0
    port_valid = 1 <= manifest.port <= 65535
    process_consistent = manifest.pid == os.getpid()
    conflict_detected = False
    if not process_consistent:
        try:
            os.kill(manifest.pid, 0)
            conflict_detected = True
        except (OSError, PermissionError):
            conflict_detected = False
    stale = is_runtime_manifest_stale(manifest)
    safe = (
        pid_valid
        and port_valid
        and _loopback_host(host)
        and manifest.protocol_version == RUNTIME_PROTOCOL_VERSION
        and not stale
        and not conflict_detected
    )
    return RuntimeHealth(
        status=DiagnosticStatus.HEALTHY if safe else DiagnosticStatus.DEGRADED,
        reason_code=None if safe else "runtime_manifest_inconsistent",
        summary=sanitize_structured_summary(
            "runtime_ok" if safe else "runtime_manifest_inconsistent", "runtime", "inspect"
        ),
        current_mode="LOCAL_DESKTOP",
        manifest_present=True,
        manifest_contract_supported=manifest.protocol_version == RUNTIME_PROTOCOL_VERSION,
        manifest_parseable=True,
        pid_valid=pid_valid,
        api_base_url_loopback=_loopback_host(host),
        port_valid=port_valid,
        stale=stale,
        process_consistent=process_consistent,
        conflict_detected=conflict_detected,
    )


def collect_runtime(settings_value: Settings = settings) -> RuntimeHealth:
    if settings_value.product_mode != "LOCAL_DESKTOP":
        return _runtime_status(settings_value, None)
    path = _manifest_path(settings_value)
    if path is None:
        return _runtime_status(settings_value, None)
    try:
        manifest = read_runtime_manifest(path)
    except (OSError, ValueError):
        manifest = None
    if manifest is None and path.is_file():
        return RuntimeHealth(
            status=DiagnosticStatus.UNKNOWN,
            reason_code="runtime_manifest_invalid",
            summary=sanitize_structured_summary("runtime_manifest_invalid", "runtime", "inspect"),
            current_mode="LOCAL_DESKTOP",
            manifest_present=True,
            manifest_contract_supported=False,
            manifest_parseable=False,
            pid_valid=None,
            api_base_url_loopback=None,
            port_valid=None,
            stale=None,
            process_consistent=None,
            conflict_detected=False,
        )
    return _runtime_status(settings_value, manifest)


def collect_api(
    engine: Engine,
    *,
    settings_value: Settings = settings,
    database_health: DatabaseHealth | None = None,
    runtime_health: RuntimeHealth | None = None,
) -> ApiHealth:
    if settings_value.product_mode == "SERVER":
        return ApiHealth(
            status=DiagnosticStatus.UNKNOWN,
            reason_code="server_mode",
            summary=sanitize_structured_summary("server_mode", "api", "unsupported"),
            process_status="RUNNING",
            readiness_status="UNKNOWN",
            health_status="UNKNOWN",
            api_contract_version=APPLICATION_VERSION,
            application_mode="SERVER",
            loopback_bound=False,
            expected_database="POSTGRESQL",
            schema_match=None,
            recent_child_process_exit=None,
        )
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        ready = True
    except Exception:
        ready = False
    loopback = _loopback_host(settings_value.api_host)
    schema_match = None
    if database_health is not None and database_health.schema_version is not None:
        schema_match = database_health.schema_version == database_health.supported_schema_version
    healthy = ready and loopback and (schema_match is not False)
    return ApiHealth(
        status=DiagnosticStatus.HEALTHY if healthy else DiagnosticStatus.DEGRADED,
        reason_code=None if healthy else "api_readiness_or_binding_failed",
        summary=sanitize_structured_summary(
            "api_ready" if healthy else "api_readiness_or_binding_failed", "api", "inspect"
        ),
        process_status="RUNNING",
        readiness_status="READY" if ready else "NOT_READY",
        health_status="HEALTHY" if ready else "UNHEALTHY",
        api_contract_version=APPLICATION_VERSION,
        application_mode="LOCAL_DESKTOP",
        loopback_bound=loopback,
        expected_database="SQLITE",
        schema_match=schema_match,
        recent_child_process_exit=None,
    )


def _size_bucket(size: int) -> str:
    if size < 1_000_000:
        return "<1 MB"
    if size < 10_000_000:
        return "1-10 MB"
    if size < 100_000_000:
        return "10-100 MB"
    return ">100 MB"


def _read_only_connection(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{quote(str(path), safe='/:\\')}?mode=ro", uri=True, timeout=0.5)


def _check_integrity(connection: sqlite3.Connection, pragma: str) -> DiagnosticStatus:
    deadline = time.monotonic() + INTEGRITY_CHECK_TIMEOUT_SECONDS
    connection.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
    try:
        rows = connection.execute(f"PRAGMA {pragma}").fetchall()
        return DiagnosticStatus.HEALTHY if rows == [("ok",)] else DiagnosticStatus.DEGRADED
    except sqlite3.OperationalError as error:
        return (
            DiagnosticStatus.TIMED_OUT
            if "interrupt" in str(error).lower()
            else DiagnosticStatus.DEGRADED
        )
    except sqlite3.Error:
        return DiagnosticStatus.ERROR
    finally:
        connection.set_progress_handler(None, 0)


def _check_foreign_keys(connection: sqlite3.Connection) -> DiagnosticStatus:
    deadline = time.monotonic() + INTEGRITY_CHECK_TIMEOUT_SECONDS
    connection.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
    try:
        rows = connection.execute("PRAGMA foreign_key_check").fetchmany(101)
        return DiagnosticStatus.HEALTHY if not rows else DiagnosticStatus.DEGRADED
    except sqlite3.OperationalError as error:
        return (
            DiagnosticStatus.TIMED_OUT
            if "interrupt" in str(error).lower()
            else DiagnosticStatus.DEGRADED
        )
    except sqlite3.Error:
        return DiagnosticStatus.ERROR
    finally:
        connection.set_progress_handler(None, 0)


def collect_database(
    engine: Engine,
    *,
    settings_value: Settings = settings,
) -> DatabaseHealth:
    path = _safe_database_path(engine, settings_value)
    base = dict(supported_schema_version=LOCAL_SCHEMA_VERSION)
    if settings_value.product_mode != "LOCAL_DESKTOP":
        return DatabaseHealth(
            status=DiagnosticStatus.UNKNOWN,
            reason_code="server_mode",
            summary=sanitize_structured_summary("server_mode", "database", "unsupported"),
            present=False,
            readable=False,
            sqlite_header_valid=None,
            foreign_keys_status=DiagnosticStatus.NOT_RUN,
            integrity_check_status=DiagnosticStatus.NOT_RUN,
            foreign_key_check_status=DiagnosticStatus.NOT_RUN,
            schema_version=None,
            schema_version_supported=None,
            supported_schema_version=LOCAL_SCHEMA_VERSION,
            journal_mode=None,
            sidecar_wal_present=False,
            sidecar_shm_present=False,
            sidecar_journal_present=False,
            operation_state="UNKNOWN",
            size_bucket="UNKNOWN",
        )
    if path is None or not path.is_file():
        return DatabaseHealth(
            status=DiagnosticStatus.BLOCKED,
            reason_code="database_missing",
            summary=sanitize_structured_summary("database_missing", "database", "inspect"),
            present=False,
            readable=False,
            sqlite_header_valid=None,
            foreign_keys_status=DiagnosticStatus.NOT_RUN,
            integrity_check_status=DiagnosticStatus.NOT_RUN,
            foreign_key_check_status=DiagnosticStatus.NOT_RUN,
            schema_version=None,
            schema_version_supported=None,
            supported_schema_version=LOCAL_SCHEMA_VERSION,
            journal_mode=None,
            sidecar_wal_present=False,
            sidecar_shm_present=False,
            sidecar_journal_present=False,
            operation_state="UNKNOWN",
            size_bucket="UNKNOWN",
        )
    sidecars = {
        "sidecar_wal_present": path.with_name(path.name + "-wal").exists(),
        "sidecar_shm_present": path.with_name(path.name + "-shm").exists(),
        "sidecar_journal_present": path.with_name(path.name + "-journal").exists(),
    }
    try:
        size_bucket = _size_bucket(path.stat().st_size)
        with _read_only_connection(path) as connection:
            header = connection.execute("PRAGMA application_id").fetchone() is not None
            connection.execute("PRAGMA foreign_keys=ON")
            foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone() == (1,)
            integrity = _check_integrity(connection, "integrity_check")
            foreign_check = _check_foreign_keys(connection)
            schema_row = connection.execute(
                "SELECT schema_version FROM local_schema_versions "
                "WHERE schema_name = 'LOCAL_DESKTOP'"
            ).fetchone()
            schema_version = int(schema_row[0]) if schema_row else None
            journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0]).upper()
        healthy = header and foreign_keys and integrity == DiagnosticStatus.HEALTHY
        healthy = (
            healthy and foreign_check == DiagnosticStatus.HEALTHY and schema_version is not None
        )
        schema_supported = (
            schema_version is not None and 1 <= schema_version <= LOCAL_SCHEMA_VERSION
        )
        if not schema_supported:
            healthy = False
        status = DiagnosticStatus.HEALTHY if healthy else DiagnosticStatus.DEGRADED
        return DatabaseHealth(
            status=status,
            reason_code=None if healthy else "database_validation_failed",
            summary=sanitize_structured_summary(
                "database_ok" if healthy else "database_validation_failed", "database", "inspect"
            ),
            present=True,
            readable=True,
            sqlite_header_valid=header,
            foreign_keys_status=DiagnosticStatus.HEALTHY
            if foreign_keys
            else DiagnosticStatus.DEGRADED,
            integrity_check_status=integrity,
            foreign_key_check_status=foreign_check,
            schema_version=schema_version,
            schema_version_supported=schema_supported,
            journal_mode=journal_mode,
            operation_state="SIDECAR_PRESENT" if any(sidecars.values()) else "NONE_DETECTED",
            size_bucket=size_bucket,
            **base,
            **sidecars,
        )
    except (OSError, sqlite3.Error, ValueError, TypeError):
        return DatabaseHealth(
            status=DiagnosticStatus.DEGRADED,
            reason_code="database_unreadable",
            summary=sanitize_structured_summary("database_unreadable", "database", "inspect"),
            present=True,
            readable=False,
            sqlite_header_valid=None,
            foreign_keys_status=DiagnosticStatus.UNKNOWN,
            integrity_check_status=DiagnosticStatus.UNKNOWN,
            foreign_key_check_status=DiagnosticStatus.UNKNOWN,
            schema_version=None,
            schema_version_supported=None,
            operation_state="SIDECAR_PRESENT" if any(sidecars.values()) else "UNKNOWN",
            size_bucket=_size_bucket(path.stat().st_size) if path.exists() else "UNKNOWN",
            **base,
            **sidecars,
        )


def _journal_row(connection: sqlite3.Connection) -> Mapping[str, Any] | None:
    try:
        row = connection.execute(
            "SELECT attempt_id, status, started_at, completed_at, "
            "safety_backup_reference, failure_stage, sanitized_error "
            "FROM local_migration_journal ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
    except sqlite3.Error:
        return None
    if row is None:
        return None
    return {
        "attempt_id": row[0],
        "status": row[1],
        "started_at": row[2],
        "completed_at": row[3],
        "safety_backup_reference": row[4],
        "failure_stage": row[5],
        "sanitized_error": row[6],
    }


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def collect_migration(
    engine: Engine,
    *,
    settings_value: Settings = settings,
) -> MigrationHealth:
    database = _safe_database_path(engine, settings_value)
    base = dict(
        supported_schema_version=LOCAL_SCHEMA_VERSION,
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
    if settings_value.product_mode != "LOCAL_DESKTOP":
        return MigrationHealth(
            status=DiagnosticStatus.UNKNOWN,
            reason_code="server_mode",
            summary=sanitize_structured_summary("server_mode", "migration", "unsupported"),
            current_schema_version=None,
            schema_status="UNKNOWN",
            **base,
        )
    if database is None or not database.is_file():
        return MigrationHealth(
            status=DiagnosticStatus.BLOCKED,
            reason_code="database_missing",
            summary=sanitize_structured_summary("database_missing", "migration", "inspect"),
            current_schema_version=None,
            schema_status=LocalSchemaState.UNKNOWN_OR_CORRUPT.value,
            recovery_action_category="RECOVERY_PREFLIGHT",
            **{**base, "blocking_reason_code": "database_missing"},
        )
    try:
        with sqlite3.connect(
            f"file:{quote(str(database), safe='/:\\')}?mode=ro", uri=True
        ) as connection:
            info = inspect_schema(connection, (), LOCAL_SCHEMA_VERSION)
            journal = _journal_row(connection)
    except sqlite3.Error:
        return MigrationHealth(
            status=DiagnosticStatus.UNKNOWN,
            reason_code="migration_state_unavailable",
            summary=sanitize_structured_summary(
                "migration_state_unavailable", "migration", "inspect"
            ),
            current_schema_version=None,
            schema_status="UNKNOWN",
            **base,
        )
    status = DiagnosticStatus.HEALTHY
    reason = None
    action = "NONE"
    if info.state in {
        LocalSchemaState.UNKNOWN_OR_CORRUPT,
        LocalSchemaState.NEWER_VERSION_UNSUPPORTED,
    }:
        status, reason, action = DiagnosticStatus.BLOCKED, info.state.value, "REVIEW"
    elif info.state == LocalSchemaState.UPGRADE_REQUIRED:
        status, reason, action = DiagnosticStatus.ACTION_REQUIRED, info.state.value, "REVIEW"
    elif info.state in {LocalSchemaState.MIGRATION_IN_PROGRESS, LocalSchemaState.FAILED_MIGRATION}:
        status, reason, action = DiagnosticStatus.BLOCKED, info.state.value, "RECOVERY_PREFLIGHT"
    row_status = str(journal["status"]) if journal else None
    interrupted = row_status in {"IN_PROGRESS", "INTERRUPTED"}
    return MigrationHealth(
        status=status,
        reason_code=reason,
        summary=sanitize_structured_summary(
            "migration_ok"
            if status == DiagnosticStatus.HEALTHY
            else (reason or "migration_status"),
            "migration",
            "inspect",
        ),
        current_schema_version=info.current_version,
        supported_schema_version=LOCAL_SCHEMA_VERSION,
        schema_status=info.state.value,
        migration_required=info.state == LocalSchemaState.UPGRADE_REQUIRED,
        migration_in_progress=info.state == LocalSchemaState.MIGRATION_IN_PROGRESS,
        last_attempt_status=row_status,
        last_successful_migration=(
            _parse_datetime(journal["completed_at"])
            if journal and row_status == "COMPLETED"
            else None
        ),
        last_rollback_status="UNKNOWN",
        interrupted_attempt_detected=interrupted,
        safety_backup_reference_exists=(
            bool(journal and journal["safety_backup_reference"]) if journal else False
        ),
        blocking_reason_code=reason,
        recovery_action_category=action,
    )


def collect_restore(
    engine: Engine,
    *,
    settings_value: Settings = settings,
    database_health: DatabaseHealth | None = None,
) -> RestoreHealth:
    database = _safe_database_path(engine, settings_value)
    if settings_value.product_mode != "LOCAL_DESKTOP":
        return RestoreHealth(
            status=DiagnosticStatus.UNKNOWN,
            reason_code="server_mode",
            summary=sanitize_structured_summary("server_mode", "restore", "unsupported"),
            backup_capability_available=False,
            last_manual_backup_result="UNKNOWN",
            pending_restore_detected=False,
            restore_validation_state="NOT_RUN",
            restore_staged=False,
            restore_confirmation_state="NOT_RUN",
            last_restore_result="UNKNOWN",
            last_restore_rollback_result="UNKNOWN",
            restore_replay_blocked=False,
            unresolved_restore_state=False,
            backup_archive_format_version=None,
            same_schema_only=True,
        )
    root = _data_root(settings_value, database)
    pending = root / "pending-restore.json"
    restore_status = root / "restore-status.json"
    pending_exists = pending.is_file()
    status_value = "none"
    status_parseable = True
    if restore_status.is_file():
        try:
            payload = json.loads(restore_status.read_text(encoding="utf-8"))
            status_value = (
                str(payload.get("status", "unknown")) if isinstance(payload, dict) else "unknown"
            )
        except (OSError, ValueError):
            status_parseable = False
            status_value = "unknown"
    pending_status = "pending"
    pending_valid = True
    if pending_exists:
        try:
            payload = json.loads(pending.read_text(encoding="utf-8"))
            pending_status = (
                str(payload.get("status", "pending")) if isinstance(payload, dict) else "unknown"
            )
        except (OSError, ValueError):
            pending_valid = False
            pending_status = "unknown"
    available = database_health is not None and database_health.present and database_health.readable
    unresolved = pending_exists or not status_parseable or (pending_exists and not pending_valid)
    blocked = pending_exists and (
        not pending_valid or pending_status in {"replay_blocked", "invalid"}
    )
    status = (
        DiagnosticStatus.BLOCKED
        if blocked
        else DiagnosticStatus.ACTION_REQUIRED
        if pending_exists
        else DiagnosticStatus.HEALTHY
    )
    return RestoreHealth(
        status=status,
        reason_code="restore_state_requires_review" if unresolved else None,
        summary=sanitize_structured_summary(
            "restore_pending" if pending_exists else "restore_ok", "restore", "inspect"
        ),
        backup_capability_available=bool(available),
        last_manual_backup_result="UNKNOWN",
        pending_restore_detected=pending_exists,
        restore_validation_state="VALIDATED" if pending_exists and pending_valid else "UNKNOWN",
        restore_staged=pending_exists,
        restore_confirmation_state="CONFIRMED_PENDING" if pending_exists else "NOT_PENDING",
        last_restore_result=status_value.upper(),
        last_restore_rollback_result="UNKNOWN",
        restore_replay_blocked=blocked,
        unresolved_restore_state=unresolved,
        backup_archive_format_version=1,
        same_schema_only=True,
    )


def collect_pairing(settings_value: Settings = settings) -> PairingHealth:
    if settings_value.product_mode != "LOCAL_DESKTOP":
        return PairingHealth(
            status="UNKNOWN",
            reason_code="server_mode",
            summary=sanitize_structured_summary("server_mode", "pairing", "unsupported"),
            capability_available=False,
            paired=None,
            record_version=None,
            record_parseable=False,
            localhost_proof_contract_available=False,
            replay_protection_enabled=False,
            repair_required=False,
        )
    path = settings_value.local_pairing_store_path
    if not path.is_file():
        return PairingHealth(
            status="NOT_PAIRED",
            reason_code=None,
            summary=sanitize_structured_summary("not_paired", "pairing", "inspect"),
            capability_available=True,
            paired=False,
            record_version=PAIRING_PROTOCOL_VERSION,
            record_parseable=True,
            localhost_proof_contract_available=all(
                value
                for value in (
                    EXTENSION_CREDENTIAL_HEADER,
                    EXTENSION_NONCE_HEADER,
                    EXTENSION_TIMESTAMP_HEADER,
                )
            ),
            replay_protection_enabled=True,
            repair_required=False,
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError
        version = payload.get("protocol_version", PAIRING_PROTOCOL_VERSION)
        if not isinstance(version, int):
            raise ValueError
        if version != PAIRING_PROTOCOL_VERSION:
            raise ValueError
        credential = payload.get("credential")
        paired = isinstance(credential, dict) and credential.get("revoked_at") is None
        if paired and isinstance(credential, dict):
            extension_id = credential.get("extension_id")
            verifier = credential.get("verifier")
            if (
                not isinstance(extension_id, str)
                or len(extension_id) != 32
                or any(character not in "abcdefghijklmnop" for character in extension_id)
                or not isinstance(verifier, str)
                or len(verifier) != 64
                or any(character not in "0123456789abcdef" for character in verifier)
            ):
                return PairingHealth(
                    status="REPAIR_REQUIRED",
                    reason_code="pairing_record_invalid",
                    summary=sanitize_structured_summary(
                        "pairing_record_invalid", "pairing", "inspect"
                    ),
                    capability_available=True,
                    paired=None,
                    record_version=version,
                    record_parseable=True,
                    localhost_proof_contract_available=True,
                    replay_protection_enabled=True,
                    repair_required=True,
                )
        status = "PAIRED" if paired else "NOT_PAIRED"
        return PairingHealth(
            status=status,
            reason_code=None,
            summary=sanitize_structured_summary(status.lower(), "pairing", "inspect"),
            capability_available=True,
            paired=paired,
            record_version=version,
            record_parseable=True,
            localhost_proof_contract_available=True,
            replay_protection_enabled=True,
            repair_required=False,
        )
    except (OSError, ValueError, TypeError):
        return PairingHealth(
            status="INVALID",
            reason_code="pairing_record_invalid",
            summary=sanitize_structured_summary("pairing_record_invalid", "pairing", "inspect"),
            capability_available=True,
            paired=None,
            record_version=None,
            record_parseable=False,
            localhost_proof_contract_available=True,
            replay_protection_enabled=True,
            repair_required=True,
        )


def collect_startup(settings_value: Settings = settings) -> StartupHealth:
    if settings_value.product_mode != "LOCAL_DESKTOP":
        return StartupHealth(
            status=DiagnosticStatus.UNKNOWN,
            reason_code="server_mode",
            summary=sanitize_structured_summary("server_mode", "startup", "unsupported"),
            source_available=False,
        )
    if settings_value.runtime_manifest_path is None:
        return StartupHealth(
            status=DiagnosticStatus.NOT_RUN,
            reason_code="startup_event_source_unavailable",
            summary=sanitize_structured_summary(
                "startup_event_source_unavailable", "startup", "inspect"
            ),
            source_available=False,
        )
    root = _data_root(settings_value)
    path = root / "startup-events.json"
    if not path.is_file():
        return StartupHealth(
            status=DiagnosticStatus.NOT_RUN,
            reason_code="startup_event_source_unavailable",
            summary=sanitize_structured_summary(
                "startup_event_source_unavailable", "startup", "inspect"
            ),
            source_available=False,
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw_events = payload.get("events", []) if isinstance(payload, dict) else []
        if not isinstance(raw_events, list):
            raise ValueError
        events: list[StartupEvent] = []
        for raw in raw_events[-20:]:
            if not isinstance(raw, dict):
                continue
            occurred_at = _parse_datetime(raw.get("occurred_at"))
            if occurred_at is None:
                continue
            severity = str(raw.get("severity", "WARNING")).upper()
            if severity not in {"INFO", "WARNING", "ERROR"}:
                severity = "WARNING"
            events.append(
                StartupEvent(
                    event_code=str(raw.get("event_code", "unknown_event"))[:80],
                    severity=severity,
                    occurred_at=occurred_at,
                    component=str(raw.get("component", "startup"))[:40],
                    sanitized_summary=sanitize_free_text(raw.get("sanitized_summary")),
                    resolved=bool(raw.get("resolved", False)),
                    attempt_id=(
                        hashlib.sha256(str(raw.get("attempt_id")).encode("utf-8")).hexdigest()[:16]
                        if raw.get("attempt_id")
                        else None
                    ),
                )
            )
        status = (
            DiagnosticStatus.DEGRADED
            if any(event.severity == "ERROR" for event in events)
            else DiagnosticStatus.HEALTHY
        )
        return StartupHealth(
            status=status,
            reason_code=None,
            summary=sanitize_structured_summary("startup_events_read", "startup", "inspect"),
            source_available=True,
            events=events,
        )
    except (OSError, ValueError, TypeError):
        return StartupHealth(
            status=DiagnosticStatus.UNKNOWN,
            reason_code="startup_event_source_invalid",
            summary=sanitize_structured_summary(
                "startup_event_source_invalid", "startup", "inspect"
            ),
            source_available=True,
        )
