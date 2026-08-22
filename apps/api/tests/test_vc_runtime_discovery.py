from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from build_support.vc_runtime import resolve_msvcp140

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_resolve_msvcp140_uses_64_bit_system_runtime(tmp_path: Path) -> None:
    system_root = tmp_path / "Windows"
    runtime = system_root / "System32" / "MSVCP140.dll"
    runtime.parent.mkdir(parents=True)
    runtime.write_bytes(b"system-runtime")

    resolved = resolve_msvcp140(
        system_root=system_root,
        python_base=tmp_path / "Python",
        program_files_roots=(),
    )

    assert resolved == runtime.resolve()


def test_resolve_msvcp140_falls_back_to_latest_visual_studio_x64_redist(
    tmp_path: Path,
) -> None:
    program_files = tmp_path / "Program Files"
    older = (
        program_files
        / "Microsoft Visual Studio/2022/Enterprise/VC/Redist/MSVC/14.44.0"
        / "x64/Microsoft.VC143.CRT/MSVCP140.dll"
    )
    newer = (
        program_files
        / "Microsoft Visual Studio/18/Enterprise/VC/Redist/MSVC/14.51.0"
        / "x64/Microsoft.VC143.CRT/MSVCP140.dll"
    )
    older.parent.mkdir(parents=True)
    newer.parent.mkdir(parents=True)
    older.write_bytes(b"older-runtime")
    newer.write_bytes(b"newer-runtime")

    resolved = resolve_msvcp140(
        system_root=tmp_path / "Windows",
        python_base=tmp_path / "Python",
        program_files_roots=(program_files,),
    )

    assert resolved == newer.resolve()


def test_resolve_msvcp140_fails_with_searched_locations(tmp_path: Path) -> None:
    system_root = tmp_path / "Windows"
    python_base = tmp_path / "Python"
    program_files = tmp_path / "Program Files"

    with pytest.raises(FileNotFoundError) as error:
        resolve_msvcp140(
            system_root=system_root,
            python_base=python_base,
            program_files_roots=(program_files,),
        )

    message = str(error.value)
    assert "MSVCP140.dll" in message
    assert str(system_root / "System32" / "MSVCP140.dll") in message
    assert str(program_files) in message


@pytest.mark.skipif(
    sys.platform != "win32" or shutil.which("pwsh") is None,
    reason="The packaged VC runtime staging boundary is Windows-only.",
)
def test_missing_pyinstaller_vc_runtime_is_staged_from_trusted_windows_source(
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "sapsos-api"
    runtime_root.mkdir()
    script = REPO_ROOT / "scripts/windows/Ensure-Packaged-VCRuntime.ps1"

    result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(script),
            "-RuntimeRoot",
            str(runtime_root),
            "-Python",
            sys.executable,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    staged_runtime = runtime_root / "MSVCP140.dll"
    assert staged_runtime.is_file()
    assert staged_runtime.stat().st_size > 0


@pytest.mark.skipif(
    sys.platform != "win32" or shutil.which("pwsh") is None,
    reason="The packaged VC runtime staging boundary is Windows-only.",
)
def test_existing_vc_runtime_returns_control_to_build_caller(tmp_path: Path) -> None:
    runtime_root = tmp_path / "sapsos-api"
    runtime_root.mkdir()
    system_runtime = Path("C:/Windows/System32/MSVCP140.dll")
    shutil.copy2(system_runtime, runtime_root / "MSVCP140.dll")
    marker = tmp_path / "caller-continued.txt"
    ensure_script = REPO_ROOT / "scripts/windows/Ensure-Packaged-VCRuntime.ps1"
    wrapper = tmp_path / "invoke-ensure.ps1"
    wrapper.write_text(
        "& '"
        + str(ensure_script).replace("'", "''")
        + "' -RuntimeRoot '"
        + str(runtime_root).replace("'", "''")
        + "' -Python '"
        + sys.executable.replace("'", "''")
        + "'\nSet-Content -LiteralPath '"
        + str(marker).replace("'", "''")
        + "' -Value 'continued' -NoNewline\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["pwsh", "-NoProfile", "-File", str(wrapper)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert marker.read_text(encoding="utf-8") == "continued"
