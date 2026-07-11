import json
from collections import Counter
from collections.abc import Generator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.academic import (
    AppliedImportAction,
    AppliedImportedRecord,
    CourseStateRecord,
    CourseStateSnapshot,
    CourseStateStatus,
    CourseStateValidationState,
    DataApplicationRun,
    DataApplicationStatus,
    DataImportReviewStatus,
    DataImportType,
    EligibilityMode,
    ImportedRecord,
    ImportedRecordReview,
    ImportedRecordReviewDecision,
    SourceType,
    StudentCourseAttempt,
    StudentCourseAttemptStatus,
)
from app.seed_dev import seed_mock_data, seed_uuid
from app.services.course_eligibility.engine import CourseEligibilityEngine
from app.services.data_imports.engine import DataImportApplicationService
from app.services.data_review.engine import DataReviewApplicationService
from tests.test_data_imports import kean_myprogress_with_85_rows_json


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


def count_rows(session: Session, model: type[Any]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def transcript_csv() -> str:
    return "\n".join(
        [
            "term,course_code,title,grade,credits,status",
            "2024FA,FIN 300,Mock Managerial Finance,B,3.0,COMPLETED",
            "2024FA,FIN 999,Unreviewed Special Topic,A,3.0,COMPLETED",
        ]
    )


def create_import(session: Session) -> UUID:
    run = DataImportApplicationService(session).create_import(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.UNOFFICIAL_TRANSCRIPT,
        file_name="mock-transcript.csv",
        file_mime_type="text/csv",
        content=transcript_csv(),
        source_type=SourceType.STUDENT_PROVIDED,
        source_reference="Student-uploaded Phase 7B test fixture",
    )
    return run.id


def myprogress_course_row(
    index: int,
    *,
    course_code: str,
    title: str,
    status: str,
    term: str = "",
    requirement: str = "Finance Requirements",
) -> dict[str, object]:
    return {
        "requirements": requirement,
        "requirement_section": requirement,
        "status": status,
        "course_code": course_code,
        "course_title": title,
        "term_code": term,
        "credits": "3",
        "raw_row_text": f"{status} {course_code} {title} {term} 3",
        "source_table_index": "1",
        "source_row_index": str(index),
        "field_provenance": {
            "course_code": {
                "rawText": course_code,
                "source": f"sanitized table 1 row {index}",
                "confidence": "high",
            }
        },
        "confidence": "high",
        "warnings": [],
    }


def reviewed_myprogress_json(
    rows: list[dict[str, object]],
    *,
    bounded: bool = False,
    validation_status: str = "AUTO_VERIFIED",
) -> str:
    return json.dumps(
        {
            "source_type": "BROWSER_EXTENSION",
            "staging_only": True,
            "page_type": "KEAN_MY_PROGRESS_PAGE",
            "programSummary": {
                "programName": "Finance, BS",
                "degree": "Bachelor of Science",
                "catalogYear": 2024,
            },
            "creditSummary": {
                "totalAppliedCredits": 104,
                "totalRequiredCredits": 120,
                "completedCredits": 67,
                "inProgressCredits": 24,
                "plannedCredits": 13,
                "remainingCredits": 16,
            },
            "requirementGroups": [
                {
                    "name": "Finance Requirements",
                    "statusText": "Reviewed sanitized requirement summary",
                    "confidence": "high",
                    "requiresReview": False,
                }
            ],
            "courseRows": rows,
            "rawSnapshot": {
                "diagnostics": {
                    "rowCount": len(rows),
                    "courseLikeRowCount": len(rows),
                    "requirementGroupCount": 1,
                    "bounded": bounded,
                    "truncated": bounded,
                }
            },
            "validation": {
                "status": validation_status,
                "exceptionCount": 0,
                "exceptions": [],
                "autoConfirmedFieldCount": 4,
                "autoConfirmedCourseRowCount": len(rows),
                "overallConfidenceScore": 1,
                "downstreamAnalysisAllowed": validation_status == "AUTO_VERIFIED",
            },
        }
    )


def create_myprogress_import(
    session: Session,
    rows: list[dict[str, object]],
    *,
    bounded: bool = False,
    validation_status: str = "AUTO_VERIFIED",
) -> UUID:
    run = DataImportApplicationService(session).create_import(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.DEGREE_AUDIT_EXPORT,
        file_name="sanitized-myprogress-course-states.json",
        file_mime_type="application/json",
        content=reviewed_myprogress_json(
            rows,
            bounded=bounded,
            validation_status=validation_status,
        ),
        source_type=SourceType.BROWSER_EXTENSION,
        source_reference="Sanitized MyProgress course-state application fixture",
    )
    return run.id


def select_review_record(
    session: Session,
    review_id: UUID,
    course_code: str,
) -> ImportedRecordReview:
    review_record = session.scalar(
        select(ImportedRecordReview)
        .join(ImportedRecord, ImportedRecordReview.imported_record_id == ImportedRecord.id)
        .where(
            ImportedRecordReview.review_session_id == review_id,
            ImportedRecord.normalized_payload["course_code"].as_string() == course_code,
        )
    )
    assert review_record is not None
    return review_record


def select_created_application_record(
    session: Session,
    application_id: UUID,
) -> AppliedImportedRecord:
    applied = session.scalar(
        select(AppliedImportedRecord)
        .where(
            AppliedImportedRecord.data_application_run_id == application_id,
            AppliedImportedRecord.action == AppliedImportAction.CREATED,
        )
        .order_by(AppliedImportedRecord.created_at, AppliedImportedRecord.id)
    )
    assert applied is not None
    return applied


def test_review_service_dry_run_and_apply_are_explicit_and_idempotent(
    session: Session,
) -> None:
    run_id = create_import(session)
    attempts_before = count_rows(session, StudentCourseAttempt)

    service = DataReviewApplicationService(session)
    review = service.create_review_session(
        data_import_run_id=run_id,
        reviewer_label="Mock student self-review",
    )

    assert review.status is DataImportReviewStatus.IN_REVIEW
    assert (
        session.scalar(
            select(func.count())
            .select_from(ImportedRecordReview)
            .where(ImportedRecordReview.review_session_id == review.id)
        )
        == 2
    )
    assert count_rows(session, StudentCourseAttempt) == attempts_before

    fin_300_review = select_review_record(session, review.id, "FIN 300")
    service.update_record_review(
        review_session_id=review.id,
        record_review_id=fin_300_review.id,
        decision=ImportedRecordReviewDecision.CONFIRMED,
    )

    dry_run = service.apply_review_session(review.id, dry_run=True)
    assert dry_run.dry_run is True
    assert dry_run.application is None
    assert dry_run.applied_records[0].action is AppliedImportAction.CREATED
    assert count_rows(session, StudentCourseAttempt) == attempts_before
    assert (
        session.scalar(
            select(func.count())
            .select_from(DataApplicationRun)
            .where(DataApplicationRun.review_session_id == review.id)
        )
        == 0
    )

    applied = service.apply_review_session(review.id)
    assert applied.dry_run is False
    assert applied.application is not None
    assert applied.application.status is DataApplicationStatus.APPLIED_WITH_WARNINGS
    assert count_rows(session, StudentCourseAttempt) == attempts_before + 1

    attempt = session.scalar(
        select(StudentCourseAttempt)
        .where(
            StudentCourseAttempt.student_profile_id == seed_uuid("student-profile:mock-student"),
            StudentCourseAttempt.course_id == seed_uuid("course:FIN-300"),
            StudentCourseAttempt.source_reference.like("%Phase 7B data review%"),
        )
        .order_by(StudentCourseAttempt.created_at.desc())
    )
    assert attempt is not None
    assert attempt.is_official is False
    assert attempt.source_type is SourceType.STUDENT_PROVIDED

    first_applied_record = select_created_application_record(session, applied.application.id)
    assert first_applied_record.action is AppliedImportAction.CREATED
    assert first_applied_record.target_entity_id == attempt.id

    duplicate = service.apply_review_session(review.id)
    assert duplicate.application is not None
    duplicate_actions = {
        row.action
        for row in session.scalars(
            select(AppliedImportedRecord).where(
                AppliedImportedRecord.data_application_run_id == duplicate.application.id
            )
        )
    }
    assert AppliedImportAction.SKIPPED_DUPLICATE in duplicate_actions
    assert count_rows(session, StudentCourseAttempt) == attempts_before + 1


def test_review_api_exposes_review_records_application_logs_and_student_index(
    client: TestClient,
) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))
    import_response = client.post(
        "/api/v1/data-imports",
        json={
            "student_profile_id": student_id,
            "import_type": "UNOFFICIAL_TRANSCRIPT",
            "file_name": "mock-transcript.csv",
            "file_mime_type": "text/csv",
            "content": transcript_csv(),
            "source_type": "STUDENT_PROVIDED",
            "source_reference": "Student-uploaded Phase 7B API fixture",
        },
    )
    assert import_response.status_code == 201
    run_id = import_response.json()["id"]

    review_response = client.post(
        "/api/v1/data-import-reviews",
        json={
            "data_import_run_id": run_id,
            "reviewer_label": "Mock student self-review",
        },
    )
    assert review_response.status_code == 201
    review_payload = review_response.json()
    review_id = review_payload["id"]
    assert review_payload["status"] == "IN_REVIEW"
    assert review_payload["student_profile_id"] == student_id

    get_review = client.get(f"/api/v1/data-import-reviews/{review_id}")
    assert get_review.status_code == 200
    assert get_review.json()["id"] == review_id

    records_response = client.get(f"/api/v1/data-import-reviews/{review_id}/records")
    assert records_response.status_code == 200
    records = records_response.json()
    fin_300_record = next(
        record
        for record in records
        if record["imported_record"]["normalized_payload"]["course_code"] == "FIN 300"
    )
    assert fin_300_record["decision"] == "UNREVIEWED"

    patch_response = client.patch(
        f"/api/v1/data-import-reviews/{review_id}/records/{fin_300_record['id']}",
        json={"decision": "CONFIRMED", "review_note": "Matches student copy."},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["decision"] == "CONFIRMED"

    dry_run_response = client.post(
        f"/api/v1/data-import-reviews/{review_id}/apply",
        json={"dry_run": True, "allow_advisor_review_records": False},
    )
    assert dry_run_response.status_code == 200
    assert dry_run_response.json()["dry_run"] is True
    assert dry_run_response.json()["application"] is None
    assert dry_run_response.json()["applied_records"][0]["action"] == "CREATED"

    apply_response = client.post(
        f"/api/v1/data-import-reviews/{review_id}/apply",
        json={"dry_run": False, "allow_advisor_review_records": False},
    )
    assert apply_response.status_code == 200
    apply_payload = apply_response.json()
    application_id = apply_payload["application"]["id"]
    assert apply_payload["application"]["status"] == "APPLIED_WITH_WARNINGS"

    applications_response = client.get(f"/api/v1/data-import-reviews/{review_id}/applications")
    assert applications_response.status_code == 200
    assert applications_response.json()[0]["id"] == application_id

    application_response = client.get(f"/api/v1/data-applications/{application_id}")
    assert application_response.status_code == 200
    assert application_response.json()["application"]["id"] == application_id
    assert application_response.json()["applied_records"]

    warnings_response = client.get(f"/api/v1/data-import-reviews/{review_id}/warnings")
    assert warnings_response.status_code == 200
    assert any(
        warning["warning_code"] == "STAGING_ONLY_NOT_OFFICIAL"
        for warning in warnings_response.json()
    )

    student_reviews = client.get(f"/api/v1/students/{student_id}/data-import-reviews")
    assert student_reviews.status_code == 200
    assert any(review["id"] == review_id for review in student_reviews.json())


def test_course_state_snapshot_api_returns_active_student_scoped_snapshot(
    client: TestClient,
) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))
    content = reviewed_myprogress_json(
        [
            myprogress_course_row(
                1,
                course_code="FIN 300",
                title="Managerial Finance",
                status="COMPLETED",
                term="2024FA",
            ),
            myprogress_course_row(
                2,
                course_code="FIN 400",
                title="Advanced Finance",
                status="PLANNED",
                term="2025SP",
            ),
        ]
    )
    import_response = client.post(
        "/api/v1/data-imports",
        json={
            "student_profile_id": student_id,
            "import_type": "DEGREE_AUDIT_EXPORT",
            "file_name": "sanitized-myprogress-course-states.json",
            "file_mime_type": "application/json",
            "content": content,
            "source_type": "BROWSER_EXTENSION",
            "source_reference": "Sanitized MyProgress course-state API fixture",
        },
    )
    assert import_response.status_code == 201
    review_response = client.post(
        "/api/v1/data-import-reviews",
        json={
            "data_import_run_id": import_response.json()["id"],
            "reviewer_label": "Sanitized MyProgress self-review",
        },
    )
    assert review_response.status_code == 201
    apply_response = client.post(
        f"/api/v1/data-import-reviews/{review_response.json()['id']}/apply",
        json={"dry_run": False, "allow_advisor_review_records": False},
    )
    assert apply_response.status_code == 200
    application_payload = apply_response.json()
    snapshot = application_payload["course_state_snapshot"]
    summary = application_payload["summary"]
    assert summary["source_import_id"] == import_response.json()["id"]
    assert summary["snapshot_id"] == snapshot["id"]
    assert summary["applied_count"] == sum(
        record["action"] in {"CREATED", "UPDATED"}
        for record in application_payload["applied_records"]
    )
    assert summary["duplicate_count"] == 0
    assert snapshot["is_active"] is True
    assert snapshot["completed_count"] == 1
    assert snapshot["planned_count"] == 1
    assert snapshot["readiness"]["semester_schedule"]["status"] == "DEMO_ONLY"

    active_response = client.get(f"/api/v1/students/{student_id}/course-state-snapshots/active")
    assert active_response.status_code == 200
    active = active_response.json()
    assert active["snapshot"]["id"] == snapshot["id"]
    assert {state["status"] for state in active["course_states"]} == {
        "COMPLETED",
        "PLANNED",
    }

    detail_response = client.get(f"/api/v1/course-state-snapshots/{snapshot['id']}")
    assert detail_response.status_code == 404

    schedule_response = client.post(
        "/api/v1/schedule-optimizations",
        json={
            "student_profile_id": student_id,
            "term_id": str(seed_uuid("term:2024-fall")),
            "academic_plan_run_id": None,
            "planning_mode": "CUSTOM_COURSE_SET",
            "candidate_course_ids": [str(seed_uuid("course:FIN-300"))],
            "minimum_credits": "3.0",
            "maximum_credits": "3.0",
            "preferred_credits": "3.0",
            "requested_option_count": 1,
            "excluded_days": [],
            "unavailable_time_blocks": [],
            "allowed_modalities": [],
            "excluded_modalities": [],
            "required_course_ids": [],
            "excluded_course_ids": [],
            "required_section_ids": [],
            "excluded_section_ids": [],
        },
    )
    assert schedule_response.status_code == 400
    assert "REAL_SECTION_SEARCH_DATA_NOT_IMPORTED" in schedule_response.text

    missing_student = client.get(f"/api/v1/students/{UUID(int=0)}/course-state-snapshots/active")
    assert missing_student.status_code == 404


