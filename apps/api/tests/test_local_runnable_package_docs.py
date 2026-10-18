import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

WINDOWS_SCRIPTS = [
    "scripts/windows/Start-Smart-Academic-Planner.ps1",
    "scripts/windows/Stop-Smart-Academic-Planner.ps1",
    "scripts/windows/Check-Prerequisites.ps1",
    "scripts/windows/Build-Browser-Extension.ps1",
    "scripts/windows/Open-Local-App.ps1",
]

REQUIRED_DOCS = [
    "docs/USER_SOFTWARE_MANUAL.md",
    "docs/LOCAL_APP_PACKAGE.md",
    "docs/KEAN_PORTAL_REAL_PAGE_QA.md",
]

REQUIRED_PACKAGE_SCRIPTS = [
    "app:check",
    "app:up",
    "app:down",
    "app:smoke",
    "extension:package",
]

PROHIBITED_MISLEADING_CLAIMS = [
    "auto-register",
    "guaranteed seat",
    "reserve seat",
    "seat grabbing",
    "live availability",
    "join waitlist automatically",
    "background polling",
    "automatic registration",
]

NEGATED_SAFETY_CONTEXTS = [
    "does not",
    "do not",
    "no ",
    "not ",
    "never",
    "without",
]


def test_phase_11c_windows_scripts_and_docs_exist() -> None:
    for relative_path in WINDOWS_SCRIPTS + REQUIRED_DOCS:
        assert (REPO_ROOT / relative_path).exists(), f"{relative_path} must exist"


def test_phase_11c_root_package_scripts_are_available() -> None:
    package_json = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = package_json.get("scripts", {})

    for script_name in REQUIRED_PACKAGE_SCRIPTS:
        assert script_name in scripts
        assert scripts[script_name].strip()

    assert "scripts/windows/Check-Prerequisites.ps1" in scripts["app:check"]
    assert "scripts/windows/Start-Smart-Academic-Planner.ps1" in scripts["app:up"]
    assert "scripts/windows/Stop-Smart-Academic-Planner.ps1" in scripts["app:down"]
    assert "scripts/smoke-test-local.mjs" in scripts["app:smoke"]
    assert "scripts/package-extension.mjs" in scripts["extension:package"]


def test_phase_11c_docs_reference_local_runtime_and_kean_manual_qa() -> None:
    combined = "\n".join(
        (REPO_ROOT / relative_path).read_text(encoding="utf-8").lower()
        for relative_path in REQUIRED_DOCS
    )

    for required_text in [
        "scripts\\windows\\start-smart-academic-planner.ps1",
        "http://localhost:3000",
        "http://localhost:8000",
        "corepack pnpm extension:package",
        "https://kean-ss.colleague.elluciancloud.com/student",
        "manual review",
        "non-official",
        "docker desktop",
    ]:
        assert required_text in combined

    assert "中文" in combined
    assert "english" in combined


def test_phase_11c_docs_do_not_make_misleading_prohibited_claims() -> None:
    combined = "\n".join(
        (REPO_ROOT / relative_path).read_text(encoding="utf-8").lower()
        for relative_path in REQUIRED_DOCS + ["README.md"]
    )

    for claim in PROHIBITED_MISLEADING_CLAIMS:
        for match in re.finditer(re.escape(claim), combined):
            line_start = combined.rfind("\n", 0, match.start()) + 1
            line_end = combined.find("\n", match.end())
            line_end = len(combined) if line_end == -1 else line_end
            context = combined[line_start:line_end]
            assert any(negation in context for negation in NEGATED_SAFETY_CONTEXTS), (
                f"Misleading unqualified claim '{claim}' found near: {context!r}"
            )
