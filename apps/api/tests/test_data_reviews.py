import csv
import io
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

from app.api.v1.academic import course_response
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.academic import (
    AcademicProgram,
    AppliedImportAction,
    AppliedImportedRecord,
    AppliedImportStatus,
    Course,
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
    ImportMappingCandidate,
    ImportTargetEntityType,
    ProgramVersion,
    Section,
    SectionMeeting,
    SectionModality,
    SectionStatus,
    SourceType,
    StudentAcademicProgram,
    StudentCourseAttempt,
    StudentCourseAttemptStatus,
)
from app.seed_dev import seed_mock_data, seed_uuid
from app.services.course_eligibility.engine import CourseEligibilityEngine
from app.services.course_state.engine import (
    active_course_state_snapshot,
    effective_student_course_attempts,
)
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


def section_csv(section_code: str = "987", course_code: str = "FIN 300") -> str:
    meetings = [
        {
            "component": "LECTURE",
            "days": "MONDAY,WEDNESDAY",
            "start_time": "09:00",
            "end_time": "10:15",
            "location": "Main Hall",
            "room": "101",
            "modality": "IN_PERSON",
            "is_async": False,
            "is_tba": False,
            "is_arranged": False,
        }
    ]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "term_code",
            "course_code",
            "course_title",
            "section_code",
            "campus",
            "component",
            "credits",
            "modality",
            "status",
            "meeting_days",
            "meeting_time",
            "location",
            "instructor_display",
            "meetings_json",
            "validation_state",
            "completeness",
        ]
    )
    writer.writerow(
        [
            "2024FA",
            course_code,
            "Mock Managerial Finance",
            section_code,
            "MAIN",
            "LECTURE",
            "3",
            "IN_PERSON",
            "OPEN",
            "MW",
            "9:00 AM-10:15 AM",
            "Main Hall 101",
            "Imported Instructor",
            json.dumps(meetings, separators=(",", ":")),
            "AUTO_VERIFIED",
            "COMPLETE",
        ]
    )
    return output.getvalue()


def create_section_import(
    session: Session,
    section_code: str = "987",
    course_code: str = "FIN 300",
) -> UUID:
    run = DataImportApplicationService(session).create_import(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.SECTION_SCHEDULE,
        file_name="visible-section-schedule.csv",
        file_mime_type="text/csv",
        content=section_csv(section_code, course_code),
        source_type=SourceType.BROWSER_EXTENSION,
        source_reference="Visible section schedule fixture",
    )
    return run.id


def catalog_json(
    course_code: str = "ACCT 2200",
    *,
    title: str = "Financial Accounting",
    credits: str = "3",
    description: str = "Reviewed source description.",
) -> str:
    return json.dumps(
        {
            "courses": [
                {
                    "course_code": course_code,
                    "course_title": title,
                    "credits": credits,
                    "description": description,
                    "raw_requisites": "Minimum grade of C required.",
                    "rule_review_status": "MANUAL_CONFIRMATION_REQUIRED",
                }
            ]
        }
    )


def create_catalog_import(
    session: Session,
    course_code: str = "ACCT 2200",
    *,
    title: str = "Financial Accounting",
    credits: str = "3",
    description: str = "Reviewed source description.",
    source_reference: str = "https://portal.example.test/catalog/search?keyword=ACCT",
) -> UUID:
    run = DataImportApplicationService(session).create_import(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.COURSE_CATALOG,
        file_name="visible-reviewed-catalog.json",
        file_mime_type="application/json",
        content=catalog_json(
            course_code,
            title=title,
            credits=credits,
            description=description,
        ),
        source_type=SourceType.BROWSER_EXTENSION,
        source_reference=source_reference,
    )
    return run.id


def create_batch_catalog_import(
    session: Session,
    courses: list[dict[str, str]],
    *,
    extraction_warnings: list[dict[str, str]] | None = None,
) -> UUID:
    run = DataImportApplicationService(session).create_import(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.COURSE_CATALOG,
        file_name="kean-batch-course-catalog.json",
        file_mime_type="application/json",
        content=json.dumps({"courses": courses}),
        source_type=SourceType.BROWSER_EXTENSION,
        source_reference=(
            "KEAN_STUDENT_PORTAL browser extension import: "
            "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses/SearchResult"
        ),
        extraction_warnings=extraction_warnings,
    )
    return run.id


def batch_catalog_course(
    course_code: str,
    title: str,
    *,
    credits: str = "3",
    description: str = "NOT_PROVIDED",
    raw_requisites: str = "NOT_PROVIDED",
    rule_review_status: str = "NO_REQUISITES_VISIBLE",
    source_page: str = (
        "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses/SearchResult"
    ),
) -> dict[str, str]:
    return {
        "course_code": course_code,
        "normalized_code": course_code,
        "raw_visible_course_code": course_code,
        "course_title": title,
        "raw_visible_title": title,
        "credits": credits,
        "department": "NOT_PROVIDED",
        "course_level": "NOT_PROVIDED",
        "description": description,
        "prerequisites": "NOT_PROVIDED",
        "corequisites": "NOT_PROVIDED",
        "minimum_grade": "NOT_PROVIDED",
        "standing_requirements": "NOT_PROVIDED",
        "restrictions": "NOT_PROVIDED",
        "raw_requisites": raw_requisites,
        "rule_review_status": rule_review_status,
        "source_page": source_page,
        "source_subject": course_code.split()[0],
        "source_page_number": "1",
        "capture_timestamp": "2026-08-26T02:00:00+00:00",
        "source_label": "Visible course catalog cards",
    }


def test_last_confirmed_record_marks_review_ready_when_autoflush_is_disabled(
    session: Session,
) -> None:
    session.autoflush = False
    run_id = create_catalog_import(session)
    service = DataReviewApplicationService(session)
    review = service.create_review_session(
        data_import_run_id=run_id,
        reviewer_label="Production-session review status regression",
    )
    record_review = session.scalar(
        select(ImportedRecordReview).where(ImportedRecordReview.review_session_id == review.id)
    )
    assert record_review is not None

    service.update_record_review(
        review_session_id=review.id,
        record_review_id=record_review.id,
        decision=ImportedRecordReviewDecision.CONFIRMED,
    )

    session.refresh(review)
    assert review.status is DataImportReviewStatus.READY_TO_APPLY


