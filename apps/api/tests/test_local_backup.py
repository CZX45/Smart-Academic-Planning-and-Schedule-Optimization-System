from __future__ import annotations

import shutil
import sqlite3
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config import settings
from app.db.bootstrap import initialize_database
from app.services.local_backup import (
    BackupError,
    create_backup_archive,
    validate_backup_archive,
)


def local_engine(path: Path) -> Engine:
    engine = create_engine(f"sqlite+pysqlite:///{path}")
    initialize_database(engine)
    return engine


def test_backup_uses_active_custom_sqlite_filename_and_validates_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "student-data-custom.sqlite"
    engine = local_engine(database)
    monkeypatch.setattr(settings, "product_mode", "LOCAL_DESKTOP")
    monkeypatch.setattr(settings, "database_url", f"sqlite+pysqlite:///{database}")

    archive, manifest = create_backup_archive(engine)
    try:
        assert manifest.database_payload_filename == "database.sqlite"
        assert manifest.database_size_bytes > 0
        validated = validate_backup_archive(archive)
        assert validated.backup_id == manifest.backup_id
        with zipfile.ZipFile(archive) as opened:
            assert opened.namelist() == ["manifest.json", "database.sqlite"]
    finally:
        shutil.rmtree(archive.parent, ignore_errors=True)


def test_backup_rejects_memory_database(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    monkeypatch.setattr(settings, "product_mode", "LOCAL_DESKTOP")
    with pytest.raises(BackupError, match="in-memory"):
        create_backup_archive(engine)


def test_backup_rejects_server_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / "data.sqlite"
    engine = local_engine(database)
    monkeypatch.setattr(settings, "product_mode", "SERVER")
    with pytest.raises(BackupError, match="LOCAL_DESKTOP"):
        create_backup_archive(engine)


def test_backup_rejects_foreign_key_violation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "broken.sqlite"
    engine = local_engine(database)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE child (parent_id INTEGER REFERENCES parent(id))")
        connection.execute("INSERT INTO child(parent_id) VALUES (99)")
    monkeypatch.setattr(settings, "product_mode", "LOCAL_DESKTOP")
    with pytest.raises(BackupError, match="foreign-key"):
        create_backup_archive(engine)


def test_archive_validator_rejects_unexpected_entries(tmp_path: Path) -> None:
    archive = tmp_path / "unexpected.zip"
    with zipfile.ZipFile(archive, "w") as opened:
        opened.writestr("manifest.json", "{}")
        opened.writestr("database.sqlite", b"not sqlite")
        opened.writestr("pairing.json", b"secret")
    with pytest.raises(BackupError, match="exactly"):
        validate_backup_archive(archive)
