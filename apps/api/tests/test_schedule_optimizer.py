from __future__ import annotations

from collections.abc import Generator
from datetime import time
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
    AuditWarningSeverity,
    Course,
    DayOfWeek,
    EligibilityOverallResult,
    ScheduleConflict,
    ScheduleConflictType,
    ScheduleConstraintSet,
    ScheduleOptimizationRun,
    ScheduleOption,
    ScheduleOptionSection,
    ScheduleOptionStatus,
    SchedulePlanningMode,
    ScheduleRunStatus,
    ScheduleWarning,
    Section,
    SectionMeeting,
    SectionModality,
)
from app.seed_dev import seed_mock_data, seed_uuid
from app.services.schedule_optimizer.engine import ScheduleOptimizerApplicationService

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


def course_id(session: Session, subject: str, number: str) -> UUID:
    course = session.scalar(
        select(Course).where(Course.subject_code == subject, Course.course_number == number)
    )
    assert course is not None
    return course.id


def section_id(session: Session, seed_name: str) -> UUID:
    section = session.get(Section, seed_uuid(f"section:{seed_name}"))
    assert section is not None
    return section.id


def option_sections(session: Session, option: ScheduleOption) -> list[ScheduleOptionSection]:
    return list(
        session.scalars(
            select(ScheduleOptionSection)
            .where(ScheduleOptionSection.schedule_option_id == option.id)
            .order_by(ScheduleOptionSection.course_id, ScheduleOptionSection.section_id)
        ).all()
    )


def test_schedule_database_constraints_and_snapshot_tables(session: Session) -> None:
    run = ScheduleOptimizationRun(
        id=seed_uuid("schedule-run:test"),
        student_profile_id=seed_uuid("student-profile:mock-student"),
        term_id=seed_uuid("term:2024-fall"),
        academic_plan_run_id=None,
        planning_mode=SchedulePlanningMode.CUSTOM_COURSE_SET,
        status=ScheduleRunStatus.COMPLETED_WITH_WARNINGS,
        engine_version="phase-6a-schedule-optimizer-v1",
        minimum_credits=Decimal("3.0"),
        maximum_credits=Decimal("6.0"),
        preferred_credits=Decimal("6.0"),
        requested_option_count=2,
    )
    constraint_set = ScheduleConstraintSet(
        id=seed_uuid("schedule-constraint-set:test"),
        schedule_optimization_run_id=run.id,
        excluded_days=[DayOfWeek.FRIDAY.value],
        unavailable_time_blocks=[
            {"day_of_week": DayOfWeek.MONDAY.value, "start_time": "09:00", "end_time": "10:00"}
        ],
        earliest_start_time=time(8, 0),
        latest_end_time=time(18, 0),
        minimum_gap_minutes=0,
        maximum_gap_minutes=240,
        allowed_modalities=[
            SectionModality.IN_PERSON.value,
            SectionModality.ONLINE_ASYNCHRONOUS.value,
        ],
        excluded_modalities=[],
        required_course_ids=[],
        excluded_course_ids=[],
        required_section_ids=[],
        excluded_section_ids=[],
        prefer_online=True,
        prefer_compact_schedule=True,
        prefer_fewer_days=True,
        prefer_in_person=False,
        avoid_early_start=True,
        avoid_late_end=True,
        allow_permission_required=False,
    )
    option = ScheduleOption(
        id=seed_uuid("schedule-option:test"),
        schedule_optimization_run_id=run.id,
        option_rank=1,
        status=ScheduleOptionStatus.FEASIBLE_WITH_WARNINGS,
        total_credits=Decimal("3.0"),
        class_days_count=1,
        earliest_start_time=time(9, 0),
        latest_end_time=time(10, 15),
        total_gap_minutes=0,
        score=Decimal("82.0"),
        explanation="Score is explainable and deterministic.",
    )
    selected = ScheduleOptionSection(
        id=seed_uuid("schedule-option-section:test"),
        schedule_option_id=option.id,
        section_id=section_id(session, "2024-fall-fin-300-web"),
        course_id=course_id(session, "FIN", "300"),
        credits=Decimal("3.0"),
        eligibility_result=EligibilityOverallResult.ELIGIBLE,
        selection_reason="ONLINE_PREFERENCE",
    )
    conflict = ScheduleConflict(
        id=seed_uuid("schedule-conflict:test"),
        schedule_optimization_run_id=run.id,
        schedule_option_id=option.id,
        conflict_type=ScheduleConflictType.UNAVAILABLE_TIME,
        section_id=section_id(session, "2024-fall-fin-300-001"),
        other_section_id=None,
        day_of_week=DayOfWeek.MONDAY,
        start_time=time(9, 0),
        end_time=time(10, 0),
        message="Monday morning block conflicts with the section meeting.",
    )
    warning = ScheduleWarning(
        id=seed_uuid("schedule-warning:test"),
        schedule_optimization_run_id=run.id,
        schedule_option_id=option.id,
        warning_code="MOCK_SECTION_DATA_NOT_OFFICIAL",
        severity=AuditWarningSeverity.INFO,
        message="Mock section data is not official.",
        requires_advisor_confirmation=True,
    )

    session.add(run)
    session.flush()
    session.add(constraint_set)
    session.add(option)
    session.flush()
    session.add_all([selected, conflict, warning])
    session.commit()

    duplicate_course = ScheduleOptionSection(
        id=seed_uuid("schedule-option-section:duplicate-course"),
        schedule_option_id=option.id,
        section_id=selected.section_id,
        course_id=selected.course_id,
        credits=Decimal("3.0"),
        eligibility_result=EligibilityOverallResult.ELIGIBLE,
        selection_reason="DUPLICATE_TEST",
    )
    session.add(duplicate_course)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    failed_run = ScheduleOptimizationRun(
        id=seed_uuid("schedule-run:failed"),
        student_profile_id=seed_uuid("student-profile:mock-student"),
        term_id=seed_uuid("term:2024-fall"),
        academic_plan_run_id=None,
        planning_mode=SchedulePlanningMode.CUSTOM_COURSE_SET,
        status=ScheduleRunStatus.FAILED,
        engine_version="phase-6a-schedule-optimizer-v1",
        minimum_credits=Decimal("3.0"),
        maximum_credits=Decimal("6.0"),
        preferred_credits=Decimal("6.0"),
        requested_option_count=1,
    )
    session.add(failed_run)
    session.commit()
    persisted_failed_run = session.get(ScheduleOptimizationRun, failed_run.id)
    assert persisted_failed_run is not None
    assert persisted_failed_run.status is ScheduleRunStatus.FAILED


