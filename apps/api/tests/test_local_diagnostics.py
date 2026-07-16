from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import zipfile
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config import settings
from app.db.bootstrap import initialize_database
from app.main import app
from app.services.diagnostics.collectors import (
    collect_database,
    collect_migration,
    collect_pairing,
    collect_runtime,
    collect_startup,
)
from app.services.diagnostics.models import DiagnosticStatus, OverallStatus
from app.services.diagnostics.sanitization import sanitize_free_text
from app.services.diagnostics.service import collect_snapshot


@pytest.fixture()
def local_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[tuple[Engine, Path], None, None]:
    database = tmp_path / "sapsos.db"
    monkeypatch.setattr(settings, "product_mode", "LOCAL_DESKTOP")
    monkeypatch.setattr(settings, "database_url", f"sqlite+pysqlite:///{database.as_posix()}")
    monkeypatch.setattr(settings, "runtime_manifest_path", tmp_path / "runtime.json")
    monkeypatch.setattr(settings, "api_host", "127.0.0.1")
    engine = create_engine(settings.database_url)
    initialize_database(engine)
    yield engine, tmp_path
    engine.dispose()


def test_snapshot_contract_is_typed_and_deterministic(
    local_engine: tuple[Engine, Path],
) -> None:
    engine, _ = local_engine
    generated = datetime(2026, 7, 16, tzinfo=UTC)
    snapshot = collect_snapshot(engine, generated_at=generated)
    payload = snapshot.model_dump(mode="json")
    assert snapshot.contract_version == 1
    assert snapshot.generated_at == generated
    assert snapshot.application_mode == "LOCAL_DESKTOP"
    assert snapshot.overall_status in set(OverallStatus)
    assert snapshot.capabilities.bundle_export is True
    assert set(payload) == {
        "contract_version",
        "generated_at",
        "application_mode",
        "application_version",
        "platform_summary",
        "overall_status",
        "runtime_health",
        "api_health",
        "database_health",
        "schema_status",
        "migration_status",
        "restore_status",
        "pairing_status",
        "recent_startup_status",
        "warnings",
        "capabilities",
    }
    assert "sapsos.db" not in json.dumps(payload)


def test_unknown_is_not_reported_as_healthy(local_engine: tuple[Engine, Path]) -> None:
    engine, _ = local_engine
    runtime = collect_runtime(settings)
    startup = collect_startup(settings)
    assert runtime.status == DiagnosticStatus.UNKNOWN
    assert startup.status == DiagnosticStatus.NOT_RUN
    assert collect_snapshot(engine).overall_status != OverallStatus.HEALTHY


def test_database_collector_is_read_only(local_engine: tuple[Engine, Path]) -> None:
    engine, tmp_path = local_engine
    database = tmp_path / "sapsos.db"
    before = hashlib.sha256(database.read_bytes()).digest()
    result = collect_database(engine)
    after = hashlib.sha256(database.read_bytes()).digest()
    assert result.status == DiagnosticStatus.HEALTHY
    assert result.integrity_check_status == DiagnosticStatus.HEALTHY
    assert result.foreign_key_check_status == DiagnosticStatus.HEALTHY
    assert before == after


def test_database_missing_is_blocked_without_path_leakage(
    local_engine: tuple[Engine, Path],
) -> None:
    engine, tmp_path = local_engine
    engine.dispose()
    (tmp_path / "sapsos.db").unlink()
    result = collect_database(engine)
    assert result.status == DiagnosticStatus.BLOCKED
    assert result.reason_code == "database_missing"
    assert str(tmp_path) not in result.model_dump_json()


def test_migration_status_reads_current_schema_without_writing(
    local_engine: tuple[Engine, Path],
) -> None:
    engine, tmp_path = local_engine
    before = (tmp_path / "sapsos.db").read_bytes()
    result = collect_migration(engine)
    assert result.schema_status == "CURRENT"
    assert result.migration_required is False
    assert result.safety_backup_reference_exists is False
    assert (tmp_path / "sapsos.db").read_bytes() == before


def test_runtime_manifest_malformed_is_unknown(local_engine: tuple[Engine, Path]) -> None:
    _, tmp_path = local_engine
    (tmp_path / "runtime.json").write_text("not-json", encoding="utf-8")
    result = collect_runtime(settings)
    assert result.status == DiagnosticStatus.UNKNOWN
    assert result.manifest_parseable is False
    assert str(tmp_path) not in result.model_dump_json()


def test_pairing_secret_is_not_returned(local_engine: tuple[Engine, Path]) -> None:
    _, tmp_path = local_engine
    pairing = tmp_path / "pairing.json"
    pairing.write_text(
        json.dumps(
            {
                "protocol_version": 1,
                "credential": {
                    "verifier": "a" * 64,
                    "extension_id": "a" * 32,
                    "revoked_at": None,
                },
            }
        ),
        encoding="utf-8",
    )
    result = collect_pairing(settings)
    assert result.status == "PAIRED"
    assert "secret-verifier" not in result.model_dump_json()