def test_reviewed_catalog_provisions_one_course_and_remaps_prior_sources(
    session: Session,
) -> None:
    program_version_count_before = count_rows(session, ProgramVersion)
    section_run_id = create_section_import(session, "01", "ACCT 2200")
    myprogress_run_id = create_myprogress_import(
        session,
        [
            myprogress_course_row(
                1,
                course_code="ACCT 2200",
                title="Financial Accounting",
                status="PLANNED",
                term="2024FA",
            )
        ],
    )
    review_service = DataReviewApplicationService(session)
    prior_section_review = review_service.create_review_session(
        data_import_run_id=section_run_id,
        reviewer_label="Unresolved section review before Catalog",
    )
    prior_section_record_review = session.scalar(
        select(ImportedRecordReview).where(
            ImportedRecordReview.review_session_id == prior_section_review.id
        )
    )
    assert prior_section_record_review is not None
    assert prior_section_record_review.requires_advisor_confirmation is True
    assert prior_section_record_review.selected_mapping_candidate_id is not None
    prior_section_candidate_id = prior_section_record_review.selected_mapping_candidate_id
    prior_myprogress_review = review_service.create_review_session(
        data_import_run_id=myprogress_run_id,
        reviewer_label="Unresolved MyProgress review before Catalog",
    )
    prior_myprogress_record_review = session.scalar(
        select(ImportedRecordReview).where(
            ImportedRecordReview.review_session_id == prior_myprogress_review.id,
            ImportedRecordReview.selected_mapping_candidate_id.is_not(None),
        )
    )
    assert prior_myprogress_record_review is not None
    assert prior_myprogress_record_review.selected_mapping_candidate_id is not None
    prior_myprogress_candidate_id = prior_myprogress_record_review.selected_mapping_candidate_id
    prior_myprogress_candidate = session.get(
        ImportMappingCandidate,
        prior_myprogress_candidate_id,
    )
    assert prior_myprogress_candidate is not None
    assert prior_myprogress_candidate.target_entity_type is ImportTargetEntityType.UNKNOWN
    assert prior_myprogress_candidate.target_entity_id is None

    catalog_run_id = create_catalog_import(session)
    catalog_record = session.scalar(
        select(ImportedRecord).where(ImportedRecord.data_import_run_id == catalog_run_id)
    )
    assert catalog_record is not None
    provisioning_candidate = session.scalar(
        select(ImportMappingCandidate).where(
            ImportMappingCandidate.imported_record_id == catalog_record.id,
            ImportMappingCandidate.is_selected.is_(True),
        )
    )
    assert provisioning_candidate is not None
    assert provisioning_candidate.target_entity_type is ImportTargetEntityType.COURSE
    assert provisioning_candidate.target_entity_id is None
    assert provisioning_candidate.reason_code == "REVIEWED_CATALOG_COURSE_PROVISIONING"

    catalog_review = review_service.create_review_session(
        data_import_run_id=catalog_run_id,
        reviewer_label="Reviewed visible Catalog",
    )
    catalog_record_review = session.scalar(
        select(ImportedRecordReview).where(
            ImportedRecordReview.review_session_id == catalog_review.id
        )
    )
    assert catalog_record_review is not None
    review_service.update_record_review(
        review_session_id=catalog_review.id,
        record_review_id=catalog_record_review.id,
        decision=ImportedRecordReviewDecision.CONFIRMED,
    )

    dry_run = review_service.apply_review_session(catalog_review.id, dry_run=True)
    assert dry_run.applied_records[0].reason_code == "WOULD_CREATE_IMPORTED_COURSE"
    assert (
        session.scalar(
            select(func.count())
            .select_from(Course)
            .where(
                Course.institution_id == seed_uuid("institution:mock-university"),
                Course.subject_code == "ACCT",
                Course.course_number == "2200",
            )
        )
        == 0
    )

    applied = review_service.apply_review_session(catalog_review.id)
    course = session.scalar(
        select(Course).where(
            Course.institution_id == seed_uuid("institution:mock-university"),
            Course.subject_code == "ACCT",
            Course.course_number == "2200",
        )
    )
    assert course is not None
    assert applied.applied_records[0].target_entity_id == course.id
    assert applied.applied_records[0].reason_code == "CREATED_IMPORTED_COURSE"
    assert course.title == "Financial Accounting"
    assert course.credits_min == course.credits_max == 3
    assert course.course_level == 0
    assert course.course_level_verified is False
    assert course.repeatable is False
    assert course.repeatable_verified is False
    assert course.source_confidence == "reviewed_catalog_partial"
    public_course = course_response(course)
    assert public_course.course_level is None
    assert public_course.repeatable is None
    assert course.source_type is SourceType.BROWSER_EXTENSION
    assert course.is_official is False
    assert course.source_reference == (
        "https://portal.example.test/catalog/search?keyword=ACCT#course=ACCT%202200"
    )
    assert count_rows(session, ProgramVersion) == program_version_count_before
    session.refresh(provisioning_candidate)
    assert provisioning_candidate.target_entity_id is None
    assert provisioning_candidate.is_selected is False

    prior_records = session.scalars(
        select(ImportedRecord)
        .where(
            ImportedRecord.data_import_run_id.in_([section_run_id, myprogress_run_id]),
        )
        .order_by(ImportedRecord.data_import_run_id, ImportedRecord.row_number)
    ).all()
    course_records = [
        record
        for record in prior_records
        if record.normalized_payload.get("course_code") == "ACCT 2200"
    ]
    assert len(course_records) == 2
    section_mapping: ImportMappingCandidate | None = None
    for record in course_records:
        mapping = session.scalar(
            select(ImportMappingCandidate).where(
                ImportMappingCandidate.imported_record_id == record.id,
                ImportMappingCandidate.target_entity_type == ImportTargetEntityType.COURSE,
                ImportMappingCandidate.target_entity_id == course.id,
                ImportMappingCandidate.is_selected.is_(True),
            )
        )
        assert mapping is not None
        assert mapping.reason_code == "REVIEWED_CATALOG_COURSE_IDENTITY"
        if record.data_import_run_id == section_run_id:
            section_mapping = mapping
    assert section_mapping is not None
    session.refresh(prior_section_record_review)
    assert prior_section_record_review.selected_mapping_candidate_id == prior_section_candidate_id
    assert prior_section_record_review.requires_advisor_confirmation is True
    session.refresh(prior_myprogress_candidate)
    assert prior_myprogress_candidate.target_entity_type is ImportTargetEntityType.UNKNOWN
    assert prior_myprogress_candidate.target_entity_id is None
    session.refresh(prior_myprogress_record_review)
    assert (
        prior_myprogress_record_review.selected_mapping_candidate_id
        == prior_myprogress_candidate_id
    )

    review_service.update_record_review(
        review_session_id=prior_section_review.id,
        record_review_id=prior_section_record_review.id,
        decision=ImportedRecordReviewDecision.CONFIRMED,
        selected_mapping_candidate_id=section_mapping.id,
    )
    section_apply = review_service.apply_review_session(prior_section_review.id)
    section = session.scalar(
        select(Section).where(
            Section.course_id == course.id,
            Section.section_code == "01",
        )
    )
    assert section is not None
    assert section_apply.applied_records[0].target_entity_id == section.id
    assert section.external_reference is None

    repeated_catalog_run_id = create_catalog_import(session)
    repeated_review = review_service.create_review_session(
        data_import_run_id=repeated_catalog_run_id,
        reviewer_label="Repeated reviewed visible Catalog",
    )
    repeated_record_review = session.scalar(
        select(ImportedRecordReview).where(
            ImportedRecordReview.review_session_id == repeated_review.id
        )
    )
    assert repeated_record_review is not None
    review_service.update_record_review(
        review_session_id=repeated_review.id,
        record_review_id=repeated_record_review.id,
        decision=ImportedRecordReviewDecision.CONFIRMED,
    )
    repeated_apply = review_service.apply_review_session(repeated_review.id)
    assert repeated_apply.applied_records[0].reason_code == "UPDATED_IMPORTED_COURSE"
    assert repeated_apply.applied_records[0].target_entity_id == course.id
    assert (
        session.scalar(
            select(func.count())
            .select_from(Course)
            .where(
                Course.institution_id == seed_uuid("institution:mock-university"),
                Course.subject_code == "ACCT",
                Course.course_number == "2200",
            )
        )
        == 1
    )