def test_schedule_engine_generates_no_friday_feasible_options_and_warnings(
    session: Session,
) -> None:
    run = ScheduleOptimizerApplicationService(session).create_schedule(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        term_id=seed_uuid("term:2024-fall"),
        academic_plan_run_id=None,
        planning_mode=SchedulePlanningMode.CUSTOM_COURSE_SET,
        candidate_course_ids=[
            course_id(session, "FIN", "300"),
            course_id(session, "FIN", "403"),
        ],
        minimum_credits=Decimal("3.0"),
        maximum_credits=Decimal("6.0"),
        preferred_credits=Decimal("6.0"),
        requested_option_count=3,
        excluded_days=[DayOfWeek.FRIDAY],
        unavailable_time_blocks=[],
        earliest_start_time=time(8, 0),
        latest_end_time=time(18, 0),
        allowed_modalities=[],
        excluded_modalities=[],
        required_course_ids=[],
        excluded_course_ids=[],
        required_section_ids=[],
        excluded_section_ids=[],
        prefer_online=False,
        prefer_compact_schedule=True,
        prefer_fewer_days=True,
        prefer_in_person=True,
        avoid_early_start=False,
        avoid_late_end=True,
        allow_permission_required=False,
    )

    options = session.scalars(
        select(ScheduleOption)
        .where(ScheduleOption.schedule_optimization_run_id == run.id)
        .order_by(ScheduleOption.option_rank)
    ).all()
    warnings = session.scalars(
        select(ScheduleWarning).where(ScheduleWarning.schedule_optimization_run_id == run.id)
    ).all()
    selected_section_ids = {
        selected.section_id for option in options for selected in option_sections(session, option)
    }
    friday_meetings = session.scalars(
        select(SectionMeeting).where(
            SectionMeeting.section_id.in_(selected_section_ids),
            SectionMeeting.day_of_week == DayOfWeek.FRIDAY,
        )
    ).all()

    assert run.status is ScheduleRunStatus.COMPLETED_WITH_WARNINGS
    assert options
    assert all(
        option.status
        in {ScheduleOptionStatus.FEASIBLE, ScheduleOptionStatus.FEASIBLE_WITH_WARNINGS}
        for option in options
    )
    assert not friday_meetings
    assert any(warning.warning_code == "MOCK_SECTION_DATA_NOT_OFFICIAL" for warning in warnings)
    assert any("credits" in option.explanation.lower() for option in options)


