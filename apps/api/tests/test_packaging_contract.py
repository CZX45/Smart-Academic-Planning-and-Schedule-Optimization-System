from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_pyinstaller_contract_is_one_folder_and_local_desktop_only() -> None:
    spec = (REPO_ROOT / "apps/api/packaging/sapsos-api.spec").read_text(encoding="utf-8")
    assert 'name="sapsos-api"' in spec
    assert "console=True" in spec
    assert "onefile" not in spec.lower()
    assert "COLLECT(" in spec
    assert 'contents_directory="."' in spec
    assert "_pydantic_core*.pyd" in spec
    assert "pydantic_core._pydantic_core" in spec
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


def test_web_ui_packaging_uses_static_export_and_runtime_bridge() -> None:
    next_config = (REPO_ROOT / "apps/web/next.config.ts").read_text(encoding="utf-8")
    build_script = (REPO_ROOT / "scripts/windows/Build-Web-UI.ps1").read_text(encoding="utf-8")
    tauri_config = (REPO_ROOT / "desktop-shell/src-tauri/tauri.conf.json").read_text(
        encoding="utf-8"
    )
    shell_source = (REPO_ROOT / "desktop-shell/src-tauri/src/main.rs").read_text(encoding="utf-8")

    assert 'output: "export"' in next_config
    assert "dist\\local-desktop-web" in build_script
    assert "api_base_url" in build_script
    assert '"frontendDist": "../../dist/installer-stage/web"' in tauri_config
    assert '"../../dist/installer-stage/runtime-payload.zip": "runtime-payload.zip"' in tauri_config
    assert (
        '"../../dist/installer-stage/runtime-payload-metadata.json": '
        '"runtime-payload-metadata.json"'
    ) in tauri_config
    assert "../../dist/local-desktop-api" not in tauri_config
    assert "../../dist/local-desktop-web" not in tauri_config
    assert "WebviewUrl::App" in shell_source
    assert "api_base_url" in shell_source
    assert "#[cfg(debug_assertions)]" in shell_source
