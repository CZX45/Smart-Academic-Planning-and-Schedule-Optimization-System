from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy.engine import Engine, make_url

from app.db.bootstrap import LOCAL_SCHEMA_VERSION


class LocalSchemaState(StrEnum):
    CURRENT = "CURRENT"
    UPGRADE_REQUIRED = "UPGRADE_REQUIRED"
    MIGRATION_IN_PROGRESS = "MIGRATION_IN_PROGRESS"
    FAILED_MIGRATION = "FAILED_MIGRATION"
    NEWER_VERSION_UNSUPPORTED = "NEWER_VERSION_UNSUPPORTED"
    UNKNOWN_OR_CORRUPT = "UNKNOWN_OR_CORRUPT"


class MigrationError(RuntimeError):
    """A fail-closed local migration error with a stable reason code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class SafetyBackupProvider(Protocol):
    def create_safety_backup(self, database: Path) -> SafetyBackupReference: ...


@dataclass(frozen=True)
class SafetyBackupReference:
    reference: str
    database_identity: str
    validated: bool = True


MigrationApply = Callable[[sqlite3.Connection], None]


@dataclass(frozen=True)
class LocalMigration:
    migration_id: str
    from_version: int
    to_version: int
    apply: MigrationApply
    requires_safety_backup: bool = False


@dataclass(frozen=True)
class LocalMigrationPlan:
    from_version: int
    target_version: int
    migrations: tuple[LocalMigration, ...]

    @property
    def migration_ids(self) -> tuple[str, ...]:
        return tuple(migration.migration_id for migration in self.migrations)


@dataclass(frozen=True)
class LocalSchemaInfo:
    state: LocalSchemaState
    current_version: int | None
    target_version: int
    plan: LocalMigrationPlan | None = None
    message: str = ""


@dataclass(frozen=True)
class MigrationRunResult:
    attempt_id: UUID
    state: LocalSchemaState
    from_version: int
    target_version: int
    migration_ids: tuple[str, ...]
    integrity_check: str
    foreign_key_violations: int


def _database_identity(database: Path) -> str:
    return hashlib.sha256(str(database.resolve()).encode("utf-8")).hexdigest()


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
        ).fetchone()
        is not None
    )


def ensure_migration_journal(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS local_migration_journal (
            attempt_id TEXT PRIMARY KEY,
            database_identity TEXT NOT NULL,
            from_version INTEGER NOT NULL,
            target_version INTEGER NOT NULL,
            migration_ids TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT NOT NULL,
            failure_stage TEXT,
            sanitized_error TEXT,
            safety_backup_reference TEXT,
            integrity_validation_result TEXT
        )
        """
    )


def _ordered_migrations(migrations: Iterable[LocalMigration]) -> tuple[LocalMigration, ...]:
    ordered = tuple(migrations)
    if tuple(sorted(ordered, key=lambda item: item.from_version)) != ordered:
        raise MigrationError(
            "migration_order_invalid", "Local migrations must be declared in order."
        )
    seen: set[str] = set()
    for migration in ordered:
        if migration.migration_id in seen:
            raise MigrationError("migration_id_duplicate", "Local migration IDs must be unique.")
        if (
            migration.migration_id in {"", "pending"}
            or migration.to_version <= migration.from_version
        ):
            raise MigrationError(
                "migration_definition_invalid",
                "Local migrations must be single-direction upgrades.",
            )
        seen.add(migration.migration_id)
    return ordered


def build_migration_plan(
    current_version: int, target_version: int, migrations: Iterable[LocalMigration]
) -> LocalMigrationPlan:
    ordered = _ordered_migrations(migrations)
    if current_version > target_version:
        raise MigrationError("downgrade_unsupported", "Local schema downgrade is not supported.")
    version = current_version
    selected: list[LocalMigration] = []
    while version < target_version:
        candidates = [migration for migration in ordered if migration.from_version == version]
        if len(candidates) != 1:
            raise MigrationError(
                "migration_path_missing", f"No unique migration path from version {version}."
            )
        migration = candidates[0]
        selected.append(migration)
        version = migration.to_version
    if version != target_version:
        raise MigrationError("migration_path_missing", "Local schema migration path is incomplete.")
    return LocalMigrationPlan(current_version, target_version, tuple(selected))