def test_reviewed_myprogress_states_apply_with_status_semantics_and_idempotency(
    session: Session,
) -> None:
    rows = [
        myprogress_course_row(
            1,
            course_code="FIN 300",
            title="Managerial Finance",
            status="COMPLETED",
            term="2024FA",
        ),
        myprogress_course_row(
            2,
            course_code="FIN 350",
            title="Applied Finance Eligibility Lab",
            status="IN_PROGRESS",
            term="2025SP",
        ),
        myprogress_course_row(
            3,
            course_code="FIN 400",
            title="Advanced Finance",
            status="PLANNED",
            term="2025SP",
        ),
        myprogress_course_row(
            4,
            course_code="FIN 450",
            title="Advanced Finance Capstone",
            status="NOT_STARTED",
        ),
        myprogress_course_row(
            5,
            course_code="EXT 999",
            title="External unmatched evidence",
            status="COMPLETED",
            term="2024FA",
        ),
    ]
    run_id = create_myprogress_import(session, rows, bounded=True)
    service = DataReviewApplicationService(session)
    review = service.create_review_session(
        data_import_run_id=run_id,
        reviewer_label="Sanitized MyProgress self-review",
    )

    dry_run = service.apply_review_session(review.id, dry_run=True)
    assert dry_run.course_state_snapshot is None
    assert {
        outcome.reason_code
        for outcome in dry_run.applied_records
        if outcome.reason_code.startswith("WOULD_APPLY")
    } == {
        "WOULD_APPLY_COURSE_STATE",
        "WOULD_APPLY_NOT_STARTED_REQUIREMENT_OPTION",
        "WOULD_APPLY_UNMATCHED_EXTERNAL_EVIDENCE",
    }
    assert session.scalar(select(func.count()).select_from(CourseStateSnapshot)) == 0

    result = service.apply_review_session(review.id)
    snapshot = result.course_state_snapshot
    assert snapshot is not None
    assert snapshot.is_active is True
    assert snapshot.is_official is False
    assert snapshot.official_application_ready is False
    assert snapshot.completed_count == 2
    assert snapshot.in_progress_count == 1
    assert snapshot.planned_count == 1
    assert snapshot.not_started_count == 1
    assert snapshot.matched_count == 4
    assert snapshot.unmatched_count == 1
    assert snapshot.extraction_bounded is True
    planner_readiness = snapshot.readiness_payload["long_term_planner"]
    schedule_readiness = snapshot.readiness_payload["semester_schedule"]
    assert isinstance(planner_readiness, dict)
    assert isinstance(schedule_readiness, dict)
    assert planner_readiness["status"] == "BLOCKED"
    assert "SOURCE_BOUNDED_OR_TRUNCATED" in planner_readiness["blocking_reasons"]
    assert schedule_readiness["status"] == "DEMO_ONLY"

    states = session.scalars(
        select(CourseStateRecord)
        .where(CourseStateRecord.snapshot_id == snapshot.id)
        .order_by(CourseStateRecord.source_row_index)
    ).all()
    assert len(states) == 5
    by_code = {state.normalized_course_code: state for state in states}
    assert by_code["FIN 300"].status is CourseStateStatus.COMPLETED
    assert by_code["FIN 350"].status is CourseStateStatus.IN_PROGRESS
    assert by_code["FIN 400"].status is CourseStateStatus.PLANNED
    assert by_code["FIN 450"].status is CourseStateStatus.NOT_STARTED
    assert by_code["FIN 450"].student_course_attempt_id is None
    assert by_code["EXT 999"].validation_state is CourseStateValidationState.EXTERNAL_EVIDENCE
    assert by_code["EXT 999"].matched_course_id is None
    ext_provenance = by_code["EXT 999"].provenance["course_code"]
    assert isinstance(ext_provenance, dict)
    assert ext_provenance["source"] == "sanitized table 1 row 5"

    snapshot_attempts = session.scalars(
        select(StudentCourseAttempt).where(
            StudentCourseAttempt.course_state_snapshot_id == snapshot.id
        )
    ).all()
    assert {attempt.status for attempt in snapshot_attempts} == {
        StudentCourseAttemptStatus.COMPLETED,
        StudentCourseAttemptStatus.IN_PROGRESS,
        StudentCourseAttemptStatus.PLANNED,
    }

    duplicate = service.apply_review_session(review.id)
    assert duplicate.course_state_snapshot is not None
    assert duplicate.course_state_snapshot.id == snapshot.id
    assert session.scalar(select(func.count()).select_from(CourseStateSnapshot)) == 1
    assert (
        session.scalar(
            select(func.count())
            .select_from(StudentCourseAttempt)
            .where(StudentCourseAttempt.course_state_snapshot_id == snapshot.id)
        )
        == 3
    )
    duplicate_actions = {outcome.action for outcome in duplicate.applied_records}
    assert duplicate_actions == {AppliedImportAction.SKIPPED_DUPLICATE}


