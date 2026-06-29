from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.academic import (
    AcademicPlanCourse,
    AcademicPlanCourseSource,
    AcademicPlanCourseStatus,
    AcademicPlanCoverageType,
    AcademicPlanningMode,
    AcademicPlanRequirementCoverage,
    AcademicPlanRun,
    AcademicPlanRunStatus,
    AcademicPlanTerm,
    AcademicPlanTermStatus,
    AcademicPlanWarning,
    AuditWarningSeverity,
    Course,
    RequirementCourseOption,
    RequirementNode,
    RequirementType,
    StudentAcademicProgram,
)
from app.seed_dev import mock_source, seed_mock_data, seed_uuid
from app.services.academic_planner.engine import AcademicPlannerApplicationService

MISSING_ID = "00000000-0000-0000-0000-000000000000"


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


def create_fin_450_requirement(session: Session) -> None:
    finance_major = session.scalar(
        select(RequirementNode).where(RequirementNode.code == "FINANCE-MAJOR")
    )
    assert finance_major is not None
    course_record = session.scalar(
        select(Course).where(Course.subject_code == "FIN", Course.course_number == "450")
    )
    assert course_record is not None
    node = RequirementNode(
        id=seed_uuid("requirement-node:PHASE5A-FIN450"),
        institution_id=seed_uuid("institution:mock-university"),
        program_version_id=seed_uuid("program-version:bs-finance-2024"),
        parent_id=finance_major.id,
        code="PHASE5A-FIN450",
        name="Phase 5A Missing Prerequisite Demonstration",
        requirement_type=RequirementType.REQUIRED_COURSE,
        display_order=5,
        minimum_grade="C",
        **mock_source(),
    )
    option = RequirementCourseOption(
        id=seed_uuid("requirement-option:PHASE5A-FIN450"),
        institution_id=node.institution_id,
        program_version_id=node.program_version_id,
        requirement_node_id=node.id,
        course_id=course_record.id,
        display_order=10,
        minimum_grade="C",
        **mock_source(),
    )
    session.add(node)
    session.flush()
    session.add(option)
    session.commit()


def test_planner_database_constraints_and_snapshot_tables(session: Session) -> None:
    fin_403 = session.scalar(
        select(Course).where(Course.subject_code == "FIN", Course.course_number == "403")
    )
    fin_electives = session.scalar(
        select(RequirementNode).where(RequirementNode.code == "FIN-ELECTIVES")
    )
    assert fin_403 is not None
    assert fin_electives is not None
    run = AcademicPlanRun(
        id=seed_uuid("academic-plan-run:test"),
        student_profile_id=seed_uuid("student-profile:mock-student"),
        program_version_id=seed_uuid("program-version:bs-finance-2024"),
        academic_plan_scenario_id=None,
        planning_mode=AcademicPlanningMode.CURRENT_PROGRAM,
        status=AcademicPlanRunStatus.COMPLETED_WITH_WARNINGS,
        engine_version="phase-5a-academic-planner-v1",
        start_term_id=seed_uuid("term:2024-fall"),
        target_completion_term_id=seed_uuid("term:2025-spring"),
        minimum_credits_per_term=Decimal("3.0"),
        maximum_credits_per_term=Decimal("6.0"),
        preferred_credits_per_term=Decimal("6.0"),
    )
    term = AcademicPlanTerm(
        id=seed_uuid("academic-plan-term:test"),
        academic_plan_run_id=run.id,
        term_id=seed_uuid("term:2024-fall"),
        sequence_index=0,
        planned_credits=Decimal("3.0"),
        status=AcademicPlanTermStatus.PLANNED,
        explanation="Mock term planning snapshot.",
    )
    course = AcademicPlanCourse(
        id=seed_uuid("academic-plan-course:test"),
        academic_plan_term_id=term.id,
        course_id=fin_403.id,
        requirement_node_id=fin_electives.id,
        source=AcademicPlanCourseSource.DEGREE_AUDIT_REMAINING,
        priority_rank=0,
        credits=Decimal("3.0"),
        eligibility_result="ELIGIBLE",
        planning_status=AcademicPlanCourseStatus.PLANNED,
        reason_code="REQUIREMENT_REMAINING",
        explanation="Mock course placed for a remaining requirement.",
    )
    coverage = AcademicPlanRequirementCoverage(
        id=seed_uuid("academic-plan-coverage:test"),
        academic_plan_run_id=run.id,
        academic_plan_course_id=course.id,
        requirement_node_id=fin_electives.id,
        coverage_type=AcademicPlanCoverageType.DIRECT_REQUIREMENT,
        credits=Decimal("3.0"),
    )
    warning = AcademicPlanWarning(
        id=seed_uuid("academic-plan-warning:test"),
        academic_plan_run_id=run.id,
        academic_plan_term_id=term.id,
        academic_plan_course_id=course.id,
        warning_code="MOCK_PLAN_NOT_OFFICIAL",
        severity=AuditWarningSeverity.INFO,
        message="Mock plan is not official policy.",
        requires_advisor_confirmation=True,
    )
    session.add(run)
    session.flush()
    session.add(term)
    session.flush()
    session.add(course)
    session.flush()
    session.add_all([coverage, warning])
    session.commit()

    duplicate_course = AcademicPlanCourse(
        id=seed_uuid("academic-plan-course:duplicate"),
        academic_plan_term_id=term.id,
        course_id=course.course_id,
        requirement_node_id=course.requirement_node_id,
        source=AcademicPlanCourseSource.DEGREE_AUDIT_REMAINING,
        priority_rank=1,
        credits=Decimal("3.0"),
        eligibility_result="ELIGIBLE",
        planning_status=AcademicPlanCourseStatus.ALTERNATIVE,
        reason_code="DUPLICATE_TEST",
        explanation="Duplicate course in the same term should be rejected.",
    )
    session.add(duplicate_course)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    invalid_term = AcademicPlanTerm(
        id=seed_uuid("academic-plan-term:negative"),
        academic_plan_run_id=run.id,
        term_id=seed_uuid("term:2025-spring"),
        sequence_index=1,
        planned_credits=Decimal("-1.0"),
        status=AcademicPlanTermStatus.BLOCKED,
        explanation="Negative credits are invalid.",
    )
    session.add(invalid_term)
    with pytest.raises(IntegrityError):
        session.commit()


