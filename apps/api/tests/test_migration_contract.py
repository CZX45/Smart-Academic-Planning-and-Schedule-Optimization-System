from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from app.config import settings
from app.db.bootstrap import LOCAL_SCHEMA_VERSION, initialize_database
from app.db.local_migrations import LocalMigration
from app.runtime.migration_contract import execute, preflight


def configured_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    database = tmp_path / "SAPSOS" / "sapsos.db"
    database.parent.mkdir()
    engine = create_engine(f"sqlite+pysqlite:///{database}")
    initialize_database(engine)
    engine.dispose()
    monkeypatch.setattr(settings, "product_mode", "LOCAL_DESKTOP")
    monkeypatch.setattr(settings, "database_url", f"sqlite+pysqlite:///{database}")
    monkeypatch.setattr(settings, "runtime_manifest_path", database.parent / "runtime.json")
    return database


def test_current_preflight_is_machine_readable_and_does_not_require_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = configured_database(tmp_path, monkeypatch)
    result = preflight()
    assert result.contract_version == 1
    assert result.schema_status == "CURRENT"
    assert result.database_identity
    assert result.migration_required is False
    assert result.safety_backup_required is False
    assert not (database.parent / "migration-safety").exists()


def test_default_contract_uses_registered_local_migration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = configured_database(tmp_path, monkeypatch)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE local_schema_versions SET schema_version = 1 "
            "WHERE schema_name = 'LOCAL_DESKTOP'"
        )
    preview = preflight()
    assert preview.schema_status == "UPGRADE_REQUIRED"
    assert preview.migration_plan == ["20260824_course_source_field_verification"]
    applied = execute()
    assert applied.schema_status == "CURRENT"
    assert applied.migration_plan == ["20260824_course_source_field_verification"]
    assert applied.integrity_check == "ok"
    with sqlite3.connect(database) as connection:
        version = connection.execute("SELECT schema_version FROM local_schema_versions").fetchone()
    assert version == (LOCAL_SCHEMA_VERSION,)


def test_execute_binds_backup_to_attempt_and_runs_test_only_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = configured_database(tmp_path, monkeypatch)

    def first(connection: sqlite3.Connection) -> None:
        connection.execute("CREATE TABLE contract_fixture (value TEXT NOT NULL)")

    def second(connection: sqlite3.Connection) -> None:
        connection.execute("INSERT INTO contract_fixture(value) VALUES ('ok')")

    result = execute(
        migrations=[
            LocalMigration("contract-one", LOCAL_SCHEMA_VERSION, LOCAL_SCHEMA_VERSION + 1, first),
            LocalMigration(
                "contract-two", LOCAL_SCHEMA_VERSION + 1, LOCAL_SCHEMA_VERSION + 2, second
            ),
        ],
        target_version=LOCAL_SCHEMA_VERSION + 2,
    )
    assert result.schema_status == "CURRENT"
    assert result.attempt_id
    assert result.safety_backup_reference == (
        f"migration-safety/{result.attempt_id}/database.sqlite"
    )
    assert (database.parent / result.safety_backup_reference).is_file()


def test_server_mode_is_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    configured_database(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "product_mode", "SERVER")
    with pytest.raises(Exception, match="LOCAL_DESKTOP"):
        preflight()
