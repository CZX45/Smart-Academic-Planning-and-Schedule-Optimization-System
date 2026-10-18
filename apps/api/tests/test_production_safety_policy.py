from pathlib import Path

from app.main import app

PROHIBITED_ENDPOINT_TERMS = [
    "auto-register",
    "auto_register",
    "register-course",
    "register_course",
    "drop-course",
    "drop_course",
    "swap-course",
    "swap_course",
    "join-waitlist",
    "join_waitlist",
    "reserve-seat",
    "reserve_seat",
    "seat-grab",
    "seat_grab",
    "poll-portal",
    "poll_portal",
]

REPO_ROOT = Path(__file__).resolve().parents[3]
PHASE_10A_REQUIRED_DOCS = [
    "docs/RELEASE_READINESS_QA.md",
    "docs/DEMO_SCENARIOS.md",
    "docs/RELEASE_CHECKLIST.md",
]
PHASE_10A_REQUIRED_SAFE_TERMS = [
    "manual review required",
    "verify in the official portal",
    "read-only imported data",
    "non-official",
]
PHASE_10A_PROHIBITED_DEMO_CLAIMS = [
    "real-time availability",
    "guaranteed seat",
    "auto-register",
    "reserve seat",
    "live seat monitor",
    "automatic waitlist join",
]


def test_openapi_paths_do_not_expose_prohibited_registration_or_polling_actions() -> None:
    for path, path_item in app.openapi()["paths"].items():
        normalized_path = path.lower()
        assert all(term not in normalized_path for term in PROHIBITED_ENDPOINT_TERMS)
        for method, operation in path_item.items():
            if method.lower() not in {"get", "post", "patch", "put", "delete"}:
                continue
            operation_id = str(operation.get("operationId", "")).lower()
            summary = str(operation.get("summary", "")).lower()
            assert all(term not in operation_id for term in PROHIBITED_ENDPOINT_TERMS)
            assert all(term not in summary for term in PROHIBITED_ENDPOINT_TERMS)


def test_phase_10a_release_docs_keep_demo_and_qa_language_advisory() -> None:
    combined_docs = []
    for relative_path in PHASE_10A_REQUIRED_DOCS:
        doc_path = REPO_ROOT / relative_path
        assert doc_path.exists(), f"{relative_path} must exist for release QA"
        combined_docs.append(doc_path.read_text(encoding="utf-8").lower())

    combined_text = "\n".join(combined_docs)
    for required_term in PHASE_10A_REQUIRED_SAFE_TERMS:
        assert required_term in combined_text

    for prohibited_claim in PHASE_10A_PROHIBITED_DEMO_CLAIMS:
        assert prohibited_claim not in combined_text