def test_schedule_engine_records_time_conflicts_and_prefers_online_when_requested(
    session: Session,
) -> None:
    run = ScheduleOptimizerApplicationService(session).create_schedule(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        term_id=seed_uuid("term:2024-fall"),
        academic_plan_run_id=None,
        planning_mode=SchedulePlanningMode.CUSTOM_COURSE_SET,
        candidate_course_ids=[
            course_id(session, "FIN", "300"),
            course_id(session, "FIN", "403"),
        ],
        minimum_credits=Decimal("6.0"),
        maximum_credits=Decimal("6.0"),
        preferred_credits=Decimal("6.0"),
        requested_option_count=2,
        excluded_days=[],
        unavailable_time_blocks=[
            {"day_of_week": DayOfWeek.TUESDAY.value, "start_time": "11:00", "end_time": "11:30"}
        ],
        earliest_start_time=None,
        latest_end_time=None,
        allowed_modalities=[],
        excluded_modalities=[],
        required_course_ids=[],
        excluded_course_ids=[],
        required_section_ids=[],
        excluded_section_ids=[],
        prefer_online=True,
        prefer_compact_schedule=False,
        prefer_fewer_days=False,
        prefer_in_person=False,
        avoid_early_start=False,
        avoid_late_end=False,
        allow_permission_required=False,
    )

    first_option = session.scalar(
        select(ScheduleOption)
        .where(ScheduleOption.schedule_optimization_run_id == run.id)
        .order_by(ScheduleOption.option_rank)
        .limit(1)
    )
    assert first_option is not None
    first_selected = option_sections(session, first_option)
    section_codes: set[str] = set()
    for selected in first_selected:
        section = session.get(Section, selected.section_id)
        assert section is not None
        section_codes.add(section.section_code)
    conflicts = session.scalars(
        select(ScheduleConflict).where(ScheduleConflict.schedule_optimization_run_id == run.id)
    ).all()
    warnings = session.scalars(
        select(ScheduleWarning).where(ScheduleWarning.schedule_optimization_run_id == run.id)
    ).all()

    assert "WEB" in section_codes
    assert any(
        conflict.conflict_type is ScheduleConflictType.UNAVAILABLE_TIME for conflict in conflicts
    )
    assert any(
        conflict.conflict_type is ScheduleConflictType.TIME_OVERLAP for conflict in conflicts
    )
    assert any(warning.warning_code == "ONLINE_ASYNC_TIMING_UNKNOWN" for warning in warnings)


def test_schedule_engine_returns_partial_when_minimum_credits_cannot_be_met(
    session: Session,
) -> None:
    run = ScheduleOptimizerApplicationService(session).create_schedule(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        term_id=seed_uuid("term:2024-fall"),
        academic_plan_run_id=None,
        planning_mode=SchedulePlanningMode.CUSTOM_COURSE_SET,
        candidate_course_ids=[
            course_id(session, "FIN", "403"),
            course_id(session, "ACTL", "300"),
        ],
        minimum_credits=Decimal("9.0"),
        maximum_credits=Decimal("9.0"),
        preferred_credits=Decimal("9.0"),
        requested_option_count=1,
        excluded_days=[],
        unavailable_time_blocks=[],
        earliest_start_time=None,
        latest_end_time=None,
        allowed_modalities=[],
        excluded_modalities=[],
        required_course_ids=[],
        excluded_course_ids=[],
        required_section_ids=[],
        excluded_section_ids=[],
        prefer_online=False,
        prefer_compact_schedule=False,
        prefer_fewer_days=False,
        prefer_in_person=False,
        avoid_early_start=False,
        avoid_late_end=False,
        allow_permission_required=False,
    )

    option = session.scalar(
        select(ScheduleOption).where(ScheduleOption.schedule_optimization_run_id == run.id)
    )
    warnings = session.scalars(
        select(ScheduleWarning).where(ScheduleWarning.schedule_optimization_run_id == run.id)
    ).all()

    assert option is not None
    assert option.status is ScheduleOptionStatus.PARTIAL
    assert option.total_credits < Decimal("9.0")
    assert any(warning.warning_code == "NO_SECTION_AVAILABLE" for warning in warnings)
    assert any(warning.warning_code == "MINIMUM_CREDITS_NOT_MET" for warning in warnings)


