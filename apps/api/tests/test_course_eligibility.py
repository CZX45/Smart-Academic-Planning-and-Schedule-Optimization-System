from collections.abc import Generator
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.academic import (
    CourseRuleExpressionNodeType,
    EligibilityCheckRun,
    EligibilityMode,
    EligibilityOverallResult,
    EligibilityRuleResult,
    RuleEvaluation,
    StudentCourseAttempt,
    StudentCourseAttemptStatus,
)
from app.seed_dev import mock_source, seed_mock_data, seed_uuid
from app.services.course_eligibility.engine import CourseEligibilityEngine


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    with testing_session() as db:
        seed_mock_data(db)
        yield db


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


def test_eligibility_database_constraints(session: Session) -> None:
    student_id = seed_uuid("student-profile:mock-student")
    course_id = seed_uuid("course:FIN-300")
    term_id = seed_uuid("term:2024-fall")
    run = EligibilityCheckRun(
        id=seed_uuid("eligibility-check:test"),
        institution_id=seed_uuid("institution:mock-university"),
        student_profile_id=student_id,
        course_id=course_id,
        section_id=None,
        target_term_id=term_id,
        mode=EligibilityMode.CURRENT,
        status="COMPLETED",
        engine_version="phase-4-course-eligibility-v1",
        overall_result=EligibilityOverallResult.ELIGIBLE,
        academic_eligibility_result=EligibilityOverallResult.ELIGIBLE,
        source_snapshot_hash="hash",
    )
    session.add(run)
    session.flush()
    rule = RuleEvaluation(
        id=seed_uuid("rule-evaluation:test"),
        eligibility_check_run_id=run.id,
        course_rule_id=seed_uuid("course-rule:fin-300-prerequisite"),
        result=EligibilityRuleResult.SATISFIED,
        rule_type="PREREQUISITE",
        explanation="Satisfied by completed mock prerequisite.",
        display_order=0,
    )
    session.add(rule)
    session.commit()

    duplicate = RuleEvaluation(
        id=seed_uuid("rule-evaluation:duplicate"),
        eligibility_check_run_id=run.id,
        course_rule_id=seed_uuid("course-rule:fin-300-prerequisite"),
        result=EligibilityRuleResult.SATISFIED,
        rule_type="PREREQUISITE",
        explanation="Duplicate.",
        display_order=1,
    )
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        session.commit()


def test_unknown_eligibility_results_persist_in_local_sqlite(session: Session) -> None:
    run = EligibilityCheckRun(
        id=seed_uuid("eligibility-check:unknown"),
        institution_id=seed_uuid("institution:mock-university"),
        student_profile_id=seed_uuid("student-profile:mock-student"),
        course_id=seed_uuid("course:FIN-300"),
        section_id=None,
        target_term_id=seed_uuid("term:2024-fall"),
        mode=EligibilityMode.CURRENT,
        status="COMPLETED_WITH_WARNINGS",
        engine_version="phase-4-course-eligibility-v1",
        overall_result=EligibilityOverallResult.UNKNOWN,
        academic_eligibility_result=EligibilityOverallResult.UNKNOWN,
        source_snapshot_hash="unknown-proof",
    )
    session.add(run)
    session.commit()

    stored = session.get(EligibilityCheckRun, run.id)
    assert stored is not None
    assert stored.overall_result is EligibilityOverallResult.UNKNOWN
    assert stored.academic_eligibility_result is EligibilityOverallResult.UNKNOWN


def test_engine_evaluates_completed_prerequisite_and_minimum_grade(session: Session) -> None:
    result = CourseEligibilityEngine(session).evaluate(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        course_id=seed_uuid("course:FIN-300"),
        section_id=None,
        target_term_id=seed_uuid("term:2024-fall"),
        mode=EligibilityMode.CURRENT,
    )

    assert result.overall_result is EligibilityOverallResult.ELIGIBLE
    assert result.rule_evaluations
    assert all(rule.result is EligibilityRuleResult.SATISFIED for rule in result.rule_evaluations)
    assert (
        any(
            expression.node_type is CourseRuleExpressionNodeType.MINIMUM_GRADE
            and expression.result is EligibilityRuleResult.SATISFIED
            and expression.matched_attempt_id
            == seed_uuid("attempt:mock-student-fin-200-incomplete")
            for expression in result.expression_evaluations
        )
        is False
    )


