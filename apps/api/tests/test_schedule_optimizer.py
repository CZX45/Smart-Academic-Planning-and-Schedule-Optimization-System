from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, date, datetime, time
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
    AcademicTerm,
    AuditWarningSeverity,
    Course,
    DataImportType,
    DayOfWeek,
    EligibilityOverallResult,
    ImportedRecordReview,
    ImportedRecordReviewDecision,
    ScheduleConflict,
    ScheduleConflictType,
    ScheduleConstraintSet,
    ScheduleOptimizationRun,
    ScheduleOption,
    ScheduleOptionSection,
    ScheduleOptionStatus,
    SchedulePlanningMode,
    ScheduleRepairSuggestion,
    ScheduleRunStatus,
    ScheduleWarning,
    Section,
    SectionDataMode,
    SectionMeeting,
    SectionModality,
    SourceType,
    StudentCourseAttempt,
    StudentProfile,
)
from app.seed_dev import seed_mock_data, seed_uuid
from app.services.data_imports.engine import DataImportApplicationService
from app.services.data_review.engine import DataReviewApplicationService
from app.services.schedule_optimizer.engine import ScheduleOptimizerApplicationService
from app.services.schedule_optimizer.real_sections import (
    evaluate_reviewed_section,
    input_snapshot_hash,
    provenance_payload,
    section_snapshot_hash,
)
from tests.test_data_reviews import section_csv

MISSING_ID = "00000000-0000-0000-0000-000000000000"


def make_schedule_fixture_term_relative(session: Session) -> None:
    prior_term = AcademicTerm(
        id=seed_uuid("term:2023-fall-schedule-fixture"),
        institution_id=seed_uuid("institution:mock-university"),
        campus_id=seed_uuid("campus:mock-main"),
        term_code="2023FA",
        name="Fall 2023",
        starts_on=date(2023, 8, 28),
        ends_on=date(2023, 12, 20),
        source_type=SourceType.MOCK,
        is_official=False,
        source_reference="Term-relative schedule test fixture",
        source_confidence="mock",
    )
    session.add(prior_term)
    completed_prerequisite = session.get(
        StudentCourseAttempt,
        seed_uuid("attempt:mock-student-fin-200-completed"),
    )
    assert completed_prerequisite is not None
    completed_prerequisite.term_id = prior_term.id
    session.commit()


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
        make_schedule_fixture_term_relative(db)
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
        make_schedule_fixture_term_relative(seed_session)

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


