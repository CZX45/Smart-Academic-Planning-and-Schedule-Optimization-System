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


def test_read_only_academic_api_returns_consistent_404(client: TestClient) -> None:
    for path in [
        f"/api/v1/programs/{MISSING_ID}",
        f"/api/v1/programs/{MISSING_ID}/requirements",
        f"/api/v1/courses/{MISSING_ID}",
        f"/api/v1/students/{MISSING_ID}",
        f"/api/v1/students/{MISSING_ID}/course-attempts",
    ]:
        response = client.get(path)
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "not_found"
