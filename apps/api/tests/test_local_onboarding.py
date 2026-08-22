from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.academic import (
    Institution,
    SourceType,
    StudentAcademicProgram,
    StudentProfile,
)
from app.seed_dev import seed_mock_data


@dataclass(frozen=True)
class OnboardingHarness:
    client: TestClient
    session_factory: sessionmaker[Session]


@pytest.fixture()
def harness(monkeypatch: pytest.MonkeyPatch) -> Generator[OnboardingHarness, None, None]:
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

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session() as db:
            yield db

    monkeypatch.setattr(settings, "product_mode", "LOCAL_DESKTOP")
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield OnboardingHarness(TestClient(app), testing_session)
    finally:
        app.dependency_overrides.clear()


def onboarding_payload() -> dict[str, object]:
    return {
        "acknowledge_non_official": True,
        "display_name": "Local learner",
        "institution_code": "LOCAL-U",
        "institution_name": "Student-provided university",
        "campus_code": "MAIN",
        "campus_name": "Main campus",
        "country": "US",
        "timezone": "America/New_York",
    }


def test_local_onboarding_creates_only_unverified_student_provided_records(
    harness: OnboardingHarness,
) -> None:
    response = harness.client.post(
        "/api/v1/local-onboarding/student-profiles",
        json=onboarding_payload(),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["reason_codes"] == ["STUDENT_PROVIDED_PROFILE_CREATED"]
    assert any("advisor" in warning.lower() for warning in payload["warnings"])
    assert payload["assumptions"] == [
        "Institution and campus details were entered by the local user and were not verified."
    ]
    assert payload["source_references"] == ["Local onboarding form"]

    institution = payload["institution"]
    campus = payload["campus"]
    student = payload["student"]
    assert institution["code"] == "LOCAL-U"
    assert campus["code"] == "MAIN"
    assert campus["institution_id"] == institution["id"]
    assert student["home_institution_id"] == institution["id"]
    assert student["home_campus_id"] == campus["id"]
    assert student["display_name"] == "Local learner"
    assert student["external_ref"] is None
    assert student["programs"] == []

    for record in (institution, campus, student):
        assert record["source"]["source_type"] == "STUDENT_PROVIDED"
        assert record["source"]["is_official"] is False
        assert record["source"]["source_confidence"] == "student-provided-unverified"
        assert record["source"]["source_reference"] == "Local onboarding form"
        assert record["source"]["source_retrieved_at"] is not None

    with harness.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(StudentProfile)) == 1
        assert session.scalar(select(func.count()).select_from(StudentAcademicProgram)) == 0

    listed = harness.client.get("/api/v1/local-onboarding/student-profiles")
    assert listed.status_code == 200
    assert [item["student"]["id"] for item in listed.json()] == [student["id"]]


def test_local_onboarding_refuses_to_create_a_second_student_profile(
    harness: OnboardingHarness,
) -> None:
    first = harness.client.post(
        "/api/v1/local-onboarding/student-profiles",
        json=onboarding_payload(),
    )
    assert first.status_code == 201

    duplicate = harness.client.post(
        "/api/v1/local-onboarding/student-profiles",
        json=onboarding_payload(),
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "student_profile_already_exists"
    with harness.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(StudentProfile)) == 1


def test_local_onboarding_never_overwrites_an_existing_institution(
    harness: OnboardingHarness,
) -> None:
    with harness.session_factory() as session:
        session.add(
            Institution(
                code="LOCAL-U",
                name="Reviewed institution",
                country="US",
                timezone="America/Chicago",
                source_type=SourceType.OFFICIAL,
                is_official=True,
                source_reference="Reviewed catalog",
                source_confidence="reviewed",
            )
        )
        session.commit()

    response = harness.client.post(
        "/api/v1/local-onboarding/student-profiles",
        json=onboarding_payload(),
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "institution_code_conflict"
    with harness.session_factory() as session:
        institution = session.scalar(select(Institution).where(Institution.code == "LOCAL-U"))
        assert institution is not None
        assert institution.name == "Reviewed institution"
        assert institution.is_official is True
        assert institution.source_type is SourceType.OFFICIAL
        assert session.scalar(select(func.count()).select_from(StudentProfile)) == 0


def test_local_onboarding_requires_explicit_non_official_acknowledgement(
    harness: OnboardingHarness,
) -> None:
    payload = onboarding_payload()
    payload["acknowledge_non_official"] = False

    response = harness.client.post(
        "/api/v1/local-onboarding/student-profiles",
        json=payload,
    )

    assert response.status_code == 422


def test_mock_seed_does_not_activate_or_block_the_first_local_profile(
    harness: OnboardingHarness,
) -> None:
    with harness.session_factory() as session:
        seed_mock_data(session)

    response = harness.client.get("/api/v1/local-onboarding/student-profiles")

    assert response.status_code == 200
    assert response.json() == []

    created = harness.client.post(
        "/api/v1/local-onboarding/student-profiles",
        json=onboarding_payload(),
    )

    assert created.status_code == 201
    with harness.session_factory() as session:
        local_student_count = session.scalar(
            select(func.count())
            .select_from(StudentProfile)
            .where(StudentProfile.source_type != SourceType.MOCK)
        )
        assert local_student_count == 1


def test_local_onboarding_is_unavailable_in_server_mode(
    harness: OnboardingHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "product_mode", "SERVER")

    response = harness.client.post(
        "/api/v1/local-onboarding/student-profiles",
        json=onboarding_payload(),
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "local_onboarding_unavailable"