def test_newer_invalid_myprogress_import_does_not_replace_active_snapshot(
    session: Session,
) -> None:
    valid_run_id = create_myprogress_import(
        session,
        [
            myprogress_course_row(
                1,
                course_code="FIN 300",
                title="Managerial Finance",
                status="COMPLETED",
                term="2024FA",
            )
        ],
    )
    service = DataReviewApplicationService(session)
    valid_review = service.create_review_session(
        data_import_run_id=valid_run_id,
        reviewer_label="Valid sanitized review",
    )
    valid_result = service.apply_review_session(valid_review.id)
    assert valid_result.course_state_snapshot is not None
    active_snapshot_id = valid_result.course_state_snapshot.id

    invalid_run_id = create_myprogress_import(
        session,
        [
            myprogress_course_row(
                1,
                course_code="FIN 350",
                title="Applied Finance Eligibility Lab",
                status="IN_PROGRESS",
                term="2025SP",
            )
        ],
        validation_status="FAILED",
    )
    invalid_review = service.create_review_session(
        data_import_run_id=invalid_run_id,
        reviewer_label="Invalid sanitized review",
    )
    first_record_review = session.scalars(
        select(ImportedRecordReview)
        .where(ImportedRecordReview.review_session_id == invalid_review.id)
        .order_by(ImportedRecordReview.created_at, ImportedRecordReview.id)
    ).first()
    assert first_record_review is not None
    service.update_record_review(
        review_session_id=invalid_review.id,
        record_review_id=first_record_review.id,
        decision=ImportedRecordReviewDecision.CONFIRMED,
    )
    blocked = service.apply_review_session(invalid_review.id)
    assert blocked.course_state_snapshot is None
    active = session.scalar(
        select(CourseStateSnapshot).where(CourseStateSnapshot.is_active.is_(True))
    )
    assert active is not None
    assert active.id == active_snapshot_id