def test_reviewed_catalog_conflict_does_not_overwrite_existing_course(
    session: Session,
) -> None:
    service = DataReviewApplicationService(session)
    first_run_id = create_catalog_import(session)
    first_review = service.create_review_session(
        data_import_run_id=first_run_id,
        reviewer_label="Review first Catalog evidence",
    )
    first_record_review = session.scalar(
        select(ImportedRecordReview).where(
            ImportedRecordReview.review_session_id == first_review.id
        )
    )
    assert first_record_review is not None
    service.update_record_review(
        review_session_id=first_review.id,
        record_review_id=first_record_review.id,
        decision=ImportedRecordReviewDecision.CONFIRMED,
    )
    service.apply_review_session(first_review.id)
    course = session.scalar(
        select(Course).where(
            Course.institution_id == seed_uuid("institution:mock-university"),
            Course.subject_code == "ACCT",
            Course.course_number == "2200",
        )
    )
    assert course is not None
    original_id = course.id
    original_reference = course.source_reference

    conflicting_run_id = create_catalog_import(
        session,
        title="Conflicting Accounting Title",
        credits="4",
        description="Conflicting source description.",
        source_reference="https://portal.example.test/catalog/other-version",
    )
    conflicting_review = service.create_review_session(
        data_import_run_id=conflicting_run_id,
        reviewer_label="Review conflicting Catalog evidence",
    )
    conflicting_record_review = session.scalar(
        select(ImportedRecordReview).where(
            ImportedRecordReview.review_session_id == conflicting_review.id
        )
    )
    assert conflicting_record_review is not None
    service.update_record_review(
        review_session_id=conflicting_review.id,
        record_review_id=conflicting_record_review.id,
        decision=ImportedRecordReviewDecision.CONFIRMED,
    )

    dry_run = service.apply_review_session(conflicting_review.id, dry_run=True)
    assert dry_run.applied_records[0].status is AppliedImportStatus.SKIPPED
    assert dry_run.applied_records[0].reason_code == "CONFLICT_CATALOG_COURSE_EVIDENCE"
    applied = service.apply_review_session(conflicting_review.id)
    assert applied.applied_records[0].status is AppliedImportStatus.SKIPPED
    assert applied.applied_records[0].reason_code == "CONFLICT_CATALOG_COURSE_EVIDENCE"
    session.refresh(course)
    assert course.id == original_id
    assert course.title == "Financial Accounting"
    assert course.credits_min == course.credits_max == 3
    assert course.description == "Reviewed source description."
    assert course.source_reference == original_reference
    assert (
        session.scalar(
            select(func.count())
            .select_from(Course)
            .where(
                Course.institution_id == seed_uuid("institution:mock-university"),
                Course.subject_code == "ACCT",
                Course.course_number == "2200",
            )
        )
        == 1
    )


def test_catalog_batch_processes_safe_fields_after_dry_run_and_recounts_myprogress(
    session: Session,
) -> None:
    myprogress_run_id = create_myprogress_import(
        session,
        [
            myprogress_course_row(
                1,
                course_code="ACCT 2200",
                title="Financial Accounting",
                status="PLANNED",
                term="2026FA",
            ),
            myprogress_course_row(
                2,
                course_code="MATH 1044",
                title="Precalculus for Business",
                status="NOT_STARTED",
                term="",
            ),
        ],
    )
    batch_run_id = create_batch_catalog_import(
        session,
        [
            batch_catalog_course(
                "ACCT 2200",
                "Financial Accounting",
                description="Visible source description.",
                raw_requisites="Minimum grade of C required.",
                rule_review_status="MANUAL_CONFIRMATION_REQUIRED",
            )
        ],
    )

    result = DataReviewApplicationService(session).process_catalog_batch_import(batch_run_id)

    assert result.status == "APPLIED"
    assert result.confirmed_record_count == 1
    assert result.blocked_record_count == 0
    assert result.dry_run is not None
    assert [item.reason_code for item in result.dry_run.applied_records] == [
        "WOULD_CREATE_IMPORTED_COURSE"
    ]
    assert result.application is not None
    assert [item.reason_code for item in result.application.applied_records] == [
        "CREATED_IMPORTED_COURSE"
    ]
    assert result.myprogress_run_id == myprogress_run_id
    assert result.myprogress_mapped_count == 1
    assert result.myprogress_unmatched_count == 1
    assert result.provider_actions_written == "NO"
    course = session.scalar(
        select(Course).where(
            Course.institution_id == seed_uuid("institution:mock-university"),
            Course.subject_code == "ACCT",
            Course.course_number == "2200",
        )
    )
    assert course is not None
    assert course.is_official is False
    assert course.source_type is SourceType.BROWSER_EXTENSION
    assert course.course_level_verified is False
    review_record = session.scalar(
        select(ImportedRecordReview).where(
            ImportedRecordReview.review_session_id == result.review_session.id
        )
    )
    assert review_record is not None
    assert review_record.decision is ImportedRecordReviewDecision.CONFIRMED
    assert review_record.requires_advisor_confirmation is True
    assert "requisite policy remains raw" in (review_record.review_note or "")

    repeated = DataReviewApplicationService(session).process_catalog_batch_import(batch_run_id)
    assert repeated.status == "APPLIED"
    assert repeated.already_processed is True
    assert (
        session.scalar(
            select(func.count())
            .select_from(Course)
            .where(
                Course.institution_id == seed_uuid("institution:mock-university"),
                Course.subject_code == "ACCT",
                Course.course_number == "2200",
            )
        )
        == 1
    )


