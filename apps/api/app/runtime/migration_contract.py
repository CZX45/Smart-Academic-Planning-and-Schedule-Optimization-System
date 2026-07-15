from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine

from app.config import settings
from app.db.bootstrap import LOCAL_SCHEMA_VERSION
from app.db.local_migrations import (
    LocalMigration,
    LocalSchemaInfo,
    LocalSchemaState,
    MigrationError,
    SafetyBackupReference,
    inspect_schema,
    run_migrations,
)
from app.services.local_backup import create_migration_safety_backup

CONTRACT_VERSION = 1


@dataclass(frozen=True)
class MigrationContractResult:
    contract_version: int
    command: str
    database_identity: str | None
    current_schema_version: int | None
    supported_schema_version: int
    schema_status: str
    migration_required: bool
    migration_plan: list[str]
    safety_backup_required: bool
    blocking_reason: str | None
    interrupted_attempt: dict[str, str] | None = None
    journal_attempt_id: str | None = None
    attempt_id: str | None = None
    safety_backup_reference: str | None = None
    integrity_check: str | None = None
    foreign_key_violations: int | None = None


def _database_path() -> Path:
    if settings.product_mode != "LOCAL_DESKTOP":
        raise MigrationError(
            "local_desktop_only", "Local migration is available only in LOCAL_DESKTOP."
        )
    if not settings.database_url.startswith("sqlite+pysqlite:///"):
        raise MigrationError(
            "sqlite_required", "Local migration requires the LOCAL_DESKTOP SQLite database."
        )
    path = Path(settings.database_url.removeprefix("sqlite+pysqlite:///"))
    path = path.expanduser().resolve()
    root = (
        settings.runtime_manifest_path.parent if settings.runtime_manifest_path else path.parent
    ).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise MigrationError(
            "database_path_invalid", "The local database is outside the app-data directory."
        ) from error
    if not path.is_file():
        raise MigrationError("database_missing", "The local application database is not available.")
    return path


def _identity(path: Path) -> str:
    return hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()


def _journal_attempt(connection: sqlite3.Connection) -> dict[str, str] | None:
    try:
        row = connection.execute(
            "SELECT attempt_id, status, safety_backup_reference "
            "FROM local_migration_journal ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
    except sqlite3.Error:
        return None
    if row is None:
        return None
    result = {"attempt_id": str(row[0]), "status": str(row[1])}
    if row[2] is not None:
        result["safety_backup_reference"] = str(row[2])
    return result


def _inspect(
    path: Path, migrations: Iterable[LocalMigration], target_version: int
) -> tuple[LocalSchemaInfo, dict[str, str] | None]:
    with sqlite3.connect(path) as connection:
        return inspect_schema(connection, migrations, target_version), _journal_attempt(connection)


def preflight(
    *, migrations: Iterable[LocalMigration] = (), target_version: int = LOCAL_SCHEMA_VERSION
) -> MigrationContractResult:
    path = _database_path()
    info, journal = _inspect(path, migrations, target_version)
    plan = list(info.plan.migration_ids) if info.plan else []
    return MigrationContractResult(
        contract_version=CONTRACT_VERSION,
        command="preflight",
        database_identity=_identity(path),
        current_schema_version=info.current_version,
        supported_schema_version=info.target_version,
        schema_status=info.state.value,
        migration_required=info.state == LocalSchemaState.UPGRADE_REQUIRED,
        migration_plan=plan,
        safety_backup_required=info.state == LocalSchemaState.UPGRADE_REQUIRED,
        blocking_reason=info.message or None,
        interrupted_attempt=journal
        if journal and journal["status"] in {"IN_PROGRESS", "INTERRUPTED"}
        else None,
        journal_attempt_id=journal["attempt_id"] if journal else None,
    )


def execute(
    *, migrations: Iterable[LocalMigration] = (), target_version: int = LOCAL_SCHEMA_VERSION
) -> MigrationContractResult:
    path = _database_path()
    info, journal = _inspect(path, migrations, target_version)
    if info.state == LocalSchemaState.CURRENT:
        result = preflight(migrations=migrations, target_version=target_version)
        return result.__class__(**{**asdict(result), "command": "execute"})
    if (
        info.state != LocalSchemaState.UPGRADE_REQUIRED
        or info.plan is None
        or info.current_version is None
    ):
        result = preflight(migrations=migrations, target_version=target_version)
        return result.__class__(**{**asdict(result), "command": "execute"})
    attempt_id = uuid4()
    root = (
        settings.runtime_manifest_path.parent if settings.runtime_manifest_path else path.parent
    ).resolve()
    snapshot = create_migration_safety_backup(path, attempt_id, root)
    reference = SafetyBackupReference(
        str(snapshot.relative_to(root)).replace("\\", "/"), _identity(path)
    )
    engine = create_engine(settings.database_url)
    try:
        try:
            run = run_migrations(
                engine,
                migrations,
                target_version=target_version,
                safety_backup=reference,
                attempt_id=attempt_id,
            )
        except MigrationError as error:
            return MigrationContractResult(
                contract_version=CONTRACT_VERSION,
                command="execute",
                database_identity=_identity(path),
                current_schema_version=info.current_version,
                supported_schema_version=target_version,
                schema_status="FAILED_MIGRATION",
                migration_required=True,
                migration_plan=list(info.plan.migration_ids),
                safety_backup_required=True,
                blocking_reason=error.code,
                interrupted_attempt=journal,
                journal_attempt_id=str(attempt_id),
                attempt_id=str(attempt_id),
                safety_backup_reference=reference.reference,
            )
    finally:
        engine.dispose()
    return MigrationContractResult(
        contract_version=CONTRACT_VERSION,
        command="execute",
        database_identity=_identity(path),
        current_schema_version=run.target_version,
        supported_schema_version=target_version,
        schema_status=run.state.value,
        migration_required=False,
        migration_plan=list(run.migration_ids),
        safety_backup_required=True,
        blocking_reason=None,
        interrupted_attempt=journal,
        journal_attempt_id=str(run.attempt_id),
        attempt_id=str(attempt_id),
        safety_backup_reference=reference.reference,
        integrity_check=run.integrity_check,
        foreign_key_violations=run.foreign_key_violations,
    )


def _emit(result: MigrationContractResult) -> int:
    sys.stdout.write(json.dumps(asdict(result), separators=(",", ":"), sort_keys=True) + "\n")
    return 0


def main(command: str) -> int:
    try:
        if command == "preflight":
            return _emit(preflight())
        if command == "execute":
            result = execute()
            _emit(result)
            return 0 if result.schema_status == LocalSchemaState.CURRENT else 2
        raise MigrationError("command_invalid", "Unsupported local migration command.")
    except MigrationError as error:
        _emit(
            MigrationContractResult(
                CONTRACT_VERSION,
                command,
                None,
                None,
                LOCAL_SCHEMA_VERSION,
                "BLOCKED",
                False,
                [],
                False,
                error.code,
            )
        )
        return 2
    except (OSError, sqlite3.Error, ValueError) as error:
        _emit(
            MigrationContractResult(
                CONTRACT_VERSION,
                command,
                None,
                None,
                LOCAL_SCHEMA_VERSION,
                "UNKNOWN_OR_CORRUPT",
                False,
                [],
                False,
                type(error).__name__,
            )
        )
        return 2