def test_engine_reports_not_eligible_for_missing_prerequisite(session: Session) -> None:
    result = CourseEligibilityEngine(session).evaluate(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        course_id=seed_uuid("course:FIN-450"),
        section_id=None,
        target_term_id=seed_uuid("term:2025-spring"),
        mode=EligibilityMode.CURRENT,
    )

    assert result.overall_result is EligibilityOverallResult.NOT_ELIGIBLE
    assert any(
        reason.reason_code == "COMPLETED_COURSE_MISSING" for reason in result.blocking_reasons
    )
    assert any(
        expression.result is EligibilityRuleResult.NOT_SATISFIED
        for expression in result.expression_evaluations
    )


def test_projected_and_registration_modes_keep_in_progress_conditional(
    session: Session,
) -> None:
    projected = CourseEligibilityEngine(session).evaluate(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        course_id=seed_uuid("course:FIN-350"),
        section_id=None,
        target_term_id=seed_uuid("term:2025-spring"),
        mode=EligibilityMode.PROJECTED,
    )
    registration = CourseEligibilityEngine(session).evaluate(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        course_id=seed_uuid("course:FIN-350"),
        section_id=None,
        target_term_id=seed_uuid("term:2025-spring"),
        mode=EligibilityMode.REGISTRATION,
    )

    assert projected.overall_result is EligibilityOverallResult.CONDITIONALLY_ELIGIBLE
    assert registration.overall_result is EligibilityOverallResult.CONDITIONALLY_ELIGIBLE
    assert any(
        "in progress" in reason.explanation.lower() for reason in projected.conditional_reasons
    )


def test_corequisite_explicit_concurrent_plan_is_conditional(session: Session) -> None:
    result = CourseEligibilityEngine(session).evaluate(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        course_id=seed_uuid("course:FIN-410"),
        section_id=None,
        target_term_id=seed_uuid("term:2025-spring"),
        mode=EligibilityMode.REGISTRATION,
        planned_corequisite_course_ids=[seed_uuid("course:FIN-411")],
    )

    assert result.overall_result is EligibilityOverallResult.CONDITIONALLY_ELIGIBLE
    assert result.corequisite_summary is not None
    assert seed_uuid("course:FIN-411") in result.corequisite_summary.must_enroll_concurrently


def test_completed_corequisite_is_reported_in_summary(session: Session) -> None:
    session.add(
        StudentCourseAttempt(
            id=seed_uuid("attempt:mock-student-fin-401l-completed"),
            student_profile_id=seed_uuid("student-profile:mock-student"),
            course_id=seed_uuid("course:FIN-401L"),
            term_id=seed_uuid("term:2024-fall"),
            attempt_number=1,
            status=StudentCourseAttemptStatus.COMPLETED,
            grade="B",
            credits_attempted=Decimal("1.0"),
            credits_earned=Decimal("1.0"),
            is_repeat=False,
            **mock_source(),
        )
    )
    session.flush()

    result = CourseEligibilityEngine(session).evaluate(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        course_id=seed_uuid("course:FIN-400"),
        section_id=None,
        target_term_id=seed_uuid("term:2025-spring"),
        mode=EligibilityMode.REGISTRATION,
    )

    assert result.corequisite_summary is not None
    assert seed_uuid("course:FIN-401L") in result.corequisite_summary.required_corequisite_courses
    assert seed_uuid("course:FIN-401L") in result.corequisite_summary.already_completed


def test_in_progress_corequisite_is_reported_in_summary(session: Session) -> None:
    session.add(
        StudentCourseAttempt(
            id=seed_uuid("attempt:mock-student-fin-401l-in-progress"),
            student_profile_id=seed_uuid("student-profile:mock-student"),
            course_id=seed_uuid("course:FIN-401L"),
            term_id=seed_uuid("term:2025-spring"),
            attempt_number=1,
            status=StudentCourseAttemptStatus.IN_PROGRESS,
            grade=None,
            credits_attempted=Decimal("1.0"),
            credits_earned=Decimal("0.0"),
            is_repeat=False,
            **mock_source(),
        )
    )
    session.flush()

    result = CourseEligibilityEngine(session).evaluate(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        course_id=seed_uuid("course:FIN-400"),
        section_id=None,
        target_term_id=seed_uuid("term:2025-spring"),
        mode=EligibilityMode.REGISTRATION,
    )

    assert result.corequisite_summary is not None
    assert seed_uuid("course:FIN-401L") in result.corequisite_summary.required_corequisite_courses
    assert seed_uuid("course:FIN-401L") in result.corequisite_summary.currently_in_progress


