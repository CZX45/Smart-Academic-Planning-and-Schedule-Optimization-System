from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.db.bootstrap import initialize_database
from app.db.local_migrations import (
    LocalMigration,
    LocalSchemaState,
    MigrationError,
    SafetyBackupReference,
    build_migration_plan,
    ensure_migration_journal,
    inspect_schema,
    run_migrations,
)


def migration_engine(tmp_path: Path) -> tuple[Engine, Path]:
    database = tmp_path / "local.sqlite"
    engine = create_engine(f"sqlite+pysqlite:///{database}")
    initialize_database(engine)
    return engine, database


def set_version(database: Path, version: int) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE local_schema_versions SET schema_version = ? "
            "WHERE schema_name = 'LOCAL_DESKTOP'",
            (version,),
        )


def test_current_schema_is_detected(tmp_path: Path) -> None:
    engine, _ = migration_engine(tmp_path)
    with sqlite3.connect(tmp_path / "local.sqlite") as connection:
        info = inspect_schema(connection, target_version=1)
    assert info.state == LocalSchemaState.CURRENT
    assert info.current_version == 1
    engine.dispose()


def test_old_schema_plan_is_deterministic_and_rejects_missing_path() -> None:
    first = LocalMigration("one", 1, 2, lambda connection: None)
    second = LocalMigration("two", 2, 3, lambda connection: None)
    plan = build_migration_plan(1, 3, [first, second])
    assert plan.migration_ids == ("one", "two")
    with pytest.raises(MigrationError, match="unique migration path"):
        build_migration_plan(1, 3, [second])


def test_newer_schema_is_fail_closed(tmp_path: Path) -> None:
    engine, database = migration_engine(tmp_path)
    set_version(database, 2)
    with sqlite3.connect(database) as connection:
        info = inspect_schema(connection, target_version=1)
    assert info.state == LocalSchemaState.NEWER_VERSION_UNSUPPORTED
    with pytest.raises(MigrationError, match="newer"):
        run_migrations(engine, [], target_version=1)


def test_interrupted_attempt_is_detected(tmp_path: Path) -> None:
    _, database = migration_engine(tmp_path)
    with sqlite3.connect(database) as connection:
        ensure_migration_journal(connection)
        connection.execute(
            "INSERT INTO local_migration_journal ("
            "attempt_id, database_identity, from_version, target_version, "
            "migration_ids, started_at, status) VALUES "
            "('attempt', 'identity', 1, 2, '[\"one\"]', "
            "'2026-07-16T00:00:00+00:00', 'IN_PROGRESS')"
        )
        info = inspect_schema(
            connection, [LocalMigration("one", 1, 2, lambda _: None)], target_version=2
        )
    assert info.state == LocalSchemaState.MIGRATION_IN_PROGRESS


def test_migrations_run_in_declared_order_and_do_not_replay(tmp_path: Path) -> None:
    engine, database = migration_engine(tmp_path)
    set_version(database, 1)
    calls: list[str] = []

    def first(connection: sqlite3.Connection) -> None:
        calls.append("first")
        connection.execute("CREATE TABLE migration_fixture (value TEXT NOT NULL)")

    def second(connection: sqlite3.Connection) -> None:
        calls.append("second")
        connection.execute("INSERT INTO migration_fixture(value) VALUES ('ok')")

    migrations = [LocalMigration("first", 1, 2, first), LocalMigration("second", 2, 3, second)]
    result = run_migrations(engine, migrations, target_version=3)
    assert result.state == LocalSchemaState.CURRENT
    assert calls == ["first", "second"]
    result = run_migrations(engine, migrations, target_version=3)
    assert result.migration_ids == ()
    assert calls == ["first", "second"]
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT value FROM migration_fixture").fetchall() == [("ok",)]


def test_failed_migration_stops_sequence_and_does_not_advance_version(tmp_path: Path) -> None:
    engine, database = migration_engine(tmp_path)
    calls: list[str] = []

    def failing(connection: sqlite3.Connection) -> None:
        calls.append("failing")
        connection.execute("CREATE TABLE rollback_fixture (value TEXT NOT NULL)")
        connection.execute("INSERT INTO rollback_fixture(value) VALUES ('rolled back')")
        raise RuntimeError("fixture failure")

    def never(connection: sqlite3.Connection) -> None:
        calls.append("never")

    with pytest.raises(MigrationError, match="failed"):
        run_migrations(
            engine,
            [LocalMigration("failing", 1, 2, failing), LocalMigration("never", 2, 3, never)],
            target_version=3,
        )
    assert calls == ["failing"]
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT schema_version FROM local_schema_versions"
        ).fetchone() == (1,)
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name = 'rollback_fixture'"
            ).fetchone()
            is None
        )
        assert connection.execute("SELECT status FROM local_migration_journal").fetchone() == (
            "FAILED",
        )


def test_destructive_migration_requires_validated_active_database_backup(tmp_path: Path) -> None:
    engine, database = migration_engine(tmp_path)
    destructive = LocalMigration(
        "destructive", 1, 2, lambda connection: None, requires_safety_backup=True
    )
    with pytest.raises(MigrationError, match="safety backup"):
        run_migrations(engine, [destructive], target_version=2)
    reference = SafetyBackupReference("backup-1", "wrong", validated=True)
    with pytest.raises(MigrationError, match="safety backup"):
        run_migrations(engine, [destructive], target_version=2, safety_backup=reference)
    reference = SafetyBackupReference(
        "backup-1", hashlib.sha256(str(database.resolve()).encode()).hexdigest()
    )
    result = run_migrations(engine, [destructive], target_version=2, safety_backup=reference)
    assert result.state == LocalSchemaState.CURRENT


def test_foreign_key_validation_is_required(tmp_path: Path) -> None:
    engine, database = migration_engine(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE child (parent_id INTEGER REFERENCES parent(id))")
        connection.execute("INSERT INTO child(parent_id) VALUES (99)")

    def create_bad_data(connection: sqlite3.Connection) -> None:
        pass

    with pytest.raises(MigrationError, match="foreign"):
        run_migrations(engine, [LocalMigration("bad-fk", 1, 2, create_bad_data)], target_version=2)
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT schema_version FROM local_schema_versions"
        ).fetchone() == (1,)


def test_server_engine_is_not_handled_by_local_runner(tmp_path: Path) -> None:
    engine = cast(object, SimpleNamespace(dialect=SimpleNamespace(name="postgresql")))
    with pytest.raises(MigrationError, match="SQLite"):
        run_migrations(cast("Engine", engine), [])
