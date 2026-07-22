import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]
COORDINATOR = ROOT / "desktop-shell/src-tauri/windows/InstallerProcessCoordination.ps1"
HOOK = ROOT / "desktop-shell/src-tauri/windows/installer-hooks.nsh"


def test_nsis_preinstall_only_rewrites_tauri_default_root() -> None:
    hook = HOOK.read_text(encoding="utf-8")
    preinstall = hook.split("!macro NSIS_HOOK_PREINSTALL", 1)[1].split(
        "!macroend", 1
    )[0]
    preuninstall = hook.split("!macro NSIS_HOOK_PREUNINSTALL", 1)[1].split(
        "!macroend", 1
    )[0]

    assert 'StrCmp $INSTDIR "$LOCALAPPDATA\\${PRODUCTNAME}"' in preinstall
    assert 'StrCpy $INSTDIR "$LOCALAPPDATA\\Programs\\${PRODUCTNAME}"' in preinstall
    assert preinstall.index("StrCmp") < preinstall.index("nsExec::ExecToLog")
    assert "StrCpy $INSTDIR" not in preuninstall


def test_coordinator_has_structured_codes_and_privacy_safe_diagnostics() -> None:
    coordinator = COORDINATOR.read_text(encoding="utf-8")

    for marker in (
        "Success = 0",
        "RealRunningProcess = 10",
        "InvalidInstallRoot = 20",
        "ProcessInspectionError = 30",
        "InternalError = 40",
        'category = $Category',
        'received_root = $InstallRoot',
        'trusted_candidates = $candidateRecords',
        "SAPSOS\\installer-preflight",
    ):
        assert marker in coordinator
    assert "command_line" not in coordinator
    assert "student" not in coordinator.lower()
    assert "sqlite" not in coordinator.lower()


@pytest.mark.skipif(os.name != "nt", reason="requires Windows PowerShell process inspection")
def test_coordinator_clean_root_and_invalid_root_exit_categories(tmp_path: Path) -> None:
    stable_root = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "SAPSOS Local Desktop"
    common = [
        "pwsh",
        "-NoProfile",
        "-File",
        str(COORDINATOR),
        "-InstallerVersion",
        "test",
        "-DiagnosticDirectory",
        str(tmp_path),
    ]
    clean = subprocess.run(
        [*common, "-InstallRoot", str(stable_root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    invalid = subprocess.run(
        [*common, "-InstallRoot", str(Path(os.environ["TEMP"]) / "nsis-test-root")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert clean.returncode == 0
    assert "SAPSOS is running" not in clean.stdout
    assert invalid.returncode == 20
    assert "stable per-user install directory" in invalid.stdout
    diagnostics = list(tmp_path.glob("*.json"))
    assert len(diagnostics) == 1
    record = json.loads(diagnostics[0].read_text(encoding="utf-8"))
    assert record["category"] == "INVALID_INSTALL_ROOT"
    assert record["exit_code"] == 20
    assert record["trusted_candidates"] == []
