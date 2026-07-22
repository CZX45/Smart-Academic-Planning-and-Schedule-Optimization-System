import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path
from typing import cast

import pytest

ROOT = Path(__file__).parents[3]
INSTALLER = ROOT / "desktop-shell/src-tauri/windows/Install-Runtime-Payload.ps1"


pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires Windows PowerShell")


def create_payload(tmp_path: Path, suffix: str = "") -> tuple[Path, Path]:
    source = tmp_path / f"payload-source{suffix}"
    source.mkdir()
    (source / "sapsos-api.exe").write_bytes(b"api")
    (source / "MSVCP140.dll").write_bytes(b"vc-runtime")
    (source / "_internal").mkdir()
    (source / "_internal" / "_pydantic_core.pyd").write_bytes(b"pydantic")
    archive = tmp_path / f"runtime-payload{suffix}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as payload:
        for path in source.rglob("*"):
            if path.is_file():
                payload.write(path, path.relative_to(source).as_posix())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    metadata = tmp_path / f"runtime-payload-metadata{suffix}.json"
    metadata.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source": "dist/installer-stage/api",
                "commit": "test-commit",
                "installer_version": "0.1.3",
                "archive_sha256": digest,
                "required_runtime_files": ["sapsos-api.exe", "MSVCP140.dll"],
            }
        ),
        encoding="utf-8",
    )
    return archive, metadata


