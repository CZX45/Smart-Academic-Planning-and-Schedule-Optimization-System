import json
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
    assert config["bundle"]["resources"][
        "../../dist/local-desktop-api/sapsos-api/**/*"
    ] == "runtime/sapsos-api/"


def test_windows_packaging_contract_has_no_release_or_auto_update_step() -> None:
    workflow = (ROOT / ".github/workflows/windows-installer-foundation.yml").read_text()
    script = (ROOT / "scripts/windows/Build-Windows-Installer.ps1").read_text()
    validator = (ROOT / "scripts/windows/Validate-Windows-Installer-Artifact.ps1").read_text()

    assert "actions/upload-artifact@v4" in workflow
    assert "desktop:installer:windows" in workflow
    assert "cargo install tauri-cli --version 2.11.4 --locked" in workflow
    assert "release" not in workflow.lower()
    assert "auto-update" not in script.lower()
    assert "signed = $false" in script
    assert "Get-FileHash" in validator
    assert "ExpectedCommit" in validator
    assert "required_runtime_resources" in script
    assert "licenses_notices" in script


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