def test_catalog_batch_replay_does_not_upgrade_an_existing_failed_application(
    session: Session,
) -> None:
    run_id = create_batch_catalog_import(
        session,
        [batch_catalog_course("ACCT 2200", "Financial Accounting")],
    )
    first = DataReviewApplicationService(session).process_catalog_batch_import(run_id)
    assert first.status == "APPLIED"
    assert first.application is not None
    assert first.application.application is not None
    applied_record = session.scalar(
        select(AppliedImportedRecord).where(
            AppliedImportedRecord.data_application_run_id == first.application.application.id
        )
    )
    assert applied_record is not None
    applied_record.status = AppliedImportStatus.FAILED
    applied_record.reason_code = "SANITIZED_EXISTING_APPLICATION_FAILURE"
    first.review_session.status = DataImportReviewStatus.APPLIED_WITH_WARNINGS
    session.commit()

    repeated = DataReviewApplicationService(session).process_catalog_batch_import(run_id)

    assert repeated.status == "BLOCKED"
    assert repeated.already_processed is True
    assert repeated.blocked_record_count == 1
    assert repeated.reason_codes == ["SANITIZED_EXISTING_APPLICATION_FAILURE"]


@pytest.mark.parametrize(
    ("warning_code", "expected_reason"),
    [
        ("EXTRACTION_LIMIT_REACHED", "BATCH_CATALOG_TRUNCATED_PAGE"),
        ("BATCH_CATALOG_RATE_LIMIT", "BATCH_CATALOG_RATE_LIMIT"),
        ("NO_IMPORTABLE_ROWS", "BATCH_CATALOG_PARSER_DRIFT"),
    ],
)
def test_catalog_batch_fails_closed_before_apply_for_unsafe_capture(
    session: Session,
    warning_code: str,
    expected_reason: str,
) -> None:
    run_id = create_batch_catalog_import(
        session,
        [batch_catalog_course("ACCT 2200", "Financial Accounting")],
        extraction_warnings=[
            {
                "code": warning_code,
                "severity": "WARNING",
                "message": "Sanitized unsafe capture fixture.",
            }
        ],
    )

    result = DataReviewApplicationService(session).process_catalog_batch_import(run_id)

    assert result.status == "BLOCKED"
    assert result.application is None
    assert result.confirmed_record_count == 0
    assert result.blocked_record_count == 1
    assert expected_reason in result.reason_codes
    assert (
        session.scalar(
            select(func.count())
            .select_from(Course)
            .where(
                Course.institution_id == seed_uuid("institution:mock-university"),
                Course.subject_code == "ACCT",
                Course.course_number == "2200",
            )
        )
        == 0
    )


def test_catalog_batch_conflicting_existing_course_stops_after_dry_run(
    session: Session,
) -> None:
    first_run_id = create_batch_catalog_import(
        session,
        [batch_catalog_course("ACCT 2200", "Financial Accounting")],
    )
    first = DataReviewApplicationService(session).process_catalog_batch_import(first_run_id)
    assert first.status == "APPLIED"

    conflict_run_id = create_batch_catalog_import(
        session,
        [batch_catalog_course("ACCT 2200", "Conflicting Accounting", credits="4")],
    )
    conflict = DataReviewApplicationService(session).process_catalog_batch_import(conflict_run_id)

    assert conflict.status == "BLOCKED"
    assert conflict.application is None
    assert "CONFLICT_CATALOG_COURSE_EVIDENCE" in conflict.reason_codes
    course = session.scalar(
        select(Course).where(
            Course.institution_id == seed_uuid("institution:mock-university"),
            Course.subject_code == "ACCT",
            Course.course_number == "2200",
        )
    )
    assert course is not None
    assert course.title == "Financial Accounting"
    assert course.credits_min == course.credits_max == 3


def test_catalog_batch_blocks_malformed_provenance_and_missing_required_fields(
    session: Session,
) -> None:
    malformed = batch_catalog_course("ACCT 2200", "Financial Accounting")
    malformed["raw_visible_title"] = ""
    malformed["source_page"] = "https://portal.example.test/catalog"
    run_id = create_batch_catalog_import(session, [malformed])

    result = DataReviewApplicationService(session).process_catalog_batch_import(run_id)

    assert result.status == "BLOCKED"
    assert result.application is None
    assert result.reason_codes == ["BATCH_CATALOG_PROVENANCE_INVALID"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.update(raw_visible_course_code="FIN 9999"),
        lambda payload: payload.pop("restrictions"),
    ],
)
def test_catalog_batch_requires_exact_raw_identity_and_explicit_optional_fields(
    session: Session,
    mutate: Any,
) -> None:
    payload = batch_catalog_course("ACCT 2200", "Financial Accounting")
    mutate(payload)
    run_id = create_batch_catalog_import(session, [payload])

    result = DataReviewApplicationService(session).process_catalog_batch_import(run_id)

    assert result.status == "BLOCKED"
    assert result.application is None
    assert result.reason_codes == ["BATCH_CATALOG_PROVENANCE_INVALID"]


def test_catalog_batch_accepts_observed_public_catalog_result_path(
    session: Session,
) -> None:
    run_id = create_batch_catalog_import(
        session,
        [
            batch_catalog_course(
                "ACCT 2200",
                "Financial Accounting",
                source_page=(
                    "https://kean-ss.colleague.elluciancloud.com/Student/Courses/SearchResult"
                ),
            )
        ],
    )

    result = DataReviewApplicationService(session).process_catalog_batch_import(run_id)

    assert result.status == "APPLIED"
    assert result.application is not None
    assert result.provider_actions_written == "NO"
    course = session.scalar(
        select(Course).where(
            Course.institution_id == seed_uuid("institution:mock-university"),
            Course.subject_code == "ACCT",
            Course.course_number == "2200",
        )
    )
    assert course is not None
    assert course.description is None


def test_catalog_batch_process_remaps_myprogress_without_creating_program_version(
    session: Session,
) -> None:
    myprogress_run_id = create_myprogress_import(
        session,
        [
            myprogress_course_row(
                1,
                course_code="ACCT 2200",
                title="Financial Accounting",
                status="PLANNED",
                term="2024FA",
            )
        ],
    )
    program_version_count_before = count_rows(session, ProgramVersion)
    catalog_run_id = create_batch_catalog_import(
        session,
        [batch_catalog_course("ACCT 2200", "Financial Accounting")],
    )

    result = DataReviewApplicationService(session).process_catalog_batch_import(catalog_run_id)

    assert result.status == "APPLIED"
    assert result.processing_stages_completed[-1] == "MYPROGRESS_REMAP"
    assert result.myprogress_total_count == 1
    assert result.myprogress_mapped_before_count == 0
    assert result.myprogress_mapped_count == 1
    assert result.myprogress_unmatched_count == 0
    assert result.myprogress_remap_executed is True
    myprogress_record = session.scalar(
        select(ImportedRecord).where(
            ImportedRecord.data_import_run_id == myprogress_run_id,
            ImportedRecord.normalized_payload["course_code"].as_string() == "ACCT 2200",
        )
    )
    assert myprogress_record is not None
    selected_mapping = session.scalar(
        select(ImportMappingCandidate).where(
            ImportMappingCandidate.imported_record_id == myprogress_record.id,
            ImportMappingCandidate.is_selected.is_(True),
        )
    )
    assert selected_mapping is not None
    assert selected_mapping.reason_code == "REVIEWED_CATALOG_COURSE_IDENTITY"
    assert count_rows(session, ProgramVersion) == program_version_count_before
    assert result.provider_actions_written == "NO"