def test_planner_creates_terms_courses_coverage_and_warnings(session: Session) -> None:
    before_programs = session.scalars(select(StudentAcademicProgram)).all()
    run = AcademicPlannerApplicationService(session).create_plan(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        program_version_id=seed_uuid("program-version:bs-finance-2024"),
        academic_plan_scenario_id=None,
        planning_mode=AcademicPlanningMode.CURRENT_PROGRAM,
        start_term_id=seed_uuid("term:2024-fall"),
        terms_to_plan=2,
        minimum_credits_per_term=Decimal("3.0"),
        maximum_credits_per_term=Decimal("6.0"),
        preferred_credits_per_term=Decimal("6.0"),
    )

    terms = session.scalars(
        select(AcademicPlanTerm)
        .where(AcademicPlanTerm.academic_plan_run_id == run.id)
        .order_by(AcademicPlanTerm.sequence_index)
    ).all()
    courses = session.scalars(
        select(AcademicPlanCourse)
        .join(AcademicPlanTerm, AcademicPlanCourse.academic_plan_term_id == AcademicPlanTerm.id)
        .where(AcademicPlanTerm.academic_plan_run_id == run.id)
        .order_by(AcademicPlanTerm.sequence_index, AcademicPlanCourse.priority_rank)
    ).all()
    coverage = session.scalars(
        select(AcademicPlanRequirementCoverage).where(
            AcademicPlanRequirementCoverage.academic_plan_run_id == run.id
        )
    ).all()
    warnings = session.scalars(
        select(AcademicPlanWarning).where(AcademicPlanWarning.academic_plan_run_id == run.id)
    ).all()

    assert run.status in {
        AcademicPlanRunStatus.COMPLETED,
        AcademicPlanRunStatus.COMPLETED_WITH_WARNINGS,
    }
    assert [term.sequence_index for term in terms] == [0, 1]
    assert all(term.planned_credits <= Decimal("6.0") for term in terms)
    assert courses
    assert coverage
    assert any(warning.warning_code == "MOCK_PLAN_NOT_OFFICIAL" for warning in warnings)
    assert session.scalars(select(StudentAcademicProgram)).all() == before_programs


def test_planner_places_missing_prerequisite_before_dependent_course(session: Session) -> None:
    create_fin_450_requirement(session)

    run = AcademicPlannerApplicationService(session).create_plan(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        program_version_id=seed_uuid("program-version:bs-finance-2024"),
        academic_plan_scenario_id=None,
        planning_mode=AcademicPlanningMode.CURRENT_PROGRAM,
        start_term_id=seed_uuid("term:2024-fall"),
        terms_to_plan=2,
        minimum_credits_per_term=Decimal("0.0"),
        maximum_credits_per_term=Decimal("6.0"),
        preferred_credits_per_term=Decimal("6.0"),
    )

    rows = session.execute(
        select(AcademicPlanTerm, AcademicPlanCourse, Course)
        .join(AcademicPlanCourse, AcademicPlanCourse.academic_plan_term_id == AcademicPlanTerm.id)
        .join(Course, Course.id == AcademicPlanCourse.course_id)
        .where(AcademicPlanTerm.academic_plan_run_id == run.id)
    ).all()
    sequence_by_course = {
        f"{course.subject_code} {course.course_number}": term.sequence_index
        for term, _, course in rows
    }

    assert sequence_by_course["ACTL 300"] < sequence_by_course["FIN 450"]
    fin_450 = next(plan_course for _, plan_course, course in rows if course.course_number == "450")
    assert fin_450.planning_status is AcademicPlanCourseStatus.CONDITIONALLY_PLANNED
    assert fin_450.reason_code == "PREREQUISITE_PLANNED_EARLIER"