def test_sanitizer_redacts_paths_tokens_urls_email_and_traceback() -> None:
    raw = (
        "Authorization: Bearer abc123 C:\\Users\\Alice\\db.sqlite "
        "\\\\server\\share\\db.sqlite alice@example.com "
        "https://example.test/path?token=secret#fragment\n"
        'Traceback (most recent call last):\n  File "C:\\x.py", line 1'
    )
    cleaned = sanitize_free_text(raw)
    assert "Alice" not in cleaned
    assert "abc123" not in cleaned
    assert "alice@example.com" not in cleaned
    assert "https://example.test" not in cleaned
    assert "C:\\x.py" not in cleaned


def test_local_diagnostics_endpoint_is_read_only(
    local_engine: tuple[Engine, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, _ = local_engine
    import app.api.local_diagnostics as local_diagnostics_api
    import app.main as main_module

    monkeypatch.setattr(local_diagnostics_api, "engine", engine)
    monkeypatch.setattr(main_module, "engine", engine)
    with TestClient(app) as client:
        response = client.get("/api/v1/local-diagnostics")
    assert response.status_code == 200
    assert response.json()["contract_version"] == 1


def test_server_mode_does_not_expose_local_diagnostics(
    local_engine: tuple[Engine, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, _ = local_engine
    import app.api.local_diagnostics as local_diagnostics_api
    import app.main as main_module

    monkeypatch.setattr(local_diagnostics_api, "engine", engine)
    monkeypatch.setattr(main_module, "engine", engine)
    monkeypatch.setattr(settings, "product_mode", "SERVER")
    with TestClient(app) as client:
        response = client.get("/api/v1/local-diagnostics")
    assert response.status_code == 404
    assert "sapsos.db" not in response.text


def test_local_diagnostics_export_is_fixed_allowlist_and_privacy_safe(
    local_engine: tuple[Engine, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, _ = local_engine
    import app.api.local_diagnostics as local_diagnostics_api
    import app.main as main_module

    monkeypatch.setattr(local_diagnostics_api, "engine", engine)
    monkeypatch.setattr(main_module, "engine", engine)
    with TestClient(app) as client:
        response = client.post("/api/v1/local-diagnostics/export")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as bundle:
        assert bundle.namelist() == [
            "manifest.json",
            "diagnostics.json",
            "startup-events.json",
            "README.txt",
        ]
        content = b"".join(bundle.read(name) for name in bundle.namelist())
        manifest = json.loads(bundle.read("manifest.json"))
        assert manifest["file_list"] == bundle.namelist()
        assert b"sapsos.db" not in content
        assert b"C:\\Users\\" not in content
        assert b"Authorization" not in content
        assert all(".." not in name for name in bundle.namelist())
        for name in bundle.namelist()[1:]:
            assert manifest["sha256"][name] == hashlib.sha256(bundle.read(name)).hexdigest()


def test_server_mode_does_not_expose_local_diagnostics_export(
    local_engine: tuple[Engine, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, _ = local_engine
    import app.api.local_diagnostics as local_diagnostics_api
    import app.main as main_module

    monkeypatch.setattr(local_diagnostics_api, "engine", engine)
    monkeypatch.setattr(main_module, "engine", engine)
    monkeypatch.setattr(settings, "product_mode", "SERVER")
    with TestClient(app) as client:
        response = client.post("/api/v1/local-diagnostics/export")
    assert response.status_code == 404
    assert "sapsos.db" not in response.text


def test_diagnostics_does_not_enable_or_modify_database_state(
    local_engine: tuple[Engine, Path],
) -> None:
    engine, tmp_path = local_engine
    database = tmp_path / "sapsos.db"
    with sqlite3.connect(database) as connection:
        before = connection.execute("PRAGMA user_version").fetchone()
    collect_snapshot(engine)
    with sqlite3.connect(database) as connection:
        after = connection.execute("PRAGMA user_version").fetchone()
    assert before == after


def test_collector_failure_isolated_to_snapshot(
    monkeypatch: pytest.MonkeyPatch, local_engine: tuple[Engine, Path]
) -> None:
    engine, _ = local_engine
    import app.services.diagnostics.service as diagnostics_service

    def fail_runtime(_settings: object) -> None:
        raise RuntimeError("C:\\Users\\private\\secret.log")

    monkeypatch.setattr(diagnostics_service, "collect_runtime", fail_runtime)
    snapshot = diagnostics_service.collect_snapshot(engine)
    assert snapshot.runtime_health.status == DiagnosticStatus.ERROR
    assert snapshot.api_health.status in {
        DiagnosticStatus.HEALTHY,
        DiagnosticStatus.DEGRADED,
        DiagnosticStatus.UNKNOWN,
    }
    assert "private" not in snapshot.model_dump_json()