def test_schedule_engine_blocks_permission_required_sections_unless_allowed(
    session: Session,
) -> None:
    blocked = ScheduleOptimizerApplicationService(session).create_schedule(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        term_id=seed_uuid("term:2025-spring"),
        academic_plan_run_id=None,
        planning_mode=SchedulePlanningMode.CUSTOM_COURSE_SET,
        candidate_course_ids=[course_id(session, "FIN", "400")],
        minimum_credits=Decimal("3.0"),
        maximum_credits=Decimal("3.0"),
        preferred_credits=Decimal("3.0"),
        requested_option_count=1,
        excluded_days=[],
        unavailable_time_blocks=[],
        earliest_start_time=None,
        latest_end_time=None,
        allowed_modalities=[],
        excluded_modalities=[],
        required_course_ids=[],
        excluded_course_ids=[],
        required_section_ids=[],
        excluded_section_ids=[],
        prefer_online=False,
        prefer_compact_schedule=False,
        prefer_fewer_days=False,
        prefer_in_person=False,
        avoid_early_start=False,
        avoid_late_end=False,
        allow_permission_required=False,
    )
    blocked_warning_codes = {
        warning.warning_code
        for warning in session.scalars(
            select(ScheduleWarning).where(
                ScheduleWarning.schedule_optimization_run_id == blocked.id
            )
        ).all()
    }

    allowed = ScheduleOptimizerApplicationService(session).create_schedule(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        term_id=seed_uuid("term:2025-spring"),
        academic_plan_run_id=None,
        planning_mode=SchedulePlanningMode.CUSTOM_COURSE_SET,
        candidate_course_ids=[course_id(session, "FIN", "400")],
        minimum_credits=Decimal("3.0"),
        maximum_credits=Decimal("3.0"),
        preferred_credits=Decimal("3.0"),
        requested_option_count=1,
        excluded_days=[],
        unavailable_time_blocks=[],
        earliest_start_time=None,
        latest_end_time=None,
        allowed_modalities=[],
        excluded_modalities=[],
        required_course_ids=[],
        excluded_course_ids=[],
        required_section_ids=[],
        excluded_section_ids=[],
        prefer_online=False,
        prefer_compact_schedule=False,
        prefer_fewer_days=False,
        prefer_in_person=False,
        avoid_early_start=False,
        avoid_late_end=False,
        allow_permission_required=True,
    )
    selected = session.scalar(
        select(ScheduleOptionSection)
        .join(ScheduleOption, ScheduleOptionSection.schedule_option_id == ScheduleOption.id)
        .where(ScheduleOption.schedule_optimization_run_id == allowed.id)
    )

    assert "PERMISSION_REQUIRED_BLOCKED" in blocked_warning_codes
    assert selected is not None
    assert selected.eligibility_result is EligibilityOverallResult.PERMISSION_REQUIRED


def test_schedule_api_create_retrieve_list_compare_and_validate(client: TestClient) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))
    response = client.post(
        "/api/v1/schedule-optimizations",
        json={
            "student_profile_id": student_id,
            "term_id": str(seed_uuid("term:2024-fall")),
            "academic_plan_run_id": None,
            "planning_mode": "CUSTOM_COURSE_SET",
            "candidate_course_ids": [
                str(seed_uuid("course:FIN-300")),
                str(seed_uuid("course:FIN-403")),
            ],
            "minimum_credits": "3.0",
            "maximum_credits": "6.0",
            "preferred_credits": "6.0",
            "requested_option_count": 2,
            "excluded_days": ["FRIDAY"],
            "unavailable_time_blocks": [],
            "earliest_start_time": "08:00",
            "latest_end_time": "18:00",
            "allowed_modalities": [],
            "excluded_modalities": [],
            "required_course_ids": [],
            "excluded_course_ids": [],
            "required_section_ids": [],
            "excluded_section_ids": [],
            "prefer_online": False,
            "prefer_compact_schedule": True,
            "prefer_fewer_days": True,
            "prefer_in_person": True,
            "avoid_early_start": False,
            "avoid_late_end": True,
            "allow_permission_required": False,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    run_id = payload["id"]
    UUID(run_id)
    assert payload["planning_mode"] == "CUSTOM_COURSE_SET"
    assert payload["options"]
    assert payload["warnings"]
    assert "registration_actions" not in payload
    assert "waitlist_actions" not in payload

    assert client.get(f"/api/v1/schedule-optimizations/{run_id}").status_code == 200
    assert client.get(f"/api/v1/schedule-optimizations/{run_id}/options").status_code == 200
    assert client.get(f"/api/v1/schedule-optimizations/{run_id}/conflicts").status_code == 200
    assert client.get(f"/api/v1/schedule-optimizations/{run_id}/warnings").status_code == 200
    student_runs = client.get(f"/api/v1/students/{student_id}/schedule-optimizations")
    assert student_runs.status_code == 200
    assert any(run["id"] == run_id for run in student_runs.json())

    compare = client.post(
        "/api/v1/schedule-optimizations/compare",
        json={"schedule_optimization_run_ids": [run_id, run_id]},
    )
    assert compare.status_code == 200
    assert compare.json()[0]["schedule_optimization_run_id"] == run_id

    invalid_limits = client.post(
        "/api/v1/schedule-optimizations",
        json={
            "student_profile_id": student_id,
            "term_id": str(seed_uuid("term:2024-fall")),
            "planning_mode": "CUSTOM_COURSE_SET",
            "candidate_course_ids": [str(seed_uuid("course:FIN-300"))],
            "minimum_credits": "3.0",
            "maximum_credits": "0.0",
            "preferred_credits": "6.0",
            "requested_option_count": 1,
        },
    )
    assert invalid_limits.status_code == 400

    assert client.get(f"/api/v1/schedule-optimizations/{MISSING_ID}").status_code == 404