def test_sanitized_85_row_fixture_applies_deterministic_course_state_distribution(
    session: Session,
) -> None:
    content = kean_myprogress_with_85_rows_json()
    source_rows = json.loads(content)["courseRows"]
    expected_distribution = Counter(
        str(row.get("status") or "UNKNOWN") for row in source_rows if row.get("course_code")
    )
    run = DataImportApplicationService(session).create_import(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.DEGREE_AUDIT_EXPORT,
        file_name="sanitized-myprogress-85-rows.json",
        file_mime_type="application/json",
        content=content,
        source_type=SourceType.BROWSER_EXTENSION,
        source_reference="Sanitized 85-row MyProgress fixture",
    )
    service = DataReviewApplicationService(session)
    review = service.create_review_session(
        data_import_run_id=run.id,
        reviewer_label="Sanitized 85-row review",
    )
    result = service.apply_review_session(review.id)
    snapshot = result.course_state_snapshot
    assert snapshot is not None
    assert snapshot.exception_count == 1
    states = session.scalars(
        select(CourseStateRecord).where(CourseStateRecord.snapshot_id == snapshot.id)
    ).all()
    assert len(states) == 84
    actual_distribution = Counter(state.status.value for state in states)
    assert actual_distribution == expected_distribution

    by_code = {state.normalized_course_code: state for state in states}
    assert by_code["MATH 1044"].status is CourseStateStatus.NOT_STARTED
    assert by_code["MATH 1054"].status is CourseStateStatus.NOT_STARTED
    assert by_code["ENG 2403"].status is CourseStateStatus.PLANNED
    math_provenance = by_code["MATH 1044"].provenance["course_code"]
    assert isinstance(math_provenance, dict)
    assert str(math_provenance["source"]).startswith("visible table")
    assert all(
        state.student_course_attempt_id is None
        for state in states
        if state.status is CourseStateStatus.NOT_STARTED
    )
    for key, expected_status in {
        "course_history": "PARTIAL",
        "long_term_planner": "BLOCKED",
        "semester_schedule": "DEMO_ONLY",
    }.items():
        readiness = snapshot.readiness_payload[key]
        assert isinstance(readiness, dict)
        assert readiness["status"] == expected_status


