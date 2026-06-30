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
    DataApplicationRun,
    DataApplicationStatus,
    DataImportReviewStatus,
    DataImportType,
    ImportedRecord,
    ImportedRecordReview,
    ImportedRecordReviewDecision,
    SourceType,
    StudentCourseAttempt,
)
from app.seed_dev import seed_mock_data, seed_uuid
from app.services.data_imports.engine import DataImportApplicationService
from app.services.data_review.engine import DataReviewApplicationService


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