def test_catalog_batch_process_api_returns_local_gate_counts(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/data-imports",
        json={
            "student_profile_id": str(seed_uuid("student-profile:mock-student")),
            "import_type": "COURSE_CATALOG",
            "file_name": "kean-batch-course-catalog.json",
            "file_mime_type": "application/json",
            "content": json.dumps(
                {"courses": [batch_catalog_course("ACCT 2200", "Financial Accounting")]}
            ),
            "source_type": "BROWSER_EXTENSION",
            "source_reference": (
                "KEAN_STUDENT_PORTAL browser extension import: "
                "https://kean-ss.colleague.elluciancloud.com/Student/Student/Courses/SearchResult"
            ),
            "page_type": "KEAN_COURSE_CATALOG_PAGE",
            "extracted_record_count": 1,
            "visible_row_count": 1,
            "academic_field_count": 22,
            "warnings": [],
            "diagnostics": {"bounded": False},
            "bounded": False,
            "truncated": False,
        },
    )
    assert create_response.status_code == 201
    run_id = create_response.json()["id"]

    process_response = client.post(f"/api/v1/data-imports/{run_id}/catalog-batch-process")

    assert process_response.status_code == 200
    payload = process_response.json()
    assert {
        key: payload[key]
        for key in (
            "status",
            "confirmed_record_count",
            "blocked_record_count",
            "provider_actions_written",
        )
    } == {
        "status": "APPLIED",
        "confirmed_record_count": 1,
        "blocked_record_count": 0,
        "provider_actions_written": "NO",
    }
    assert payload["dry_run_result"]["dry_run"] is True
    assert payload["application_result"]["dry_run"] is False
    assert payload["processing_stages_completed"] == [
        "LOCAL_STAGING",
        "LOCAL_VALIDATION",
        "LOCAL_REVIEW",
        "LOCAL_DRY_RUN",
        "LOCAL_APPLY",
        "MYPROGRESS_REMAP",
    ]
    assert payload["staged_record_count"] == 1
    assert payload["review_valid_count"] == 1
    assert payload["review_warning_count"] == 0
    assert payload["applied_record_count"] == 1
    assert payload["myprogress_total_count"] == 0
    assert payload["myprogress_mapped_before_count"] == 0
    assert payload["myprogress_mapped_count"] == 0
    assert payload["myprogress_unmatched_count"] == 0
    assert payload["myprogress_remap_executed"] is True


def test_section_review_apply_is_dry_run_safe_non_official_and_idempotent(
    session: Session,
) -> None:
    run_id = create_section_import(session)
    sections_before = count_rows(session, Section)
    service = DataReviewApplicationService(session)
    review = service.create_review_session(
        data_import_run_id=run_id,
        reviewer_label="Visible schedule self-review",
    )
    record_review = session.scalar(
        select(ImportedRecordReview).where(
            ImportedRecordReview.review_session_id == review.id,
        )
    )
    assert record_review is not None
    service.update_record_review(
        review_session_id=review.id,
        record_review_id=record_review.id,
        decision=ImportedRecordReviewDecision.CONFIRMED,
    )

    dry_run = service.apply_review_session(review.id, dry_run=True)
    assert dry_run.applied_records[0].action is AppliedImportAction.CREATED
    assert dry_run.applied_records[0].reason_code == "WOULD_CREATE_IMPORTED_SECTION"
    assert count_rows(session, Section) == sections_before

    applied = service.apply_review_session(review.id)
    assert applied.application is not None
    section = session.scalar(
        select(Section).where(
            Section.course_id == seed_uuid("course:FIN-300"),
            Section.section_code == "987",
        )
    )
    assert section is not None
    assert section.is_official is False
    assert section.source_type is SourceType.BROWSER_EXTENSION
    assert section.capacity is None
    assert section.available_seats is None
    meetings = session.scalars(
        select(SectionMeeting).where(SectionMeeting.section_id == section.id)
    ).all()
    assert len(meetings) == 2
    assert {
        meeting.day_of_week.name for meeting in meetings if meeting.day_of_week is not None
    } == {"MONDAY", "WEDNESDAY"}
    assert all(meeting.is_official is False for meeting in meetings)

    duplicate = service.apply_review_session(review.id)
    assert duplicate.application is not None
    assert count_rows(session, Section) == sections_before + 1
    assert (
        session.scalar(
            select(func.count())
            .select_from(SectionMeeting)
            .where(
                SectionMeeting.section_id == section.id,
            )
        )
        == 2
    )


def test_repeated_section_capture_updates_one_section_without_duplicate_meetings(
    session: Session,
) -> None:
    sections_before = count_rows(session, Section)
    service = DataReviewApplicationService(session)
    target_section_id: UUID | None = None

    for capture_number in (1, 2):
        run_id = create_section_import(session, "IDEMPOTENT")
        review = service.create_review_session(
            data_import_run_id=run_id,
            reviewer_label=f"Repeated visible schedule review {capture_number}",
        )
        record_review = session.scalar(
            select(ImportedRecordReview).where(
                ImportedRecordReview.review_session_id == review.id,
            )
        )
        assert record_review is not None
        service.update_record_review(
            review_session_id=review.id,
            record_review_id=record_review.id,
            decision=ImportedRecordReviewDecision.CONFIRMED,
        )
        applied = service.apply_review_session(review.id)
        assert applied.applied_records[0].action is (
            AppliedImportAction.CREATED if capture_number == 1 else AppliedImportAction.UPDATED
        )
        if target_section_id is None:
            target_section_id = applied.applied_records[0].target_entity_id
        else:
            assert applied.applied_records[0].target_entity_id == target_section_id

    assert target_section_id is not None
    assert count_rows(session, Section) == sections_before + 1
    section = session.get(Section, target_section_id)
    assert section is not None
    assert section.source_reference == (
        "Visible section schedule fixture#section=2024FA%7CFIN%20300%7CIDEMPOTENT"
    )
    assert (
        session.scalar(
            select(func.count())
            .select_from(SectionMeeting)
            .where(SectionMeeting.section_id == target_section_id)
        )
        == 2
    )