def test_planner_pairs_corequisite_in_same_term_when_credit_limit_allows(
    session: Session,
) -> None:
    run = AcademicPlannerApplicationService(session).create_plan(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        program_version_id=seed_uuid("program-version:bs-finance-2024"),
        academic_plan_scenario_id=None,
        planning_mode=AcademicPlanningMode.CURRENT_PROGRAM,
        start_term_id=seed_uuid("term:2024-fall"),
        terms_to_plan=2,
        minimum_credits_per_term=Decimal("0.0"),
        maximum_credits_per_term=Decimal("6.0"),
        preferred_credits_per_term=Decimal("6.0"),
    )

    rows = session.execute(
        select(AcademicPlanTerm, Course, AcademicPlanCourse)
        .join(AcademicPlanCourse, AcademicPlanCourse.academic_plan_term_id == AcademicPlanTerm.id)
        .join(Course, Course.id == AcademicPlanCourse.course_id)
        .where(AcademicPlanTerm.academic_plan_run_id == run.id)
    ).all()
    sequence_by_course = {
        f"{course.subject_code} {course.course_number}": term.sequence_index
        for term, course, _ in rows
    }

    assert sequence_by_course["FIN 400"] == sequence_by_course["FIN 401L"]
    corequisite = next(
        planned
        for _, course, planned in rows
        if f"{course.subject_code} {course.course_number}" == "FIN 401L"
    )
    assert corequisite.source is AcademicPlanCourseSource.COREQUISITE_PAIR


def test_planner_warns_for_unknown_offering_pattern_and_credit_shortfall(
    session: Session,
) -> None:
    run = AcademicPlannerApplicationService(session).create_plan(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        program_version_id=seed_uuid("program-version:bs-finance-2024"),
        academic_plan_scenario_id=None,
        planning_mode=AcademicPlanningMode.CURRENT_PROGRAM,
        start_term_id=seed_uuid("term:2024-fall"),
        terms_to_plan=1,
        minimum_credits_per_term=Decimal("9.0"),
        maximum_credits_per_term=Decimal("3.0"),
        preferred_credits_per_term=Decimal("3.0"),
    )

    warnings = session.scalars(
        select(AcademicPlanWarning).where(AcademicPlanWarning.academic_plan_run_id == run.id)
    ).all()

    assert run.status is AcademicPlanRunStatus.COMPLETED_WITH_WARNINGS
    assert any(warning.warning_code == "COURSE_OFFERING_PATTERN_UNKNOWN" for warning in warnings)
    assert any(warning.warning_code == "MINIMUM_CREDITS_NOT_MET" for warning in warnings)
    assert any(warning.warning_code == "PARTIAL_PLAN_HORIZON_INSUFFICIENT" for warning in warnings)


def test_planner_api_create_retrieve_list_compare_and_validate(
    client: TestClient,
) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))
    create_response = client.post(
        "/api/v1/academic-plans",
        json={
            "student_profile_id": student_id,
            "program_version_id": str(seed_uuid("program-version:bs-finance-2024")),
            "academic_plan_scenario_id": None,
            "planning_mode": "CURRENT_PROGRAM",
            "start_term_id": str(seed_uuid("term:2024-fall")),
            "terms_to_plan": 2,
            "minimum_credits_per_term": "3.0",
            "maximum_credits_per_term": "6.0",
            "preferred_credits_per_term": "6.0",
        },
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    plan_id = payload["id"]
    UUID(plan_id)
    assert payload["planning_mode"] == "CURRENT_PROGRAM"
    assert payload["terms"]
    assert payload["planned_courses"]
    assert payload["warnings"]
    assert "registered_courses" not in payload
    assert "weekly_schedule" not in payload

    assert client.get(f"/api/v1/academic-plans/{plan_id}").status_code == 200
    assert client.get(f"/api/v1/academic-plans/{plan_id}/terms").status_code == 200
    assert client.get(f"/api/v1/academic-plans/{plan_id}/courses").status_code == 200
    assert client.get(f"/api/v1/academic-plans/{plan_id}/warnings").status_code == 200
    student_plans = client.get(f"/api/v1/students/{student_id}/academic-plans")
    assert student_plans.status_code == 200
    assert any(plan["id"] == plan_id for plan in student_plans.json())

    compare_response = client.post(
        "/api/v1/academic-plans/compare",
        json={"academic_plan_ids": [plan_id, plan_id]},
    )
    assert compare_response.status_code == 200
    assert compare_response.json()[0]["academic_plan_run_id"] == plan_id

    invalid_limits = client.post(
        "/api/v1/academic-plans",
        json={
            "student_profile_id": student_id,
            "program_version_id": str(seed_uuid("program-version:bs-finance-2024")),
            "planning_mode": "CURRENT_PROGRAM",
            "start_term_id": str(seed_uuid("term:2024-fall")),
            "terms_to_plan": 2,
            "minimum_credits_per_term": "0.0",
            "maximum_credits_per_term": "-1.0",
            "preferred_credits_per_term": "3.0",
        },
    )
    assert invalid_limits.status_code == 422

    missing = client.get(f"/api/v1/academic-plans/{MISSING_ID}")
    assert missing.status_code == 404