@pytest.mark.parametrize("excluded_day", [False, True])
def test_synchronous_online_meetings_obey_time_constraints(
    session: Session, excluded_day: bool
) -> None:
    # Online delivery does not mean asynchronous: both timed meetings overlap.
    course_ids = [course_id(session, "FIN", "300"), course_id(session, "FIN", "403")]
    sections = list(session.scalars(select(Section).where(Section.course_id.in_(course_ids))))
    for section in sections:
        for meeting in session.scalars(
            select(SectionMeeting).where(SectionMeeting.section_id == section.id)
        ):
            meeting.is_online = True
            meeting.is_arranged = False
            meeting.day_of_week = DayOfWeek.MONDAY
            meeting.start_time = time(10, 0)
            meeting.end_time = time(11, 0)
    session.commit()
    run = ScheduleOptimizerApplicationService(session).create_schedule(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        term_id=seed_uuid("term:2024-fall"),
        academic_plan_run_id=None,
        planning_mode=SchedulePlanningMode.CUSTOM_COURSE_SET,
        candidate_course_ids=course_ids,
        minimum_credits=Decimal("6"),
        maximum_credits=Decimal("6"),
        preferred_credits=Decimal("6"),
        requested_option_count=3,
        excluded_days=[DayOfWeek.MONDAY] if excluded_day else [],
        unavailable_time_blocks=[],
        earliest_start_time=None,
        latest_end_time=None,
        allowed_modalities=[],
        excluded_modalities=[],
        required_course_ids=course_ids,
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
    options = session.scalars(
        select(ScheduleOption).where(ScheduleOption.schedule_optimization_run_id == run.id)
    ).all()
    assert not any(
        option.status
        in {ScheduleOptionStatus.FEASIBLE, ScheduleOptionStatus.FEASIBLE_WITH_WARNINGS}
        for option in options
    )
    conflicts = session.scalars(
        select(ScheduleConflict).where(ScheduleConflict.schedule_optimization_run_id == run.id)
    ).all()
    expected = (
        ScheduleConflictType.EXCLUDED_DAY if excluded_day else ScheduleConflictType.TIME_OVERLAP
    )
    assert any(conflict.conflict_type is expected for conflict in conflicts)


def test_reviewed_imported_boundary_requires_successful_stage_11_apply(session: Session) -> None:
    mock_section = session.scalar(
        select(Section).where(Section.id == seed_uuid("section:2024-fall-fin-300-web"))
    )
    assert mock_section is not None
    student = session.get(StudentProfile, seed_uuid("student-profile:mock-student"))
    assert student is not None

    denied = evaluate_reviewed_section(
        session,
        section=mock_section,
        student=student,
        target_term_id=seed_uuid("term:2024-fall"),
        requested_course_id=seed_uuid("course:FIN-300"),
        now=datetime.now(UTC),
    )
    assert not denied.eligible
    assert "SECTION_SOURCE_NOT_APPLIED" in denied.reason_codes

    run = DataImportApplicationService(session).create_import(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.SECTION_SCHEDULE,
        file_name="reviewed-section.csv",
        file_mime_type="text/csv",
        content=section_csv("REAL-1"),
        source_type=SourceType.BROWSER_EXTENSION,
        source_reference="Synthetic visible-page section fixture",
    )
    review_service = DataReviewApplicationService(session)
    review = review_service.create_review_session(
        data_import_run_id=run.id,
        reviewer_label="Synthetic reviewer",
    )
    record_review = session.scalar(
        select(ImportedRecordReview).where(ImportedRecordReview.review_session_id == review.id)
    )
    assert record_review is not None
    review_service.update_record_review(
        review_session_id=review.id,
        record_review_id=record_review.id,
        decision=ImportedRecordReviewDecision.CONFIRMED,
    )
    applied = review_service.apply_review_session(review.id)
    assert applied.application is not None
    section = session.scalar(select(Section).where(Section.section_code == "REAL-1"))
    assert section is not None
    decision = evaluate_reviewed_section(
        session,
        section=section,
        student=student,
        target_term_id=seed_uuid("term:2024-fall"),
        requested_course_id=seed_uuid("course:FIN-300"),
        now=datetime.now(UTC),
    )
    assert decision.eligible
    assert decision.provenance is not None
    assert decision.provenance.crn_source_status == "NOT_PROVIDED"
    serialized_provenance = provenance_payload(decision.provenance)
    assert serialized_provenance is not None
    assert serialized_provenance["crn_source_status"] == "NOT_PROVIDED"

    refreshed_run = DataImportApplicationService(session).create_import(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.SECTION_SCHEDULE,
        file_name="reviewed-section-refresh.csv",
        file_mime_type="text/csv",
        content=section_csv("REAL-1"),
        source_type=SourceType.BROWSER_EXTENSION,
        source_reference="Synthetic visible-page section refresh fixture",
    )
    refreshed_review = review_service.create_review_session(
        data_import_run_id=refreshed_run.id,
        reviewer_label="Synthetic reviewer",
    )
    refreshed_record_review = session.scalar(
        select(ImportedRecordReview).where(
            ImportedRecordReview.review_session_id == refreshed_review.id
        )
    )
    assert refreshed_record_review is not None
    review_service.update_record_review(
        review_session_id=refreshed_review.id,
        record_review_id=refreshed_record_review.id,
        decision=ImportedRecordReviewDecision.CONFIRMED,
    )
    refreshed_applied = review_service.apply_review_session(refreshed_review.id)
    assert refreshed_applied.application is not None
    refreshed_decision = evaluate_reviewed_section(
        session,
        section=section,
        student=student,
        target_term_id=seed_uuid("term:2024-fall"),
        requested_course_id=seed_uuid("course:FIN-300"),
        now=datetime.now(UTC),
    )
    assert refreshed_decision.eligible
    assert refreshed_decision.provenance is not None
    assert input_snapshot_hash(
        section_data_mode=SectionDataMode.REVIEWED_IMPORTED.value,
        student_id=seed_uuid("student-profile:mock-student"),
        institution_id=seed_uuid("institution:mock-university"),
        term_id=seed_uuid("term:2024-fall"),
        course_ids=[seed_uuid("course:FIN-300")],
        section_ids=[section.id],
        maximum_source_age_minutes=None,
    ) == input_snapshot_hash(
        section_data_mode=SectionDataMode.REVIEWED_IMPORTED.value,
        student_id=seed_uuid("student-profile:mock-student"),
        institution_id=seed_uuid("institution:mock-university"),
        term_id=seed_uuid("term:2024-fall"),
        course_ids=[seed_uuid("course:FIN-300")],
        section_ids=[section.id],
        maximum_source_age_minutes=None,
    )


def test_reviewed_imported_mode_never_falls_back_to_mock_sections(session: Session) -> None:
    run = ScheduleOptimizerApplicationService(session).create_schedule(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        term_id=seed_uuid("term:2024-fall"),
        academic_plan_run_id=None,
        planning_mode=SchedulePlanningMode.CUSTOM_COURSE_SET,
        section_data_mode=SectionDataMode.REVIEWED_IMPORTED,
        candidate_course_ids=[course_id(session, "FIN", "300")],
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
    detail = session.get(ScheduleOptimizationRun, run.id)
    assert detail is not None
    assert detail.section_data_mode is SectionDataMode.REVIEWED_IMPORTED
    assert detail.source_readiness_payload["covered_course_count"] == 0
    assert detail.input_snapshot_hash is not None
    warnings = session.scalars(
        select(ScheduleWarning).where(ScheduleWarning.schedule_optimization_run_id == run.id)
    ).all()
    assert any(warning.warning_code == "SECTION_SOURCE_NOT_APPLIED" for warning in warnings)
    selected = session.scalars(
        select(ScheduleOptionSection)
        .join(ScheduleOption, ScheduleOptionSection.schedule_option_id == ScheduleOption.id)
        .where(ScheduleOption.schedule_optimization_run_id == run.id)
    ).all()
    assert not selected


def test_same_fixture_inputs_produce_same_ranked_options_three_times(
    session: Session,
) -> None:
    signatures: list[tuple[object, ...]] = []
    snapshot_hashes: set[str | None] = set()

    for _ in range(3):
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
            requested_option_count=3,
            excluded_days=[],
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
            avoid_early_start=True,
            avoid_late_end=True,
            allow_permission_required=False,
            prefer_no_gaps=True,
            prefer_morning=True,
            prefer_afternoon=False,
            diversity_mode="HIGH",
            allow_partial_options=True,
            max_combinations=24,
        )
        snapshot_hashes.add(run.input_snapshot_hash)
        options = session.scalars(
            select(ScheduleOption)
            .where(ScheduleOption.schedule_optimization_run_id == run.id)
            .order_by(ScheduleOption.option_rank)
        ).all()
        signatures.append(
            tuple(
                (
                    option.option_rank,
                    option.status.value,
                    str(option.total_credits),
                    str(option.total_score),
                    option.explanation,
                    option.score_explanation,
                    tuple(
                        str(selected.section_id) for selected in option_sections(session, option)
                    ),
                )
                for option in options
            )
        )

    assert len(snapshot_hashes) == 1
    assert signatures[0] == signatures[1] == signatures[2]


def test_section_snapshot_hash_changes_when_meeting_shape_changes(session: Session) -> None:
    section = session.scalar(
        select(Section).where(Section.id == seed_uuid("section:2024-fall-fin-300-web"))
    )
    assert section is not None
    meetings = list(
        session.scalars(
            select(SectionMeeting)
            .where(SectionMeeting.section_id == section.id)
            .order_by(SectionMeeting.display_order, SectionMeeting.id)
        ).all()
    )
    assert meetings
    original_hash = section_snapshot_hash(section, meetings)
    original_start = meetings[0].start_time
    meetings[0].start_time = time(8, 0) if original_start != time(8, 0) else time(8, 30)
    assert section_snapshot_hash(section, meetings) != original_hash


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


def test_phase_6b_scores_priorities_and_diversifies_options(session: Session) -> None:
    fin_403_id = course_id(session, "FIN", "403")
    fin_403_section_id = section_id(session, "2024-fall-fin-403-002")

    run = ScheduleOptimizerApplicationService(session).create_schedule(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        term_id=seed_uuid("term:2024-fall"),
        academic_plan_run_id=None,
        planning_mode=SchedulePlanningMode.CUSTOM_COURSE_SET,
        candidate_course_ids=[
            course_id(session, "FIN", "300"),
            fin_403_id,
        ],
        minimum_credits=Decimal("6.0"),
        maximum_credits=Decimal("6.0"),
        preferred_credits=Decimal("6.0"),
        requested_option_count=3,
        excluded_days=[],
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
        avoid_early_start=True,
        avoid_late_end=True,
        allow_permission_required=False,
        preference_weights={
            "gap": Decimal("1.5"),
            "priority": Decimal("2.0"),
            "time": Decimal("1.0"),
        },
        course_priority_weights={fin_403_id: Decimal("3.0")},
        section_priority_weights={fin_403_section_id: Decimal("5.0")},
        prefer_no_gaps=True,
        prefer_morning=True,
        prefer_afternoon=False,
        diversity_mode="HIGH",
        allow_partial_options=True,
        max_combinations=24,
    )

    constraint_set = session.scalar(
        select(ScheduleConstraintSet).where(
            ScheduleConstraintSet.schedule_optimization_run_id == run.id
        )
    )
    options = session.scalars(
        select(ScheduleOption)
        .where(ScheduleOption.schedule_optimization_run_id == run.id)
        .order_by(ScheduleOption.option_rank)
    ).all()

    assert constraint_set is not None
    assert constraint_set.preference_weights["priority"] == "2.0"
    assert constraint_set.course_priority_weights[str(fin_403_id)] == "3.0"
    assert constraint_set.section_priority_weights[str(fin_403_section_id)] == "5.0"
    assert constraint_set.prefer_no_gaps is True
    assert constraint_set.prefer_morning is True
    assert constraint_set.diversity_mode == "HIGH"
    assert constraint_set.max_combinations == 24
    assert len(options) >= 2
    assert options[0].total_score == options[0].score
    assert options[0].credit_score > Decimal("0.00")
    assert options[0].priority_score > Decimal("0.00")
    assert options[0].penalty_score <= Decimal("0.00")
    assert any(
        item["reason_code"] == "SECTION_PRIORITY_WEIGHT" for item in options[0].score_explanation
    )
    assert options[0].diversity_rank == 1
    assert options[0].shared_section_count_with_previous_option == 0
    assert options[1].diversity_rank == 2
    assert options[1].difference_summary


def test_phase_6b_repair_suggestions_when_hard_constraints_block_full_schedule(
    session: Session,
) -> None:
    required_friday = section_id(session, "2024-fall-fin-403-friday")

    run = ScheduleOptimizerApplicationService(session).create_schedule(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        term_id=seed_uuid("term:2024-fall"),
        academic_plan_run_id=None,
        planning_mode=SchedulePlanningMode.CUSTOM_COURSE_SET,
        candidate_course_ids=[course_id(session, "FIN", "403")],
        minimum_credits=Decimal("3.0"),
        maximum_credits=Decimal("3.0"),
        preferred_credits=Decimal("3.0"),
        requested_option_count=2,
        excluded_days=[DayOfWeek.FRIDAY],
        unavailable_time_blocks=[],
        earliest_start_time=None,
        latest_end_time=None,
        allowed_modalities=[],
        excluded_modalities=[],
        required_course_ids=[],
        excluded_course_ids=[],
        required_section_ids=[required_friday],
        excluded_section_ids=[],
        prefer_online=False,
        prefer_compact_schedule=False,
        prefer_fewer_days=False,
        prefer_in_person=False,
        avoid_early_start=False,
        avoid_late_end=False,
        allow_permission_required=False,
        preference_weights={},
        course_priority_weights={},
        section_priority_weights={},
        prefer_no_gaps=False,
        prefer_morning=False,
        prefer_afternoon=False,
        diversity_mode="STANDARD",
        allow_partial_options=False,
        max_combinations=10,
    )

    option = session.scalar(
        select(ScheduleOption).where(ScheduleOption.schedule_optimization_run_id == run.id)
    )
    suggestions = session.scalars(
        select(ScheduleRepairSuggestion)
        .where(ScheduleRepairSuggestion.schedule_optimization_run_id == run.id)
        .order_by(ScheduleRepairSuggestion.suggestion_type)
    ).all()

    assert option is not None
    assert option.status is ScheduleOptionStatus.INFEASIBLE
    assert {suggestion.suggestion_type for suggestion in suggestions} >= {
        "RELAX_EXCLUDED_DAY",
        "REMOVE_REQUIRED_SECTION",
    }
    assert all(suggestion.message for suggestion in suggestions)
    assert any(suggestion.requires_advisor_confirmation for suggestion in suggestions)


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

    advanced = client.post(
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
            "minimum_credits": "6.0",
            "maximum_credits": "6.0",
            "preferred_credits": "6.0",
            "requested_option_count": 3,
            "max_options": 3,
            "max_combinations": 24,
            "excluded_days": [],
            "unavailable_time_blocks": [],
            "preference_weights": {"priority": "2.0", "gap": "1.5"},
            "course_priority_weights": {str(seed_uuid("course:FIN-403")): "3.0"},
            "section_priority_weights": {str(seed_uuid("section:2024-fall-fin-403-002")): "5.0"},
            "prefer_no_gaps": True,
            "prefer_morning": True,
            "prefer_afternoon": False,
            "diversity_mode": "HIGH",
            "allow_partial_options": True,
        },
    )
    assert advanced.status_code == 201
    advanced_payload = advanced.json()
    assert advanced_payload["options"][0]["score_breakdown"]["priority_score"] != "0.00"
    assert advanced_payload["options"][0]["diversity_rank"] == 1
    assert "hard_constraint_results" in advanced_payload
    assert "soft_preference_results" in advanced_payload
    assert "repair_suggestions" in advanced_payload

    invalid_weight = client.post(
        "/api/v1/schedule-optimizations",
        json={
            "student_profile_id": student_id,
            "term_id": str(seed_uuid("term:2024-fall")),
            "planning_mode": "CUSTOM_COURSE_SET",
            "candidate_course_ids": [str(seed_uuid("course:FIN-300"))],
            "minimum_credits": "3.0",
            "maximum_credits": "3.0",
            "preferred_credits": "3.0",
            "requested_option_count": 1,
            "preference_weights": {"priority": "-1.0"},
        },
    )
    assert invalid_weight.status_code == 400

    invalid_pinned_section = client.post(
        "/api/v1/schedule-optimizations",
        json={
            "student_profile_id": student_id,
            "term_id": str(seed_uuid("term:2024-fall")),
            "planning_mode": "CUSTOM_COURSE_SET",
            "candidate_course_ids": [str(seed_uuid("course:FIN-300"))],
            "minimum_credits": "3.0",
            "maximum_credits": "3.0",
            "preferred_credits": "3.0",
            "requested_option_count": 1,
            "required_section_ids": [MISSING_ID],
        },
    )
    assert invalid_pinned_section.status_code == 400

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