def test_rejected_deferred_and_exception_rows_do_not_enter_reliable_history(
    session: Session,
) -> None:
    exception_row: dict[str, object] = {
        "requirements": "Unsupported Requirement Format",
        "status": "NEEDS_REVIEW",
        "course_title": "Ambiguous placeholder row",
        "raw_row_text": "Needs review Ambiguous placeholder row",
        "source_table_index": "1",
        "source_row_index": "4",
        "confidence": "low",
    }
    run_id = create_myprogress_import(
        session,
        [
            myprogress_course_row(
                1,
                course_code="FIN 300",
                title="Managerial Finance",
                status="COMPLETED",
                term="2024FA",
            ),
            myprogress_course_row(
                2,
                course_code="FIN 350",
                title="Applied Finance Eligibility Lab",
                status="IN_PROGRESS",
                term="2025SP",
            ),
            myprogress_course_row(
                3,
                course_code="FIN 450",
                title="Advanced Finance Capstone",
                status="NOT_STARTED",
            ),
            exception_row,
        ],
    )
    service = DataReviewApplicationService(session)
    review = service.create_review_session(
        data_import_run_id=run_id,
        reviewer_label="Decision semantics review",
    )
    service.update_record_review(
        review_session_id=review.id,
        record_review_id=select_review_record(session, review.id, "FIN 300").id,
        decision=ImportedRecordReviewDecision.REJECTED,
    )
    service.update_record_review(
        review_session_id=review.id,
        record_review_id=select_review_record(session, review.id, "FIN 350").id,
        decision=ImportedRecordReviewDecision.DEFERRED,
    )
    exception_review = session.scalar(
        select(ImportedRecordReview)
        .join(ImportedRecord, ImportedRecordReview.imported_record_id == ImportedRecord.id)
        .where(
            ImportedRecordReview.review_session_id == review.id,
            ImportedRecord.normalized_payload["raw_row_text"].as_string()
            == "Needs review Ambiguous placeholder row",
        )
    )
    assert exception_review is not None
    service.update_record_review(
        review_session_id=review.id,
        record_review_id=exception_review.id,
        decision=ImportedRecordReviewDecision.CONFIRMED,
    )

    result = service.apply_review_session(review.id)
    snapshot = result.course_state_snapshot
    assert snapshot is not None
    states = session.scalars(
        select(CourseStateRecord).where(CourseStateRecord.snapshot_id == snapshot.id)
    ).all()
    assert {state.normalized_course_code for state in states} == {"FIN 450", ""}
    exception = next(state for state in states if state.normalized_course_code == "")
    assert exception.validation_state is CourseStateValidationState.EXCEPTION
    assert exception.student_course_attempt_id is None
    assert snapshot.exception_count == 1
    assert (
        session.scalar(
            select(func.count())
            .select_from(StudentCourseAttempt)
            .where(StudentCourseAttempt.course_state_snapshot_id == snapshot.id)
        )
        == 0
    )
    by_reason = {outcome.reason_code for outcome in result.applied_records}
    assert "RECORD_REJECTED" in by_reason
    assert "RECORD_DEFERRED" in by_reason
    assert "COURSE_STATE_EXCEPTION" in by_reason
    assert "SKIPPED_UNSUPPORTED" not in by_reason