def test_section_rules_are_combined_with_course_rules_and_seats_are_separate(
    session: Session,
) -> None:
    result = CourseEligibilityEngine(session).evaluate(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        course_id=seed_uuid("course:FIN-400"),
        section_id=seed_uuid("section:2025-spring-fin-400-hyb"),
        target_term_id=seed_uuid("term:2025-spring"),
        mode=EligibilityMode.REGISTRATION,
    )

    assert result.overall_result is EligibilityOverallResult.PERMISSION_REQUIRED
    assert result.registration_availability is not None
    assert result.registration_availability.section_status == "WAITLIST"
    assert result.registration_availability.available_seats == 0
    assert result.academic_eligibility_result is EligibilityOverallResult.PERMISSION_REQUIRED


def test_api_creates_retrieves_lists_and_batches_eligibility_checks(
    client: TestClient,
) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))
    response = client.post(
        "/api/v1/eligibility-checks",
        json={
            "student_profile_id": student_id,
            "course_id": str(seed_uuid("course:FIN-300")),
            "target_term_id": str(seed_uuid("term:2024-fall")),
            "mode": "CURRENT",
            "planned_corequisite_course_ids": [],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    check_id = payload["id"]
    UUID(check_id)
    assert payload["overall_result"] == "ELIGIBLE"
    assert payload["academic_eligibility_result"] == "ELIGIBLE"
    assert payload["blocking_reasons"] == []
    assert "schedule" not in payload

    detail = client.get(f"/api/v1/eligibility-checks/{check_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == check_id

    rules = client.get(f"/api/v1/eligibility-checks/{check_id}/rules")
    assert rules.status_code == 200
    assert rules.json()[0]["expressions"]

    warnings = client.get(f"/api/v1/eligibility-checks/{check_id}/warnings")
    assert warnings.status_code == 200

    student_checks = client.get(f"/api/v1/students/{student_id}/eligibility-checks")
    assert student_checks.status_code == 200
    assert any(item["id"] == check_id for item in student_checks.json())

    batch = client.post(
        "/api/v1/eligibility-checks/batch",
        json={
            "checks": [
                {
                    "student_profile_id": student_id,
                    "course_id": str(seed_uuid("course:FIN-300")),
                    "target_term_id": str(seed_uuid("term:2024-fall")),
                    "mode": "CURRENT",
                },
                {
                    "student_profile_id": student_id,
                    "course_id": str(seed_uuid("course:FIN-450")),
                    "target_term_id": str(seed_uuid("term:2025-spring")),
                    "mode": "CURRENT",
                },
            ]
        },
    )
    assert batch.status_code == 201
    assert [item["overall_result"] for item in batch.json()["results"]] == [
        "ELIGIBLE",
        "NOT_ELIGIBLE",
    ]


def test_api_rejects_invalid_section_course_pair_and_batch_limit(client: TestClient) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))
    mismatch = client.post(
        "/api/v1/eligibility-checks",
        json={
            "student_profile_id": student_id,
            "course_id": str(seed_uuid("course:FIN-300")),
            "section_id": str(seed_uuid("section:2025-spring-fin-400-hyb")),
            "target_term_id": str(seed_uuid("term:2025-spring")),
            "mode": "CURRENT",
        },
    )
    assert mismatch.status_code == 400
    assert mismatch.json()["detail"]["code"] == "section_course_mismatch"

    too_many = client.post(
        "/api/v1/eligibility-checks/batch",
        json={
            "checks": [
                {
                    "student_profile_id": student_id,
                    "course_id": str(seed_uuid("course:FIN-300")),
                    "target_term_id": str(seed_uuid("term:2024-fall")),
                    "mode": "CURRENT",
                }
                for _ in range(51)
            ]
        },
    )
    assert too_many.status_code == 422


def test_no_restrictions_course_is_eligible_with_notice(session: Session) -> None:
    result = CourseEligibilityEngine(session).evaluate(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        course_id=seed_uuid("course:FREE-100"),
        section_id=None,
        target_term_id=seed_uuid("term:2024-fall"),
        mode=EligibilityMode.CURRENT,
    )

    assert result.overall_result is EligibilityOverallResult.ELIGIBLE
    assert any(warning.warning_code == "NO_STORED_RESTRICTIONS" for warning in result.warnings)


def test_closed_section_keeps_academic_eligibility_separate(session: Session) -> None:
    result = CourseEligibilityEngine(session).evaluate(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        course_id=seed_uuid("course:FREE-100"),
        section_id=seed_uuid("section:2024-fall-free-100-closed"),
        target_term_id=seed_uuid("term:2024-fall"),
        mode=EligibilityMode.REGISTRATION,
    )

    assert result.academic_eligibility_result is EligibilityOverallResult.ELIGIBLE
    assert result.overall_result is EligibilityOverallResult.ELIGIBLE
    assert result.registration_availability is not None
    assert result.registration_availability.section_status == "CLOSED"
    assert result.registration_availability.available_seats == 0
