from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_pyinstaller_contract_is_one_folder_and_local_desktop_only() -> None:
    spec = (REPO_ROOT / "apps/api/packaging/sapsos-api.spec").read_text(encoding="utf-8")
    assert 'name="sapsos-api"' in spec
    assert "console=True" in spec
    assert "onefile" not in spec.lower()
    assert "COLLECT(" in spec
    assert 'ROOT / "app" / "run.py"' in spec
    assert '"tests"' in spec


def test_build_script_has_reproducible_output_and_actionable_failures() -> None:
    script = (REPO_ROOT / "scripts/windows/Build-FastAPI-Runtime.ps1").read_text(encoding="utf-8")
    assert "requirements.txt" in script
    assert "--noconfirm" in script
    assert "--clean" in script
    assert "sapsos-api\\sapsos-api.exe" in script
    assert "end users do not need Python" in script


def test_desktop_shell_requires_explicit_packaged_artifact_when_selected() -> None:
    source = (REPO_ROOT / "desktop-shell/src-tauri/src/main.rs").read_text(encoding="utf-8")
    assert "SAPSOS_API_EXECUTABLE" in source
    assert "Packaged FastAPI artifact was not found" in source
    assert "api_working_directory" in source
    assert '"-m".to_string(), "app.run".to_string()' in source