def inspect_schema(
    connection: sqlite3.Connection,
    migrations: Iterable[LocalMigration] = (),
    target_version: int = LOCAL_SCHEMA_VERSION,
) -> LocalSchemaInfo:
    if not _table_exists(connection, "local_schema_versions"):
        return LocalSchemaInfo(
            LocalSchemaState.UNKNOWN_OR_CORRUPT,
            None,
            target_version,
            message="Schema version table is missing.",
        )
    rows = connection.execute(
        "SELECT schema_version FROM local_schema_versions WHERE schema_name = 'LOCAL_DESKTOP'"
    ).fetchall()
    if len(rows) != 1 or not isinstance(rows[0][0], int) or rows[0][0] < 1:
        return LocalSchemaInfo(
            LocalSchemaState.UNKNOWN_OR_CORRUPT,
            None,
            target_version,
            message="Schema version record is missing or corrupt.",
        )
    current_version = rows[0][0]
    journal_exists = _table_exists(connection, "local_migration_journal")
    if (
        journal_exists
        and connection.execute(
            "SELECT 1 FROM local_migration_journal WHERE status = 'IN_PROGRESS' LIMIT 1"
        ).fetchone()
        is not None
    ):
        return LocalSchemaInfo(
            LocalSchemaState.MIGRATION_IN_PROGRESS,
            current_version,
            target_version,
            message="A previous migration attempt is still in progress.",
        )
    if (
        journal_exists
        and connection.execute(
            "SELECT 1 FROM local_migration_journal "
            "WHERE status = 'FAILED' ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        is not None
    ):
        return LocalSchemaInfo(
            LocalSchemaState.FAILED_MIGRATION,
            current_version,
            target_version,
            message="A previous local migration failed.",
        )
    if current_version > target_version:
        return LocalSchemaInfo(
            LocalSchemaState.NEWER_VERSION_UNSUPPORTED,
            current_version,
            target_version,
            message="The database is newer than this application supports.",
        )
    if current_version == target_version:
        return LocalSchemaInfo(LocalSchemaState.CURRENT, current_version, target_version)
    try:
        plan = build_migration_plan(current_version, target_version, migrations)
    except MigrationError as error:
        return LocalSchemaInfo(
            LocalSchemaState.UNKNOWN_OR_CORRUPT,
            current_version,
            target_version,
            message=error.message,
        )
    return LocalSchemaInfo(LocalSchemaState.UPGRADE_REQUIRED, current_version, target_version, plan)


def _sanitize_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {str(error)[:240]}"


def _validate_integrity(connection: sqlite3.Connection) -> tuple[str, int]:
    foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()
    if foreign_keys != (1,):
        raise MigrationError("foreign_keys_disabled", "SQLite foreign keys are not enabled.")
    violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise MigrationError("foreign_key_check_failed", "SQLite foreign-key validation failed.")
    integrity = connection.execute("PRAGMA integrity_check").fetchone()
    if integrity != ("ok",):
        raise MigrationError("integrity_check_failed", "SQLite integrity validation failed.")
    return str(integrity[0]), len(violations)


def run_migrations(
    engine: Engine,
    migrations: Iterable[LocalMigration],
    *,
    target_version: int = LOCAL_SCHEMA_VERSION,
    safety_backup: SafetyBackupReference | None = None,
    attempt_id: UUID | None = None,
) -> MigrationRunResult:
    if engine.dialect.name != "sqlite":
        raise MigrationError("sqlite_required", "Local migrations require SQLite.")
    database_url = make_url(str(engine.url)).database
    if not database_url or database_url == ":memory:":
        raise MigrationError(
            "file_database_required", "Local migrations require a file-backed database."
        )
    database = Path(database_url).expanduser().resolve()
    resolved_attempt_id = attempt_id or uuid4()
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        ensure_migration_journal(connection)
        connection.commit()
        connection.execute(
            "UPDATE local_migration_journal SET status = 'INTERRUPTED', "
            "completed_at = ? WHERE status = 'IN_PROGRESS'",
            (datetime.now(UTC).isoformat(),),
        )
        connection.commit()
        info = inspect_schema(connection, migrations, target_version)
        if info.state == LocalSchemaState.CURRENT:
            return MigrationRunResult(
                resolved_attempt_id,
                info.state,
                info.current_version or target_version,
                target_version,
                (),
                "ok",
                0,
            )
        if (
            info.state != LocalSchemaState.UPGRADE_REQUIRED
            or info.plan is None
            or info.current_version is None
        ):
            raise MigrationError("schema_not_migratable", info.message or info.state.value)
        if any(item.requires_safety_backup for item in info.plan.migrations):
            if (
                safety_backup is None
                or not safety_backup.validated
                or safety_backup.database_identity != _database_identity(database)
            ):
                raise MigrationError(
                    "safety_backup_required",
                    "A validated safety backup for the active database is required.",
                )
        migration_ids = json.dumps(info.plan.migration_ids, separators=(",", ":"))
        connection.execute(
            "INSERT INTO local_migration_journal ("
            "attempt_id, database_identity, from_version, target_version, "
            "migration_ids, started_at, status, safety_backup_reference) "
            "VALUES (?, ?, ?, ?, ?, ?, 'IN_PROGRESS', ?)",
            (
                str(resolved_attempt_id),
                _database_identity(database),
                info.current_version,
                target_version,
                migration_ids,
                datetime.now(UTC).isoformat(),
                safety_backup.reference if safety_backup else None,
            ),
        )
        connection.commit()
        try:
            connection.execute("BEGIN")
            for migration in info.plan.migrations:
                migration.apply(connection)
            integrity, violations = _validate_integrity(connection)
            connection.execute(
                "UPDATE local_schema_versions SET schema_version = ? "
                "WHERE schema_name = 'LOCAL_DESKTOP'",
                (target_version,),
            )
            connection.commit()
            connection.execute(
                "UPDATE local_migration_journal SET status = 'COMPLETED', "
                "completed_at = ?, integrity_validation_result = ? "
                "WHERE attempt_id = ?",
                (datetime.now(UTC).isoformat(), integrity, str(resolved_attempt_id)),
            )
            connection.commit()
            return MigrationRunResult(
                resolved_attempt_id,
                LocalSchemaState.CURRENT,
                info.current_version,
                target_version,
                info.plan.migration_ids,
                integrity,
                violations,
            )
        except Exception as error:
            connection.rollback()
            connection.execute(
                "UPDATE local_migration_journal SET status = 'FAILED', "
                "completed_at = ?, failure_stage = ?, sanitized_error = ? "
                "WHERE attempt_id = ?",
                (
                    datetime.now(UTC).isoformat(),
                    "execution",
                    _sanitize_error(error),
                    str(resolved_attempt_id),
                ),
            )
            connection.commit()
            if isinstance(error, MigrationError):
                raise
            raise MigrationError(
                "migration_failed", "Local migration failed; schema version was not advanced."
            ) from error
    finally:
        connection.close()