def test_section_apply_does_not_overwrite_official_section(session: Session) -> None:
    official = Section(
        id=seed_uuid("section:official-import-conflict"),
        institution_id=seed_uuid("institution:mock-university"),
        course_id=seed_uuid("course:FIN-300"),
        term_id=seed_uuid("term:2024-fall"),
        campus_id=seed_uuid("campus:mock-main"),
        section_code="CONFLICT",
        status=SectionStatus.OPEN,
        modality=SectionModality.IN_PERSON,
        is_official=True,
        source_type=SourceType.OFFICIAL,
        source_reference="Reviewed school catalog fixture",
    )
    session.add(official)
    session.commit()

    run_id = create_section_import(session, "CONFLICT")
    service = DataReviewApplicationService(session)
    review = service.create_review_session(
        data_import_run_id=run_id,
        reviewer_label="Visible schedule conflict review",
    )
    record_review = session.scalar(
        select(ImportedRecordReview).where(
            ImportedRecordReview.review_session_id == review.id,
        )
    )
    assert record_review is not None
    service.update_record_review(
        review_session_id=review.id,
        record_review_id=record_review.id,
        decision=ImportedRecordReviewDecision.CONFIRMED,
    )
    applied = service.apply_review_session(review.id)
    assert applied.applied_records[0].reason_code == "CONFLICT_OFFICIAL_OR_MOCK_TARGET"
    assert session.get(Section, official.id) is not None


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


def confirm_all_review_records(session: Session, review_id: UUID) -> None:
    service = DataReviewApplicationService(session)
    records = session.scalars(
        select(ImportedRecordReview)
        .where(ImportedRecordReview.review_session_id == review_id)
        .order_by(ImportedRecordReview.created_at, ImportedRecordReview.id)
    ).all()
    for record in records:
        service.update_record_review(
            review_session_id=review_id,
            record_review_id=record.id,
            decision=ImportedRecordReviewDecision.CONFIRMED,
        )


def mark_finance_program_identity_as_reviewed(session: Session) -> None:
    program = session.get(AcademicProgram, seed_uuid("program:bs-finance"))
    version = session.get(ProgramVersion, seed_uuid("program-version:bs-finance-2024"))
    assignment = session.get(
        StudentAcademicProgram,
        seed_uuid("student-academic-program:mock-student-bs-finance"),
    )
    assert program is not None
    assert version is not None
    assert assignment is not None
    program.name = "Finance, BS"
    for record, evidence_label in (
        (program, "academic program"),
        (version, "program version"),
        (assignment, "student program assignment"),
    ):
        record.source_type = SourceType.BROWSER_EXTENSION
        record.source_reference = f"Sanitized reviewed {evidence_label} evidence"
        record.source_confidence = "reviewed"
    session.commit()


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


def test_repeated_transcript_capture_does_not_duplicate_course_attempt(
    session: Session,
) -> None:
    attempts_before = count_rows(session, StudentCourseAttempt)
    service = DataReviewApplicationService(session)
    second_reason_codes: set[str] = set()

    for capture_number in (1, 2):
        run_id = create_import(session)
        review = service.create_review_session(
            data_import_run_id=run_id,
            reviewer_label=f"Repeated transcript review {capture_number}",
        )
        fin_300_review = select_review_record(session, review.id, "FIN 300")
        service.update_record_review(
            review_session_id=review.id,
            record_review_id=fin_300_review.id,
            decision=ImportedRecordReviewDecision.CONFIRMED,
        )
        result = service.apply_review_session(review.id)
        if capture_number == 2:
            second_reason_codes = {outcome.reason_code for outcome in result.applied_records}

    assert count_rows(session, StudentCourseAttempt) == attempts_before + 1
    assert "DUPLICATE_COURSE_ATTEMPT" in second_reason_codes


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
    review_records = client.get(
        f"/api/v1/data-import-reviews/{review_response.json()['id']}/records"
    )
    assert review_records.status_code == 200
    for record in review_records.json():
        confirm_response = client.patch(
            f"/api/v1/data-import-reviews/{review_response.json()['id']}/records/{record['id']}",
            json={"decision": "CONFIRMED"},
        )
        assert confirm_response.status_code == 200
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
    confirm_all_review_records(session, review.id)

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
    requirement = snapshot.requirement_summary[0]
    assert isinstance(requirement, dict)
    assert requirement["name"] == "Finance Requirements"
    assert requirement["review_state"] == "CONFIRMED"
    assert requirement["requires_manual_confirmation"] is False
    provenance = requirement["provenance"]
    assert isinstance(provenance, dict)
    assert provenance["source"] == "BROWSER_EXTENSION"
    assert provenance["source_reference"] == (
        "Sanitized MyProgress course-state application fixture"
    )
    assert provenance["capture_time"]
    assert provenance["program_context"]["programName"] == "Finance, BS"
    assert provenance["normalized_requirement"]["name"] == "Finance Requirements"
    assert provenance["evidence_reference"].startswith("data-import://")
    assert provenance["confidence"] == "high"
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


def test_myprogress_separates_verified_program_from_unknown_catalog_version(
    session: Session,
) -> None:
    mark_finance_program_identity_as_reviewed(session)
    payload = json.loads(
        reviewed_myprogress_json(
            [
                myprogress_course_row(
                    1,
                    course_code="FIN 300",
                    title="Managerial Finance",
                    status="COMPLETED",
                    term="2024FA",
                )
            ]
        )
    )
    payload["programSummary"].pop("catalogYear")
    run = DataImportApplicationService(session).create_import(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.DEGREE_AUDIT_EXPORT,
        file_name="sanitized-myprogress-program-only.json",
        file_mime_type="application/json",
        content=json.dumps(payload),
        source_type=SourceType.BROWSER_EXTENSION,
        source_reference="Sanitized program identity without Catalog version",
    )
    review_service = DataReviewApplicationService(session)
    review = review_service.create_review_session(
        data_import_run_id=run.id,
        reviewer_label="Sanitized MyProgress self-review",
    )
    confirm_all_review_records(session, review.id)

    result = review_service.apply_review_session(review.id)
    snapshot = result.course_state_snapshot
    assert snapshot is not None
    assert snapshot.program_mapping_state == ("PROGRAM_IDENTITY_VERIFIED_CATALOG_VERSION_UNKNOWN")
    degree_readiness = snapshot.readiness_payload["degree_audit"]
    assert isinstance(degree_readiness, dict)
    assert degree_readiness["status"] == "BLOCKED"
    assert degree_readiness["blocking_reasons"] == ["CATALOG_VERSION_UNKNOWN"]