def run_payload(
    install_root: Path,
    archive: Path,
    metadata: Path,
    diagnostics: Path,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(INSTALLER),
            "-InstallRoot",
            str(install_root),
            "-PayloadArchivePath",
            str(archive),
            "-PayloadMetadataPath",
            str(metadata),
            "-InstallerVersion",
            "0.1.3",
            "-DiagnosticDirectory",
            str(diagnostics),
            *extra,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def begin_attempt(install_root: Path, diagnostics: Path) -> None:
    result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(INSTALLER),
            "-InstallRoot",
            str(install_root),
            "-InstallerVersion",
            "0.1.3",
            "-DiagnosticDirectory",
            str(diagnostics),
            "-BeginAttempt",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def remove_installed_runtime(
    install_root: Path, diagnostics: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(INSTALLER),
            "-InstallRoot",
            str(install_root),
            "-DiagnosticDirectory",
            str(diagnostics),
            "-RemoveInstalledRuntime",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def read_latest_diagnostic(diagnostics: Path) -> dict[str, object]:
    records = sorted(diagnostics.glob("runtime-install-*.json"), key=lambda p: p.stat().st_mtime)
    assert records
    return cast(dict[str, object], json.loads(records[-1].read_text(encoding="utf-8-sig")))


def test_clean_install_and_runtime_integrity(tmp_path: Path) -> None:
    archive, metadata = create_payload(tmp_path)
    install_root = tmp_path / "Programs" / "SAPSOS Local Desktop"
    diagnostics = tmp_path / "diagnostics"

    result = run_payload(install_root, archive, metadata, diagnostics)

    assert result.returncode == 0, result.stderr or result.stdout
    assert (install_root / "runtime/sapsos-api/sapsos-api.exe").is_file()
    assert (install_root / "runtime/sapsos-api/MSVCP140.dll").is_file()
    assert not archive.exists()
    assert not metadata.exists()
    record = read_latest_diagnostic(diagnostics)
    assert record["install_mode"] == "clean_install"
    assert record["status"] == "succeeded"
    assert record["final_outcome"] == "runtime_payload_installed"


def test_existing_runtime_is_replaced_and_user_data_is_not_touched(tmp_path: Path) -> None:
    archive, metadata = create_payload(tmp_path)
    install_root = tmp_path / "Programs" / "SAPSOS Local Desktop"
    old_runtime = install_root / "runtime/sapsos-api"
    old_runtime.mkdir(parents=True)
    (old_runtime / "sapsos-api.exe").write_bytes(b"old")
    (old_runtime / "MSVCP140.dll").write_bytes(b"old-vc")
    data_root = tmp_path / "SAPSOS"
    data_root.mkdir()
    sentinel = data_root / "sapsos.db"
    sentinel.write_bytes(b"user-data")

    result = run_payload(install_root, archive, metadata, tmp_path / "diagnostics")

    assert result.returncode == 0, result.stderr or result.stdout
    assert (old_runtime / "MSVCP140.dll").read_bytes() == b"vc-runtime"
    assert sentinel.read_bytes() == b"user-data"


def test_uninstall_cleanup_removes_runtime_but_preserves_user_data(tmp_path: Path) -> None:
    archive, metadata = create_payload(tmp_path)
    install_root = tmp_path / "Programs" / "SAPSOS Local Desktop"
    diagnostics = tmp_path / "diagnostics"
    result = run_payload(install_root, archive, metadata, diagnostics)
    assert result.returncode == 0, result.stderr or result.stdout
    (install_root / "runtime-payload.zip").write_bytes(b"stale-archive")
    (install_root / "runtime-payload-metadata.json").write_text("{}", encoding="utf-8")
    data_root = tmp_path / "SAPSOS"
    data_root.mkdir()
    sentinel = data_root / "sapsos.db"
    sentinel.write_bytes(b"user-data")

    cleanup = remove_installed_runtime(install_root, diagnostics)

    assert cleanup.returncode == 0, cleanup.stderr or cleanup.stdout
    assert not (install_root / "runtime/sapsos-api").exists()
    assert not (install_root / "runtime-payload.zip").exists()
    assert not (install_root / "runtime-payload-metadata.json").exists()
    assert sentinel.read_bytes() == b"user-data"


@pytest.mark.parametrize(
    ("error_code", "category"),
    [("32", "sharing_violation"), ("5", "access_denied")],
)
def test_write_failure_is_categorized_bounded_and_preserved(
    tmp_path: Path, error_code: str, category: str
) -> None:
    archive, metadata = create_payload(tmp_path)
    install_root = tmp_path / "Programs" / "SAPSOS Local Desktop"
    diagnostics = tmp_path / "diagnostics"
    begin_attempt(install_root, diagnostics)

    result = run_payload(
        install_root,
        archive,
        metadata,
        diagnostics,
        "-TestMode",
        "-SimulateWin32ErrorCode",
        error_code,
    )

    assert result.returncode != 0
    assert not (install_root / "runtime/sapsos-api/MSVCP140.dll").exists()
    record = read_latest_diagnostic(diagnostics)
    assert record["status"] == "failed"
    assert record["final_outcome"] == "installation_failed"
    assert record["windows_error_code"] == int(error_code)
    assert record["windows_error_category"] == category
    assert record["retry_count"] == (3 if error_code == "32" else 0)
    assert archive.exists()


def test_partial_install_recovers_without_deleting_user_data(tmp_path: Path) -> None:
    archive, metadata = create_payload(tmp_path)
    install_root = tmp_path / "Programs" / "SAPSOS Local Desktop"
    incomplete_runtime = install_root / "runtime/sapsos-api"
    incomplete_runtime.mkdir(parents=True)
    (incomplete_runtime / "sapsos-api.exe").write_bytes(b"partial")
    (install_root / "sapsos-local-desktop.exe").write_bytes(b"partial-app")
    user_data = tmp_path / "SAPSOS" / "sapsos.db"
    user_data.parent.mkdir()
    user_data.write_bytes(b"preserve")

    result = run_payload(install_root, archive, metadata, tmp_path / "diagnostics")

    assert result.returncode == 0, result.stderr or result.stdout
    assert (install_root / "runtime/sapsos-api/MSVCP140.dll").is_file()
    assert user_data.read_bytes() == b"preserve"
    assert read_latest_diagnostic(tmp_path / "diagnostics")["install_mode"] == "partial_install"
