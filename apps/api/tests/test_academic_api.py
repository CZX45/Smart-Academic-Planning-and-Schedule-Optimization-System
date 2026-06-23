from collections.abc import Generator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.seed_dev import seed_mock_data, seed_uuid

MISSING_ID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    with testing_session() as seed_session:
        seed_mock_data(seed_session)

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_read_only_academic_api_returns_mock_catalog_and_student(client: TestClient) -> None:
    institutions_response = client.get("/api/v1/institutions")
    assert institutions_response.status_code == 200
    institutions = institutions_response.json()
    assert institutions[0]["code"] == "MOCKU"
    assert institutions[0]["source"]["source_type"] == "MOCK"
    assert institutions[0]["source"]["is_official"] is False

    programs_response = client.get("/api/v1/programs")
    assert programs_response.status_code == 200
    programs = programs_response.json()
    assert programs[0]["program_code"] == "BSFIN"
    program_version_id = programs[0]["program_version_id"]
    UUID(program_version_id)

    program_response = client.get(f"/api/v1/programs/{program_version_id}")
    assert program_response.status_code == 200
    program_payload = program_response.json()
    assert program_payload["catalog_year"] == "2024"
    assert program_payload["program"]["code"] == "BSFIN"
    assert "degree_audit" not in program_payload

    requirements_response = client.get(f"/api/v1/programs/{program_version_id}/requirements")
    assert requirements_response.status_code == 200
    requirements_payload = requirements_response.json()
    assert requirements_payload["program_version_id"] == program_version_id
    names = {node["name"] for node in requirements_payload["nodes"]}
    assert "Choose 2 from 3 Finance Electives" in names
    elective_node = next(
        node
        for node in requirements_payload["nodes"]
        if node["name"] == "Choose 2 from 3 Finance Electives"
    )
    assert elective_node["choose_n"] == 2
    assert len(elective_node["course_options"]) == 3

    courses_response = client.get("/api/v1/courses")
    assert courses_response.status_code == 200
    courses = courses_response.json()
    assert any(course["subject_code"] == "FIN" for course in courses)
    course_id = courses[0]["id"]

    course_response = client.get(f"/api/v1/courses/{course_id}")
    assert course_response.status_code == 200
    assert course_response.json()["id"] == course_id

    student_id = str(seed_uuid("student-profile:mock-student"))

    student_response = client.get(f"/api/v1/students/{student_id}")
    assert student_response.status_code == 200
    student_payload = student_response.json()
    assert student_payload["display_name"] == "Mock Student"
    assert student_payload["programs"][0]["program_type"] == "PRIMARY_MAJOR"

    attempts_response = client.get(f"/api/v1/students/{student_id}/course-attempts")
    assert attempts_response.status_code == 200
    attempts = attempts_response.json()
    assert len(attempts) >= 2
    assert any(attempt["is_repeat"] for attempt in attempts)


def test_phase_2b_section_rule_and_offering_api(client: TestClient) -> None:
    fall_term_id = str(seed_uuid("term:2024-fall"))
    spring_term_id = str(seed_uuid("term:2025-spring"))
    fin_300_id = str(seed_uuid("course:FIN-300"))
    fin_400_id = str(seed_uuid("course:FIN-400"))
    fin_300_section_id = str(seed_uuid("section:2024-fall-fin-300-001"))
    fin_400_section_id = str(seed_uuid("section:2025-spring-fin-400-hyb"))

    fall_sections_response = client.get(
        f"/api/v1/terms/{fall_term_id}/sections",
        params={"status": "OPEN"},
    )
    assert fall_sections_response.status_code == 200
    fall_sections = fall_sections_response.json()
    assert any(section["id"] == fin_300_section_id for section in fall_sections)
    assert all(section["term_id"] == fall_term_id for section in fall_sections)
    assert all(section["source"]["source_type"] == "MOCK" for section in fall_sections)

    online_sections_response = client.get(
        f"/api/v1/terms/{fall_term_id}/sections",
        params={"modality": "ONLINE_ASYNCHRONOUS"},
    )
    assert online_sections_response.status_code == 200
    assert all(
        section["modality"] == "ONLINE_ASYNCHRONOUS" for section in online_sections_response.json()
    )

    course_sections_response = client.get(
        f"/api/v1/courses/{fin_400_id}/sections",
        params={"term_id": spring_term_id, "modality": "HYBRID"},
    )
    assert course_sections_response.status_code == 200
    course_sections = course_sections_response.json()
    assert [section["id"] for section in course_sections] == [fin_400_section_id]

    section_response = client.get(f"/api/v1/sections/{fin_300_section_id}")
    assert section_response.status_code == 200
    section_payload = section_response.json()
    assert section_payload["course_id"] == fin_300_id
    assert section_payload["section_code"] == "001"
    assert "eligible" not in section_payload

    meetings_response = client.get(f"/api/v1/sections/{fin_300_section_id}/meetings")
    assert meetings_response.status_code == 200
    meetings = meetings_response.json()
    assert [meeting["meeting_type"] for meeting in meetings] == ["LECTURE", "LAB"]

    course_rules_response = client.get(f"/api/v1/courses/{fin_300_id}/rules")
    assert course_rules_response.status_code == 200
    course_rules = course_rules_response.json()
    prerequisite = next(rule for rule in course_rules if rule["rule_type"] == "PREREQUISITE")
    assert prerequisite["source"]["is_official"] is False
    assert "eligibility" not in prerequisite

    rule_response = client.get(f"/api/v1/rules/{prerequisite['id']}")
    assert rule_response.status_code == 200
    assert rule_response.json()["id"] == prerequisite["id"]

    expression_response = client.get(f"/api/v1/rules/{prerequisite['id']}/expression")
    assert expression_response.status_code == 200
    expression = expression_response.json()
    assert expression["root"]["node_type"] == "AND"
    assert [child["node_type"] for child in expression["root"]["children"]] == [
        "COMPLETED_COURSE",
        "MINIMUM_GRADE",
    ]

    section_rules_response = client.get(f"/api/v1/sections/{fin_400_section_id}/rules")
    assert section_rules_response.status_code == 200
    assert any(rule["rule_type"] == "PERMISSION" for rule in section_rules_response.json())

    patterns_response = client.get(f"/api/v1/courses/{fin_300_id}/offering-patterns")
    assert patterns_response.status_code == 200
    patterns = patterns_response.json()
    assert patterns[0]["term_type"] in {"FALL", "SPRING"}
    assert patterns[0]["source"]["source_type"] == "MOCK"


