import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).parents[3]


def test_windows_identity_and_tauri_bundle_are_single_target_per_user() -> None:
    identity = json.loads((ROOT / "desktop-shell/desktop-identity.json").read_text())
    config = json.loads((ROOT / "desktop-shell/src-tauri/tauri.conf.json").read_text())

    assert identity["product_name"] == "SAPSOS Local Desktop"
    assert identity["version"] == config["version"]
    assert identity["bundle_identifier"] == config["identifier"]
    assert identity["windows_application_id"] == identity["bundle_identifier"]
    assert identity["executable_name"] == "sapsos-local-desktop.exe"
    assert identity["installer_artifact_name"] == "SAPSOS-Local-Desktop-{version}-x64-setup.exe"
    assert config["bundle"]["targets"] == ["nsis"]
    assert config["bundle"]["windows"]["nsis"]["installMode"] == "currentUser"
    assert (
        config["bundle"]["resources"]["../../dist/installer-stage/api/**/*"]
        == "runtime/sapsos-api/"
    )
    assert config["build"]["frontendDist"] == "../../dist/installer-stage/web"


def test_windows_packaging_contract_has_no_release_or_auto_update_step() -> None:
    workflow = (ROOT / ".github/workflows/windows-installer-foundation.yml").read_text()
    script = (ROOT / "scripts/windows/Build-Windows-Installer.ps1").read_text()
    validator = (ROOT / "scripts/windows/Validate-Windows-Installer-Artifact.ps1").read_text()

    assert "actions/upload-artifact@v4" in workflow
    assert "desktop:installer:windows" in workflow
    assert "desktop:installer:validate" in workflow
    assert "dist/windows-installer" in workflow
    assert workflow.index("pnpm desktop:installer:windows") < workflow.index(
        "cargo test --manifest-path desktop-shell/src-tauri/Cargo.toml"
    )
    assert "cargo install tauri-cli --version 2.11.4 --locked" in workflow
    assert "release" not in workflow.lower()
    assert "auto-update" not in script.lower()
    assert "signed = $false" in script
    assert "Get-Sha256" in validator
    assert "ExpectedCommit" in validator
    assert "required_runtime_resources" in script
    assert "licenses_notices" in script
    assert "data-retention-contract.json" in script
    assert "Validate-Packaging-Staging.ps1" in script
    assert "Validate-FastAPI-Runtime.ps1" in script
    assert "installer-stage" in script
    assert "$cleanup -TargetPath $stageRoot" in script
    build_order = [
        '"@sapsos/shared", "build"',
        '"pnpm", "openapi:check"',
        '"Build-Web-UI.ps1"',
        '"Build-FastAPI-Runtime.ps1"',
        '"Validate-Packaging-Staging.ps1"',
        "cargo tauri build --bundles nsis --ci",
        '"Validate-Windows-Installer-Artifact.ps1"',
    ]
    positions = [script.index(marker) for marker in build_order]
    assert positions == sorted(positions)


def test_short_staging_contract_preserves_deep_metadata_and_licenses() -> None:
    script = (ROOT / "scripts/windows/Build-Windows-Installer.ps1").read_text()
    validator = (ROOT / "scripts/windows/Validate-Windows-Installer-Artifact.ps1").read_text()
    assert 'Join-Path $stageRoot "api"' in script
    assert 'Join-Path $stageRoot "web"' in script
    assert "licenses_notices" in script
    assert "licenses_notices" in validator
    assert "tests?(?:" in validator


def test_stable_app_data_policy_is_explicit() -> None:
    identity = json.loads((ROOT / "desktop-shell/desktop-identity.json").read_text())
    assert identity["app_data_directory"] == "SAPSOS"
    assert identity["data_directory"] == "%LOCALAPPDATA%\\SAPSOS"
    assert identity["install_scope"] == "per-user"


def test_upgrade_and_uninstall_boundary_preserves_user_data() -> None:
    identity = json.loads((ROOT / "desktop-shell/desktop-identity.json").read_text())
    config = json.loads((ROOT / "desktop-shell/src-tauri/tauri.conf.json").read_text())
    decisions = (ROOT / "docs/DECISIONS.md").read_text(encoding="utf-8")
    plan = (ROOT / "docs/LOCAL_DESKTOP_EXECUTION_PLAN.md").read_text(encoding="utf-8")

    assert identity["install_directory"] != identity["data_directory"]
    assert config["bundle"]["windows"]["nsis"].get("installerHooks") is None
    assert "preserves that user data" in decisions
    assert "Upgrade preserves that data" in plan
    assert "uninstall" in decisions.lower()