def test_zero_credit_sections_do_not_inherit_course_default(session: Session) -> None:
    target_course = course_id(session, "FIN", "300")
    for section in session.scalars(select(Section).where(Section.course_id == target_course)):
        section.credits = Decimal("0")
    session.commit()
    run = ScheduleOptimizerApplicationService(session).create_schedule(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        term_id=seed_uuid("term:2024-fall"),
        academic_plan_run_id=None,
        planning_mode=SchedulePlanningMode.CUSTOM_COURSE_SET,
        candidate_course_ids=[target_course],
        minimum_credits=Decimal("0"),
        maximum_credits=Decimal("0"),
        preferred_credits=Decimal("0"),
        requested_option_count=3,
        excluded_days=[],
        unavailable_time_blocks=[],
        earliest_start_time=None,
        latest_end_time=None,
        allowed_modalities=[],
        excluded_modalities=[],
        required_course_ids=[target_course],
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
    options = list(
        session.scalars(
            select(ScheduleOption).where(ScheduleOption.schedule_optimization_run_id == run.id)
        )
    )
    assert options
    assert any(option_sections(session, option) for option in options)
    assert all(option.total_credits == Decimal("0") for option in options)
    assert all(
        selected.credits == Decimal("0")
        for option in options
        for selected in option_sections(session, option)
    )
