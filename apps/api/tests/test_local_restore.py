from __future__ import annotations

import io
import shutil
from pathlib import Path

import pytest
from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config import settings
from app.db.bootstrap import initialize_database
from app.services.local_backup import (
    BackupError,
    cancel_restore,
    confirm_restore,
    create_backup_archive,
    validate_and_stage_restore,
)


def local_engine(path: Path) -> Engine:
    engine = create_engine(f"sqlite+pysqlite:///{path}")
    initialize_database(engine)
    return engine


def test_restore_validation_stages_candidate_and_confirmation_only_writes_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "custom.sqlite"
    engine = local_engine(database)
    monkeypatch.setattr(settings, "product_mode", "LOCAL_DESKTOP")
    monkeypatch.setattr(settings, "runtime_manifest_path", tmp_path / "runtime.json")

    archive, _ = create_backup_archive(engine)
    try:
        upload = UploadFile(filename="backup.sapsos-backup", file=io.BytesIO(archive.read_bytes()))
        preview = validate_and_stage_restore(engine, upload)
        assert preview.compatibility == "exact_supported_schema"
        assert not (tmp_path / "pending-restore.json").exists()
        with pytest.raises(BackupError, match="Type RESTORE"):
            confirm_restore(engine, preview.session_id, "yes")
        result = confirm_restore(engine, preview.session_id, "RESTORE")
        assert result.restart_required is True
        assert (tmp_path / "pending-restore.json").is_file()
    finally:
        shutil.rmtree(archive.parent, ignore_errors=True)


def test_restore_cancellation_removes_staged_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "custom.sqlite"
    engine = local_engine(database)
    monkeypatch.setattr(settings, "product_mode", "LOCAL_DESKTOP")
    monkeypatch.setattr(settings, "runtime_manifest_path", tmp_path / "runtime.json")
    archive, _ = create_backup_archive(engine)
    try:
        upload = UploadFile(filename="backup.sapsos-backup", file=io.BytesIO(archive.read_bytes()))
        preview = validate_and_stage_restore(engine, upload)
        cancel_restore(engine, preview.session_id)
        assert not list((tmp_path / "restore-staging").glob(f"{preview.session_id}.*"))
    finally:
        shutil.rmtree(archive.parent, ignore_errors=True)