def test_data_retention_contract_has_all_required_categories() -> None:
    contract = json.loads((ROOT / "desktop-shell/data-retention-contract.json").read_text())
    assert contract["data_root"] == "%LOCALAPPDATA%\\SAPSOS"
    assert contract["install_root"] == "%LOCALAPPDATA%\\Programs\\SAPSOS Local Desktop"
    assert set(contract["categories"]) == {
        "PERSISTENT_USER_DATA",
        "RECOVERABLE_OPERATIONAL_STATE",
        "EPHEMERAL_RUNTIME_STATE",
        "GENERATED_EXPORTS",
    }
    assert "SQLite" in " ".join(contract["rules"])


def test_packaging_staging_validator_records_files_and_rejects_forbidden_files() -> None:
    validator = ROOT / "scripts/windows/Validate-Packaging-Staging.ps1"
    with tempfile.TemporaryDirectory(dir=ROOT / "dist") as temporary:
        temporary_root = Path(temporary)
        api_root = temporary_root / "api"
        web_root = temporary_root / "web"
        api_root.mkdir()
        web_root.mkdir()
        (api_root / "sapsos-api.exe").write_bytes(b"api")
        (api_root / "app.py").write_text("print('ok')", encoding="utf-8")
        license_path = (
            api_root
            / "_internal"
            / "setuptools"
            / "_vendor"
            / "importlib_metadata-8.7.1.dist-info"
            / "licenses"
            / "LICENSE"
        )
        license_path.parent.mkdir(parents=True)
        license_path.write_text("license", encoding="utf-8")
        (web_root / "index.html").write_text("<html></html>", encoding="utf-8")
        manifest = temporary_root / "staging-manifest.json"
        valid = subprocess.run(
            [
                "pwsh",
                "-NoProfile",
                "-File",
                str(validator),
                "-ApiRoot",
                str(api_root),
                "-WebRoot",
                str(web_root),
                "-ManifestPath",
                str(manifest),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert valid.returncode == 0, valid.stderr
        staging = json.loads(manifest.read_text(encoding="utf-8"))
        assert any(
            record["path"].endswith("sapsos-api.exe")
            for record in staging["components"]["fastapi_runtime"]
        )
        assert any(
            record["path"].endswith("importlib_metadata-8.7.1.dist-info/licenses/LICENSE")
            for record in staging["components"]["fastapi_runtime"]
        )

        (web_root / ".env").write_text("SECRET=blocked", encoding="utf-8")
        invalid = subprocess.run(
            [
                "pwsh",
                "-NoProfile",
                "-File",
                str(validator),
                "-ApiRoot",
                str(api_root),
                "-WebRoot",
                str(web_root),
                "-ManifestPath",
                str(manifest),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert invalid.returncode != 0
        shutil.rmtree(temporary_root, ignore_errors=True)


def test_safe_build_cleanup_allows_child_output_and_rejects_dangerous_targets() -> None:
    helper = ROOT / "scripts/windows/Invoke-SafeBuildCleanup.ps1"
    temp_parent = (
        Path(os.environ.get("SystemRoot", "C:\\Windows")) / "Temp"
        if os.name == "nt"
        else Path("/tmp")
    )
    with tempfile.TemporaryDirectory(dir=temp_parent) as temporary:
        build_root = Path(temporary) / "dist"
        child = build_root / "stale-output"
        child.mkdir(parents=True)
        (child / "old.txt").write_text("stale", encoding="utf-8")
        valid = subprocess.run(
            [
                "pwsh",
                "-NoProfile",
                "-File",
                str(helper),
                "-TargetPath",
                str(child),
                "-AllowedBuildRoot",
                str(build_root),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert valid.returncode == 0, valid.stderr
        assert not child.exists()

        build_root.mkdir(parents=True, exist_ok=True)
        invalid = subprocess.run(
            [
                "pwsh",
                "-NoProfile",
                "-File",
                str(helper),
                "-TargetPath",
                str(build_root),
                "-AllowedBuildRoot",
                str(build_root),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert invalid.returncode != 0
        assert build_root.exists()