def test_read_only_academic_api_returns_consistent_404(client: TestClient) -> None:
    for path in [
        f"/api/v1/programs/{MISSING_ID}",
        f"/api/v1/programs/{MISSING_ID}/requirements",
        f"/api/v1/courses/{MISSING_ID}",
        f"/api/v1/students/{MISSING_ID}",
        f"/api/v1/students/{MISSING_ID}/course-attempts",
        f"/api/v1/terms/{MISSING_ID}/sections",
        f"/api/v1/courses/{MISSING_ID}/sections",
        f"/api/v1/sections/{MISSING_ID}",
        f"/api/v1/sections/{MISSING_ID}/meetings",
        f"/api/v1/courses/{MISSING_ID}/rules",
        f"/api/v1/sections/{MISSING_ID}/rules",
        f"/api/v1/rules/{MISSING_ID}",
        f"/api/v1/rules/{MISSING_ID}/expression",
        f"/api/v1/courses/{MISSING_ID}/offering-patterns",
    ]:
        response = client.get(path)
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "not_found"


def test_phase_2b_section_filter_validation_error(client: TestClient) -> None:
    fall_term_id = str(seed_uuid("term:2024-fall"))

    response = client.get(
        f"/api/v1/terms/{fall_term_id}/sections",
        params={"status": "NOT_A_STATUS"},
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_degree_audit_api_creates_snapshot_and_returns_requirements(
    client: TestClient,
) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))
    program_version_id = str(seed_uuid("program-version:bs-finance-2024"))

    create_response = client.post(
        "/api/v1/degree-audits",
        json={
            "student_profile_id": student_id,
            "program_version_id": program_version_id,
            "calculation_mode": "PROJECTED",
        },
    )

    assert create_response.status_code == 201
    audit = create_response.json()
    audit_id = audit["id"]
    UUID(audit_id)
    assert audit["student_profile_id"] == student_id
    assert audit["program_version_id"] == program_version_id
    assert audit["calculation_mode"] == "PROJECTED"
    assert audit["status"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
    assert audit["engine_version"] == "phase-3a-degree-audit-v1"
    assert audit["completed_credits"] != "0.0"
    assert audit["remaining_credits"] >= "0.0"
    assert "eligibility" not in audit

    get_response = client.get(f"/api/v1/degree-audits/{audit_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == audit_id

    requirements_response = client.get(f"/api/v1/degree-audits/{audit_id}/requirements")
    assert requirements_response.status_code == 200
    requirements = requirements_response.json()
    assert len(requirements) >= 10
    business_a = next(item for item in requirements if item["requirement_code"] == "BUS-REQ-A")
    assert business_a["status"] == "SATISFIED"
    assert business_a["applications"][0]["application_type"] == "COURSE_ATTEMPT"
    assert business_a["applications"][0]["course_code"] == "BUS 101"

    transfer_requirement = next(
        item for item in requirements if item["requirement_code"] == "GEN-REQ"
    )
    assert transfer_requirement["status"] == "SATISFIED"
    assert transfer_requirement["applications"][0]["application_type"] == "TRANSFER_CREDIT"

    warnings_response = client.get(f"/api/v1/degree-audits/{audit_id}/warnings")
    assert warnings_response.status_code == 200
    warnings = warnings_response.json()
    assert any(warning["warning_code"] == "PENDING_TRANSFER" for warning in warnings)
    assert any(warning["requires_advisor_confirmation"] for warning in warnings)

    list_response = client.get(f"/api/v1/students/{student_id}/degree-audits")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [audit_id]

    latest_response = client.get(f"/api/v1/students/{student_id}/degree-audits/latest")
    assert latest_response.status_code == 200
    assert latest_response.json()["id"] == audit_id


def test_degree_audit_api_validates_scope_and_mode(client: TestClient) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))
    program_version_id = str(seed_uuid("program-version:bs-finance-2024"))

    invalid_mode = client.post(
        "/api/v1/degree-audits",
        json={
            "student_profile_id": student_id,
            "program_version_id": program_version_id,
            "calculation_mode": "ELIGIBILITY",
        },
    )
    assert invalid_mode.status_code == 422

    missing_student = client.post(
        "/api/v1/degree-audits",
        json={
            "student_profile_id": MISSING_ID,
            "program_version_id": program_version_id,
            "calculation_mode": "CURRENT",
        },
    )
    assert missing_student.status_code == 404
    assert missing_student.json()["detail"]["code"] == "not_found"

    missing_latest = client.get(f"/api/v1/students/{MISSING_ID}/degree-audits/latest")
    assert missing_latest.status_code == 404