def test_myprogress_program_mapping_uses_explicitly_edited_review_payload(
    session: Session,
) -> None:
    mark_finance_program_identity_as_reviewed(session)
    payload = json.loads(
        reviewed_myprogress_json(
            [
                myprogress_course_row(
                    1,
                    course_code="FIN 300",
                    title="Managerial Finance",
                    status="COMPLETED",
                    term="2024FA",
                )
            ]
        )
    )
    payload["programSummary"]["programName"] = "Unverified Source Label"
    run = DataImportApplicationService(session).create_import(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.DEGREE_AUDIT_EXPORT,
        file_name="sanitized-myprogress-edited-program.json",
        file_mime_type="application/json",
        content=json.dumps(payload),
        source_type=SourceType.BROWSER_EXTENSION,
        source_reference="Sanitized program identity corrected during review",
    )
    service = DataReviewApplicationService(session)
    review = service.create_review_session(
        data_import_run_id=run.id,
        reviewer_label="Correct sanitized program identity",
    )
    review_records = session.scalars(
        select(ImportedRecordReview)
        .where(ImportedRecordReview.review_session_id == review.id)
        .order_by(ImportedRecordReview.created_at, ImportedRecordReview.id)
    ).all()
    for review_record in review_records:
        record = session.get(ImportedRecord, review_record.imported_record_id)
        assert record is not None
        is_program_summary = (
            record.normalized_payload.get("record_kind") == "MY_PROGRESS_PROGRAM_SUMMARY"
        )
        service.update_record_review(
            review_session_id=review.id,
            record_review_id=review_record.id,
            decision=(
                ImportedRecordReviewDecision.EDITED_AND_CONFIRMED
                if is_program_summary
                else ImportedRecordReviewDecision.CONFIRMED
            ),
            edited_normalized_payload=(
                {
                    "programSummary": {
                        "programName": "Finance, BS",
                        "degree": "Bachelor of Science",
                        "catalogYear": 2024,
                    }
                }
                if is_program_summary
                else None
            ),
        )

    result = service.apply_review_session(review.id)
    snapshot = result.course_state_snapshot
    assert snapshot is not None
    assert snapshot.program_summary["programName"] == "Finance, BS"
    assert snapshot.program_summary["review_state"] == "EDITED_AND_CONFIRMED"
    assert snapshot.program_mapping_state == "EXACT"


