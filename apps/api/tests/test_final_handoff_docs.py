from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

PHASE_10B_REQUIRED_DOCS = [
    "docs/FINAL_PROJECT_SUMMARY.md",
    "docs/FINAL_DEMO_SCRIPT.md",
    "docs/FEATURE_INVENTORY.md",
    "docs/FINAL_ARCHITECTURE_SNAPSHOT.md",
    "docs/KNOWN_LIMITATIONS_AND_FUTURE_WORK.md",
    "docs/FINAL_SAFETY_AND_NON_AUTOMATION_STATEMENT.md",
    "docs/HANDOFF_CHECKLIST.md",
]

REQUIRED_SAFE_LANGUAGE = [
    "read-only import",
    "manual review",
    "advisory",
    "verify in the official portal",
    "non-official",
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

ALLOWED_NEGATED_SAFETY_PHRASES = [
    "does not reserve seats",
]


def test_phase_10b_final_handoff_docs_exist_and_keep_safe_language() -> None:
    combined_docs = []
    for relative_path in PHASE_10B_REQUIRED_DOCS:
        doc_path = REPO_ROOT / relative_path
        assert doc_path.exists(), f"{relative_path} must exist for final handoff"
        combined_docs.append(doc_path.read_text(encoding="utf-8").lower())

    combined_text = "\n".join(combined_docs)
    for required_term in REQUIRED_SAFE_LANGUAGE:
        assert required_term in combined_text

    claim_scan_text = combined_text
    for allowed_phrase in ALLOWED_NEGATED_SAFETY_PHRASES:
        claim_scan_text = claim_scan_text.replace(allowed_phrase, "")

    for prohibited_claim in PROHIBITED_MISLEADING_CLAIMS:
        assert prohibited_claim not in claim_scan_text