@pytest.mark.parametrize(
    ("imported_status", "expected_reason"),
    [
        ("COMPLETED", "COMPLETED_COURSE_SATISFIED"),
        ("IN_PROGRESS", "COMPLETED_COURSE_MISSING"),
        ("PLANNED", "COMPLETED_COURSE_MISSING"),
    ],
)
def test_eligibility_distinguishes_reviewed_completed_in_progress_and_planned(
    session: Session,
    imported_status: str,
    expected_reason: str,
) -> None:
    run_id = create_myprogress_import(
        session,
        [
            myprogress_course_row(
                1,
                course_code="FIN 200",
                title="Finance Foundations",
                status=imported_status,
                term="2024FA",
            )
        ],
    )
    service = DataReviewApplicationService(session)
    review = service.create_review_session(
        data_import_run_id=run_id,
        reviewer_label=f"Eligibility {imported_status} review",
    )
    result = service.apply_review_session(review.id)
    assert result.course_state_snapshot is not None

    eligibility = CourseEligibilityEngine(session).evaluate(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        course_id=seed_uuid("course:FIN-300"),
        section_id=None,
        target_term_id=seed_uuid("term:2025-spring"),
        mode=EligibilityMode.PROJECTED,
    )
    reason_codes = {evaluation.reason_code for evaluation in eligibility.expression_evaluations}
    assert expected_reason in reason_codes
    if imported_status in {"IN_PROGRESS", "PLANNED"}:
        assert "COMPLETED_COURSE_IN_PROGRESS" not in reason_codes