@pytest.mark.parametrize(
    "unverified_source_type",
    [SourceType.MOCK, SourceType.STUDENT_PROVIDED, SourceType.INFERRED],
)
def test_myprogress_program_mapping_never_uses_unverified_program_version(
    session: Session,
    unverified_source_type: SourceType,
) -> None:
    program = session.get(AcademicProgram, seed_uuid("program:bs-finance"))
    version = session.get(ProgramVersion, seed_uuid("program-version:bs-finance-2024"))
    assignment = session.get(
        StudentAcademicProgram,
        seed_uuid("student-academic-program:mock-student-bs-finance"),
    )
    assert program is not None
    assert version is not None
    assert assignment is not None
    program.name = "Finance, BS"
    program.source_type = unverified_source_type
    version.source_type = unverified_source_type
    assignment.source_type = unverified_source_type
    session.commit()
    run_id = create_myprogress_import(
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
    review = service.create_review_session(
        data_import_run_id=run_id,
        reviewer_label="Do not bind real evidence to an unverified ProgramVersion",
    )
    confirm_all_review_records(session, review.id)

    result = service.apply_review_session(review.id)
    snapshot = result.course_state_snapshot
    assert snapshot is not None
    assert snapshot.program_mapping_state == "PROGRAM_IDENTITY_UNMATCHED"
    degree_readiness = snapshot.readiness_payload["degree_audit"]
    assert isinstance(degree_readiness, dict)
    assert degree_readiness["status"] == "BLOCKED"
    assert degree_readiness["blocking_reasons"] == ["PROGRAM_IDENTITY_UNMATCHED"]


def test_rejected_myprogress_context_stays_evidence_only(
    session: Session,
) -> None:
    program = session.get(AcademicProgram, seed_uuid("program:bs-finance"))
    assert program is not None
    program.name = "Finance, BS"
    session.commit()
    run_id = create_myprogress_import(
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
    review = service.create_review_session(
        data_import_run_id=run_id,
        reviewer_label="Reject unverified MyProgress context",
    )
    review_records = session.scalars(
        select(ImportedRecordReview)
        .where(ImportedRecordReview.review_session_id == review.id)
        .order_by(ImportedRecordReview.created_at, ImportedRecordReview.id)
    ).all()
    for review_record in review_records:
        record = session.get(ImportedRecord, review_record.imported_record_id)
        assert record is not None
        decision = (
            ImportedRecordReviewDecision.CONFIRMED
            if record.normalized_payload.get("record_kind") == "MY_PROGRESS_COURSE_ROW"
            else ImportedRecordReviewDecision.REJECTED
        )
        service.update_record_review(
            review_session_id=review.id,
            record_review_id=review_record.id,
            decision=decision,
        )

    result = service.apply_review_session(review.id)
    snapshot = result.course_state_snapshot
    assert snapshot is not None
    assert snapshot.is_active is True
    assert snapshot.program_mapping_state == "PROGRAM_IDENTITY_REVIEW_REQUIRED"
    assert snapshot.program_summary["review_state"] == "REJECTED"
    requirement = snapshot.requirement_summary[0]
    assert isinstance(requirement, dict)
    assert requirement["review_state"] == "REJECTED"
    assert requirement["requires_manual_confirmation"] is True
    summary_readiness = snapshot.readiness_payload["summary"]
    requirement_readiness = snapshot.readiness_payload["requirement_summary"]
    degree_readiness = snapshot.readiness_payload["degree_audit"]
    assert isinstance(summary_readiness, dict)
    assert isinstance(requirement_readiness, dict)
    assert isinstance(degree_readiness, dict)
    assert summary_readiness["status"] == "NEEDS_REVIEW"
    assert summary_readiness["blocking_reasons"] == ["PROGRAM_SUMMARY_REVIEW_REQUIRED"]
    assert requirement_readiness["status"] == "NEEDS_REVIEW"
    assert requirement_readiness["blocking_reasons"] == ["REQUIREMENT_REVIEW_REQUIRED"]
    assert degree_readiness["status"] == "BLOCKED"
    assert degree_readiness["blocking_reasons"] == [
        "PROGRAM_IDENTITY_REVIEW_REQUIRED",
        "REQUIREMENT_REVIEW_REQUIRED",
    ]


def test_myprogress_partial_requirements_remain_visible_without_global_block(
    session: Session,
) -> None:
    mark_finance_program_identity_as_reviewed(session)
    payload = json.loads(
        reviewed_myprogress_json(
            [
                myprogress_course_row(
                    1,
                    course_code="FIN 300",
                    title="Managerial Finance",
                    status="COMPLETED",
                    term="2024FA",
                )
            ]
        )
    )
    payload["requirementGroups"] = [
        {
            "name": "Verified Finance Core",
            "statusText": "Reviewed structured requirement",
            "confidence": "high",
            "requiresReview": False,
        },
        {
            "name": "Uncertain Finance Elective",
            "statusText": "Advisor confirmation required",
            "confidence": "medium",
            "requiresReview": True,
        },
    ]
    run = DataImportApplicationService(session).create_import(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.DEGREE_AUDIT_EXPORT,
        file_name="sanitized-myprogress-partial-requirements.json",
        file_mime_type="application/json",
        content=json.dumps(payload),
        source_type=SourceType.BROWSER_EXTENSION,
        source_reference="Sanitized partial requirement evidence",
    )
    service = DataReviewApplicationService(session)
    review = service.create_review_session(
        data_import_run_id=run.id,
        reviewer_label="Review certain and uncertain requirement evidence",
    )
    review_records = session.scalars(
        select(ImportedRecordReview)
        .where(ImportedRecordReview.review_session_id == review.id)
        .order_by(ImportedRecordReview.created_at, ImportedRecordReview.id)
    ).all()
    for review_record in review_records:
        record = session.get(ImportedRecord, review_record.imported_record_id)
        assert record is not None
        requirement = record.normalized_payload.get("requirementGroup")
        requires_advisor = (
            isinstance(requirement, dict)
            and requirement.get("name") == "Uncertain Finance Elective"
        )
        service.update_record_review(
            review_session_id=review.id,
            record_review_id=review_record.id,
            decision=(
                ImportedRecordReviewDecision.NEEDS_ADVISOR_REVIEW
                if requires_advisor
                else ImportedRecordReviewDecision.CONFIRMED
            ),
        )

    result = service.apply_review_session(review.id)
    snapshot = result.course_state_snapshot
    assert snapshot is not None
    assert snapshot.is_active is True
    requirement_states = {
        requirement["name"]: requirement["review_state"]
        for requirement in snapshot.requirement_summary
        if isinstance(requirement, dict)
    }
    assert requirement_states == {
        "Uncertain Finance Elective": "NEEDS_ADVISOR_REVIEW",
        "Verified Finance Core": "CONFIRMED",
    }
    requirement_readiness = snapshot.readiness_payload["requirement_summary"]
    degree_readiness = snapshot.readiness_payload["degree_audit"]
    assert isinstance(requirement_readiness, dict)
    assert isinstance(degree_readiness, dict)
    assert requirement_readiness["status"] == "READY_WITH_WARNINGS"
    assert requirement_readiness["blocking_reasons"] == []
    assert requirement_readiness["warnings"] == ["REQUIREMENT_EVIDENCE_PARTIAL"]
    assert degree_readiness["status"] == "READY_WITH_WARNINGS"
    assert degree_readiness["blocking_reasons"] == []
    assert degree_readiness["warnings"] == ["REQUIREMENT_EVIDENCE_PARTIAL"]


def test_attempted_myprogress_row_stays_out_of_reliable_course_history(
    session: Session,
) -> None:
    run_id = create_myprogress_import(
        session,
        [
            myprogress_course_row(
                1,
                course_code="FIN 2999",
                title="Sanitized Attempted Course",
                status="ATTEMPTED",
                term="2025FAW",
            )
        ],
    )
    service = DataReviewApplicationService(session)
    review = service.create_review_session(
        data_import_run_id=run_id,
        reviewer_label="Attempted status regression review",
    )
    review_records = session.scalars(
        select(ImportedRecordReview).where(ImportedRecordReview.review_session_id == review.id)
    ).all()
    for review_record in review_records:
        record = session.get(ImportedRecord, review_record.imported_record_id)
        assert record is not None
        decision = (
            ImportedRecordReviewDecision.NEEDS_ADVISOR_REVIEW
            if record.normalized_payload.get("source_status") == "ATTEMPTED"
            else ImportedRecordReviewDecision.CONFIRMED
        )
        service.update_record_review(
            review_session_id=review.id,
            record_review_id=review_record.id,
            decision=decision,
        )

    dry_run = service.apply_review_session(review.id, dry_run=True)
    assert "ADVISOR_REVIEW_REQUIRED" in {outcome.reason_code for outcome in dry_run.applied_records}

    result = service.apply_review_session(review.id)
    assert result.course_state_snapshot is not None
    assert result.course_state_snapshot.completed_count == 0
    assert result.course_state_snapshot.exception_count == 1
    assert result.course_state_snapshot.is_active is False
    assert (
        session.scalar(
            select(func.count())
            .select_from(StudentCourseAttempt)
            .where(StudentCourseAttempt.course_state_snapshot_id == result.course_state_snapshot.id)
        )
        == 0
    )


def test_repeated_myprogress_capture_replaces_active_evidence_without_double_counting(
    session: Session,
) -> None:
    service = DataReviewApplicationService(session)
    student_id = seed_uuid("student-profile:mock-student")
    course_id = seed_uuid("course:FIN-200")
    snapshot_ids: list[UUID] = []

    for capture_number in (1, 2):
        run_id = create_myprogress_import(
            session,
            [
                myprogress_course_row(
                    1,
                    course_code="FIN 200",
                    title="Finance Foundations",
                    status="COMPLETED",
                    term="2024FA",
                )
            ],
        )
        review = service.create_review_session(
            data_import_run_id=run_id,
            reviewer_label=f"Repeated MyProgress review {capture_number}",
        )
        confirm_all_review_records(session, review.id)
        result = service.apply_review_session(review.id)
        assert result.course_state_snapshot is not None
        snapshot_ids.append(result.course_state_snapshot.id)

    active = active_course_state_snapshot(session, student_id)
    assert active is not None
    assert active.id == snapshot_ids[1]
    previous = session.get(CourseStateSnapshot, snapshot_ids[0])
    assert previous is not None
    assert previous.is_active is False
    effective = effective_student_course_attempts(
        session,
        student_id,
        course_id=course_id,
        statuses={StudentCourseAttemptStatus.COMPLETED},
    )
    assert len(effective) == 1
    assert effective[0].course_state_snapshot_id == snapshot_ids[1]


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
    confirm_all_review_records(session, valid_review.id)
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
    for record in session.scalars(
        select(ImportedRecordReview)
        .join(ImportedRecord, ImportedRecordReview.imported_record_id == ImportedRecord.id)
        .where(ImportedRecordReview.review_session_id == review.id)
    ).all():
        imported_record = session.get(ImportedRecord, record.imported_record_id)
        assert imported_record is not None
        row_validation = imported_record.normalized_payload.get("row_validation")
        if not isinstance(row_validation, dict) or not row_validation.get("reason_codes"):
            DataReviewApplicationService(session).update_record_review(
                review_session_id=review.id,
                record_review_id=record.id,
                decision=ImportedRecordReviewDecision.CONFIRMED,
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
    service.update_record_review(
        review_session_id=review.id,
        record_review_id=select_review_record(session, review.id, "FIN 450").id,
        decision=ImportedRecordReviewDecision.CONFIRMED,
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
    confirm_all_review_records(session, review.id)
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
