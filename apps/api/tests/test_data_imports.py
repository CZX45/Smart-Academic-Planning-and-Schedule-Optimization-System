import json
from collections.abc import Generator
from typing import Any, Protocol, cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pytest import LogCaptureFixture
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.academic import (
    AppliedImportStatus,
    AuditWarningSeverity,
    DataImportFile,
    DataImportReviewStatus,
    DataImportRun,
    DataImportStatus,
    DataImportStorageStrategy,
    DataImportType,
    ImportedRecord,
    ImportedRecordReview,
    ImportedRecordReviewDecision,
    ImportedRecordStatus,
    ImportedRecordType,
    ImportMappingCandidate,
    ImportMatchType,
    ImportPreviewSummary,
    ImportTargetEntityType,
    ImportValidationWarning,
    SourceType,
    StudentCourseAttempt,
)
from app.seed_dev import seed_mock_data, seed_uuid
from app.services.data_imports.engine import DataImportApplicationService
from app.services.data_review.engine import DataReviewApplicationService


class DataImportCreatedLogRecord(Protocol):
    student_profile_id: str
    source_type: str
    import_type: str
    record_count: int
    warning_count: int


def count_rows(session: Session, model: type[Any]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


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


def transcript_csv() -> str:
    return "\n".join(
        [
            "term,course_code,title,grade,credits,status",
            "2024FA,FIN 300,Mock Managerial Finance,B,3.0,COMPLETED",
            "2024FA,FIN 999,Unreviewed Special Topic,A,3.0,COMPLETED",
        ]
    )


def kean_finance_myprogress_json() -> str:
    return json.dumps(
        {
            "source_type": "BROWSER_EXTENSION",
            "staging_only": True,
            "page_type": "KEAN_MY_PROGRESS_PAGE",
            "programSummary": {
                "programName": "Finance, BS",
                "degree": "Bachelor of Science",
                "major": "Finance",
                "department": "Accounting & Finance",
                "catalogYear": 2024,
                "cumulativeGpa": 3.916,
                "institutionGpa": 3.916,
                "anticipatedCompletionDate": "12/20/2028",
            },
            "creditSummary": {
                "totalAppliedCredits": 104,
                "totalRequiredCredits": 120,
                "completedCredits": 67,
                "inProgressCredits": 24,
                "plannedCredits": 13,
                "remainingCredits": 16,
                "completionPercent": 86.67,
            },
            "progressBarSegments": [
                {
                    "value": 67,
                    "rawText": "67",
                    "classification": "COMPLETED",
                    "requiresReview": False,
                },
                {
                    "value": 24,
                    "rawText": "24",
                    "classification": "IN_PROGRESS",
                    "requiresReview": False,
                },
                {
                    "value": 13,
                    "rawText": "13",
                    "classification": "PLANNED",
                    "requiresReview": False,
                },
            ],
            "fieldProvenance": {
                "completedCredits": {
                    "value": 67,
                    "rawText": "67",
                    "source": "MyProgress Total Credits progress bar green segment",
                    "confidence": "high",
                    "requiresReview": False,
                }
            },
            "requirementGroups": [
                {
                    "name": "GE Foundation Requirements 13 S.H.",
                    "statusText": "GE*1000/3000 4 of 5 Completed 13",
                    "source": "Requirement Group",
                    "confidence": "high",
                    "requiresReview": False,
                }
            ],
            "courseRows": [],
            "rawSnapshot": {
                "pageTitle": "MyProgress",
                "pageUrl": (
                    "https://kean-ss.colleague.elluciancloud.com/Student/"
                    "Planning/Programs/MyProgress"
                ),
                "capturedAt": "1970-01-01T00:00:00.000Z",
                "visibleTextSample": (
                    "My Progress Finance, BS Degree Bachelor of Science Major Finance "
                    "Department Accounting & Finance Catalog 2024 Cumulative GPA 3.916 "
                    "Institution GPA 3.916 Anticipated Completion Date 12/20/2028 "
                    "Total Credits 104 of 120 67 24 13 GE Foundation Requirements 13 S.H. "
                    "GE*1000/3000 4 of 5 Completed"
                ),
                "headings": [
                    "My Progress",
                    "Finance, BS",
                    "GE Foundation Requirements 13 S.H.",
                ],
                "visibleTables": [
                    {
                        "caption": "GE Foundation Requirements 13 S.H.",
                        "headers": ["Requirement", "Status", "Credits"],
                        "rows": [["GE*1000/3000", "4 of 5 Completed", "13"]],
                    }
                ],
                "visibleRows": [["GE*1000/3000", "4 of 5 Completed", "13"]],
                "requirementLikeBlocks": ["GE Foundation Requirements 13 S.H."],
                "courseLikeRows": [],
                "progressBarText": "67 24 13",
                "progressSegmentText": ["67", "24", "13"],
                "diagnostics": {
                    "tableCount": 1,
                    "rowCount": 1,
                    "requirementGroupCount": 1,
                    "courseLikeRowCount": 1,
                    "truncated": False,
                },
            },
            "validation": {
                "status": "AUTO_VERIFIED",
                "exceptionCount": 0,
                "exceptions": [],
                "autoConfirmedFieldCount": 14,
                "autoConfirmedCourseRowCount": 0,
                "overallConfidenceScore": 1.0,
                "downstreamAnalysisAllowed": True,
            },
        }
    )


def myprogress_course_row(
    index: int,
    *,
    course_code: str,
    title: str,
    status: str,
    term: str = "",
    requirement: str = "Open Electives Requirements",
    confidence: str = "high",
) -> dict[str, Any]:
    return {
        "requirements": requirement,
        "requirement_section": requirement,
        "status": status,
        "raw_course_code": course_code.replace(" ", "*"),
        "course_code": course_code,
        "course_title": title,
        "term_code": term,
        "credits": "3",
        "source_page_type": "KEAN_MY_PROGRESS_PAGE",
        "type": "DEGREE_AUDIT_EXPORT",
        "source_label": requirement,
        "raw_row_text": f"{status} {course_code} {title} {term} 3",
        "source_table_index": str(1 + (index // 5)),
        "source_row_index": str(index),
        "field_provenance": {
            "course_code": {
                "rawText": course_code,
                "source": f"visible table {1 + (index // 5)} row {index}",
                "confidence": confidence,
            }
        },
        "confidence": confidence,
        "warnings": [],
    }


def kean_myprogress_with_85_rows_json() -> str:
    payload = json.loads(kean_finance_myprogress_json())
    examples = [
        myprogress_course_row(
            1,
            course_code="MATH 1044",
            title="Precalculus for Business",
            status="NOT_STARTED",
            requirement="Mathematics Requirements",
        ),
        myprogress_course_row(
            2,
            course_code="MATH 1054",
            title="Pre-Calculus",
            status="NOT_STARTED",
            requirement="Mathematics Requirements",
        ),
        myprogress_course_row(
            3,
            course_code="ENG 2403",
            title="World Literature",
            status="PLANNED",
            term="2026SUW",
            requirement="Open Electives Requirements",
        ),
        myprogress_course_row(
            4,
            course_code="GE 1855",
            title="First Year Seminar",
            status="NOT_STARTED",
            requirement="GE Foundation Requirements 13 S.H.",
        ),
        myprogress_course_row(
            5,
            course_code="AH 1700",
            title="Art-Prehist to Middle Ages",
            status="NOT_STARTED",
            requirement="Humanities Requirements",
        ),
        myprogress_course_row(
            6,
            course_code="AH 1701",
            title="Hist Art-Renssce to Mod. Wrld",
            status="NOT_STARTED",
            requirement="Humanities Requirements",
        ),
    ]
    generated = [
        myprogress_course_row(
            index,
            course_code=f"FIN {3000 + index}",
            title=f"Finance Requirement {index}",
            status="COMPLETED" if index % 3 == 0 else "IN_PROGRESS",
            term="2025FAW" if index % 3 == 0 else "2026SPW",
            requirement="Finance Major Requirements",
        )
        for index in range(7, 85)
    ]
    exception_row = {
        "requirements": "Unsupported Requirement Format",
        "requirement_section": "Unsupported Requirement Format",
        "status": "NEEDS_REVIEW",
        "course_title": "Ambiguous placeholder row",
        "raw_row_text": "Needs review Ambiguous placeholder row",
        "source_table_index": "17",
        "source_row_index": "85",
        "confidence": "low",
        "warnings": ["unsupported requirement format"],
    }
    payload["courseRows"] = [*examples, *generated, exception_row]
    payload["rawSnapshot"]["visibleRows"] = [
        [str(row.get("raw_row_text", ""))] for row in payload["courseRows"]
    ]
    payload["rawSnapshot"]["courseLikeRows"] = [
        str(row.get("raw_row_text", "")) for row in payload["courseRows"]
    ]
    payload["rawSnapshot"]["diagnostics"] = {
        "tableCount": 17,
        "rowCount": 85,
        "requirementGroupCount": 1,
        "courseLikeRowCount": 85,
        "truncated": True,
        "bounded": True,
        "academicRowsSkipped": 1,
    }
    payload["validation"] = {
        "status": "AUTO_VERIFIED",
        "exceptionCount": 0,
        "exceptions": [],
        "autoConfirmedFieldCount": 14,
        "autoConfirmedCourseRowCount": 84,
        "overallConfidenceScore": 1.0,
        "downstreamAnalysisAllowed": True,
    }
    payload["warnings"] = [
        {
            "code": "EXTRACTION_LIMIT_REACHED",
            "severity": "WARNING",
            "message": "Extraction stopped early because the page is large.",
        },
        {
            "code": "MY_PROGRESS_PARTIAL_TABLE_PARSE",
            "severity": "WARNING",
            "message": "Only a subset of visible MyProgress rows was parsed.",
        },
    ]
    return json.dumps(payload)


def failed_kean_myprogress_json() -> str:
    payload = json.loads(kean_finance_myprogress_json())
    payload["programSummary"].pop("catalogYear")
    payload["creditSummary"]["remainingCredits"] = 93
    payload["validation"] = {
        "status": "FAILED",
        "exceptionCount": 2,
        "exceptions": [
            {
                "code": "MY_PROGRESS_CATALOG_YEAR_MISSING",
                "message": "Catalog year was not detected.",
                "source": "At a Glance",
                "severity": "ERROR",
            },
            {
                "code": "MY_PROGRESS_REMAINING_CREDITS_MISMATCH",
                "message": "Remaining credits do not reconcile with total credits.",
                "source": "Total Credits",
                "severity": "ERROR",
            },
        ],
        "autoConfirmedFieldCount": 12,
        "autoConfirmedCourseRowCount": 0,
        "overallConfidenceScore": 0.0,
        "downstreamAnalysisAllowed": False,
    }
    return json.dumps(payload)


def test_data_import_models_are_staging_only_and_explainable(session: Session) -> None:
    run = DataImportRun(
        id=seed_uuid("data-import-run:test-model"),
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.UNOFFICIAL_TRANSCRIPT,
        status=DataImportStatus.PARSED_WITH_WARNINGS,
        storage_strategy=DataImportStorageStrategy.METADATA_ONLY,
        file_name="mock-transcript.csv",
        file_mime_type="text/csv",
        file_size_bytes=97,
        file_sha256="a" * 64,
        parser_version="phase7a-data-import-v1",
        record_count=1,
        valid_record_count=0,
        warning_count=1,
        error_count=0,
        official_application_ready=False,
        source_type=SourceType.STUDENT_PROVIDED,
        is_official=False,
        source_reference="User-provided mock transcript fixture",
        source_confidence="student_provided",
    )
    session.add(run)
    session.flush()

    session.add(
        DataImportFile(
            id=seed_uuid("data-import-file:test-model"),
            data_import_run_id=run.id,
            storage_strategy=DataImportStorageStrategy.METADATA_ONLY,
            file_name=run.file_name,
            file_mime_type=run.file_mime_type,
            file_size_bytes=run.file_size_bytes,
            file_sha256=run.file_sha256,
            content_preview="term,course_code,title,grade,credits,status",
        )
    )
    record = ImportedRecord(
        id=seed_uuid("imported-record:test-model"),
        data_import_run_id=run.id,
        record_type=ImportedRecordType.COURSE_ATTEMPT,
        row_number=2,
        status=ImportedRecordStatus.AMBIGUOUS,
        external_identifier="FIN 999",
        raw_label="FIN 999 Unreviewed Special Topic",
        normalized_payload={"course_code": "FIN 999", "credits": "3.0"},
        confidence_score="0.35",
    )
    session.add(record)
    session.flush()
    session.add_all(
        [
            ImportMappingCandidate(
                id=seed_uuid("import-mapping-candidate:test-model"),
                imported_record_id=record.id,
                target_entity_type=ImportTargetEntityType.UNKNOWN,
                target_entity_id=None,
                match_type=ImportMatchType.NO_MATCH,
                confidence_score="0.00",
                is_selected=False,
                reason_code="NO_MATCH",
                explanation="FIN 999 did not match the mock catalog and requires manual review.",
            ),
            ImportValidationWarning(
                id=seed_uuid("import-warning:test-model"),
                data_import_run_id=run.id,
                imported_record_id=record.id,
                warning_code="UNMATCHED_COURSE_CODE",
                severity=AuditWarningSeverity.WARNING,
                message="FIN 999 is staged but not matched to a reviewed course.",
                requires_advisor_confirmation=True,
            ),
            ImportPreviewSummary(
                id=seed_uuid("import-preview:test-model"),
                data_import_run_id=run.id,
                record_count=1,
                valid_record_count=0,
                warning_count=1,
                error_count=0,
                official_application_ready=False,
                summary_payload={"disclaimer": "Staging preview only."},
            ),
        ]
    )
    session.commit()

    reloaded = session.get(DataImportRun, run.id)
    assert reloaded is not None
    assert reloaded.is_official is False
    assert reloaded.official_application_ready is False

    bad_run = DataImportRun(
        id=seed_uuid("data-import-run:bad-official"),
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.UNOFFICIAL_TRANSCRIPT,
        status=DataImportStatus.PENDING,
        storage_strategy=DataImportStorageStrategy.METADATA_ONLY,
        file_name="official-looking.csv",
        file_mime_type="text/csv",
        file_size_bytes=12,
        file_sha256="b" * 64,
        parser_version="phase7a-data-import-v1",
        source_type=SourceType.OFFICIAL,
        is_official=True,
        source_confidence="official",
    )
    session.add(bad_run)
    with pytest.raises(IntegrityError):
        session.commit()


def test_data_import_service_parses_and_matches_without_writing_domain_records(
    session: Session,
) -> None:
    attempts_before = count_rows(session, StudentCourseAttempt)
    service = DataImportApplicationService(session)

    run = service.create_import(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.UNOFFICIAL_TRANSCRIPT,
        file_name="mock-transcript.csv",
        file_mime_type="text/csv",
        content=transcript_csv(),
        source_type=SourceType.STUDENT_PROVIDED,
        source_reference="Student-uploaded CSV fixture",
    )
    session.commit()

    assert run.status is DataImportStatus.PARSED_WITH_WARNINGS
    assert run.source_type is SourceType.STUDENT_PROVIDED
    assert run.is_official is False
    assert run.official_application_ready is False
    assert count_rows(session, StudentCourseAttempt) == attempts_before

    records = session.scalars(
        select(ImportedRecord)
        .where(ImportedRecord.data_import_run_id == run.id)
        .order_by(ImportedRecord.row_number)
    ).all()
    assert [record.normalized_payload["course_code"] for record in records] == [
        "FIN 300",
        "FIN 999",
    ]
    assert records[0].status is ImportedRecordStatus.VALID_WITH_WARNINGS
    assert records[1].status is ImportedRecordStatus.AMBIGUOUS

    candidates = session.scalars(
        select(ImportMappingCandidate)
        .join(ImportedRecord, ImportMappingCandidate.imported_record_id == ImportedRecord.id)
        .where(ImportedRecord.data_import_run_id == run.id)
        .order_by(ImportedRecord.row_number, ImportMappingCandidate.confidence_score.desc())
    ).all()
    assert candidates[0].target_entity_type is ImportTargetEntityType.COURSE
    assert candidates[0].target_entity_id == seed_uuid("course:FIN-300")
    assert candidates[0].reason_code == "EXACT_COURSE_CODE"
    assert candidates[-1].match_type is ImportMatchType.NO_MATCH
    assert candidates[-1].explanation

    warnings = session.scalars(
        select(ImportValidationWarning)
        .where(ImportValidationWarning.data_import_run_id == run.id)
        .order_by(ImportValidationWarning.warning_code)
    ).all()
    warning_codes = {warning.warning_code for warning in warnings}
    assert {"STAGING_ONLY_NOT_OFFICIAL", "UNMATCHED_COURSE_CODE"} <= warning_codes
    assert all(warning.requires_advisor_confirmation for warning in warnings)


def test_data_import_service_logs_safe_metadata(
    session: Session,
    caplog: LogCaptureFixture,
) -> None:
    service = DataImportApplicationService(session)

    with caplog.at_level("INFO", logger="app.services.data_imports.engine"):
        service.create_import(
            student_profile_id=seed_uuid("student-profile:mock-student"),
            import_type=DataImportType.UNOFFICIAL_TRANSCRIPT,
            file_name="mock-transcript.csv",
            file_mime_type="text/csv",
            content=transcript_csv(),
        )

    records = [record for record in caplog.records if record.message == "data_import.created"]
    assert len(records) == 1
    log_record = cast(DataImportCreatedLogRecord, records[0])
    assert log_record.student_profile_id == str(seed_uuid("student-profile:mock-student"))
    assert log_record.source_type == "STUDENT_PROVIDED"
    assert log_record.import_type == "UNOFFICIAL_TRANSCRIPT"
    assert log_record.record_count == 2
    assert log_record.warning_count >= 1
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "Mock Managerial Finance" not in log_text
    assert "FIN 999" not in log_text
    assert "mock-transcript.csv" not in log_text


def test_browser_extension_import_enters_staging_and_preserves_review_boundary(
    session: Session,
) -> None:
    attempts_before = count_rows(session, StudentCourseAttempt)
    service = DataImportApplicationService(session)

    run = service.create_import(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.SECTION_SCHEDULE,
        file_name="browser-extension-section-schedule.csv",
        file_mime_type="text/csv",
        content="\n".join(
            [
                "term_code,course_code,section_code,modality,status,credits",
                "2025FA,FIN 403,001,IN_PERSON,OPEN,3",
            ]
        ),
        source_type=SourceType.BROWSER_EXTENSION,
        source_reference=(
            "Browser extension visible-page import: https://portal.example.edu/section-search"
        ),
    )

    assert run.source_type is SourceType.BROWSER_EXTENSION
    assert run.source_confidence == "browser_extension"
    assert run.is_official is False
    assert run.official_application_ready is False
    assert count_rows(session, StudentCourseAttempt) == attempts_before

    preview = session.scalar(
        select(ImportPreviewSummary).where(ImportPreviewSummary.data_import_run_id == run.id)
    )
    assert preview is not None
    disclaimer_items = preview.summary_payload["disclaimers"]
    assert isinstance(disclaimer_items, list)
    disclaimers = " ".join(str(item) for item in disclaimer_items)
    assert "Browser extension imports are staging-only" in disclaimers
    assert "Phase 7B review is required" in disclaimers


def test_data_import_api_exposes_preview_records_candidates_warnings_and_validation(
    client: TestClient,
) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))
    response = client.post(
        "/api/v1/data-imports",
        json={
            "student_profile_id": student_id,
            "import_type": "UNOFFICIAL_TRANSCRIPT",
            "file_name": "mock-transcript.csv",
            "file_mime_type": "text/csv",
            "content": transcript_csv(),
            "source_type": "STUDENT_PROVIDED",
            "source_reference": "Student-uploaded CSV fixture",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    run_id = payload["id"]
    UUID(run_id)
    assert payload["status"] == "PARSED_WITH_WARNINGS"
    assert payload["source"]["source_type"] == "STUDENT_PROVIDED"
    assert payload["official_application_ready"] is False

    assert client.get(f"/api/v1/data-imports/{run_id}").status_code == 200

    records = client.get(f"/api/v1/data-imports/{run_id}/records")
    assert records.status_code == 200
    record_payload = records.json()
    assert [record["normalized_payload"]["course_code"] for record in record_payload] == [
        "FIN 300",
        "FIN 999",
    ]

    candidates = client.get(f"/api/v1/data-imports/{run_id}/mapping-candidates")
    assert candidates.status_code == 200
    assert any(
        candidate["target_entity_type"] == "COURSE"
        and candidate["target_entity_id"] == str(seed_uuid("course:FIN-300"))
        for candidate in candidates.json()
    )

    warnings = client.get(f"/api/v1/data-imports/{run_id}/warnings")
    assert warnings.status_code == 200
    assert {warning["warning_code"] for warning in warnings.json()} >= {
        "STAGING_ONLY_NOT_OFFICIAL",
        "UNMATCHED_COURSE_CODE",
    }

    preview = client.get(f"/api/v1/data-imports/{run_id}/preview")
    assert preview.status_code == 200
    preview_payload = preview.json()
    assert preview_payload["official_application_ready"] is False
    assert "not official school policy" in " ".join(preview_payload["disclaimers"]).lower()

    student_imports = client.get(f"/api/v1/students/{student_id}/data-imports")
    assert student_imports.status_code == 200
    assert any(item["id"] == run_id for item in student_imports.json())

    validation = client.post(f"/api/v1/data-imports/{run_id}/validate")
    assert validation.status_code == 200
    assert validation.json()["official_application_ready"] is False

    blocked_official = client.post(
        "/api/v1/data-imports",
        json={
            "student_profile_id": student_id,
            "import_type": "UNOFFICIAL_TRANSCRIPT",
            "file_name": "official.csv",
            "file_mime_type": "text/csv",
            "content": transcript_csv(),
            "source_type": "OFFICIAL",
        },
    )
    assert blocked_official.status_code == 400
    assert "read-only" in blocked_official.json()["detail"]["message"].lower()


def test_data_import_api_accepts_browser_extension_source_as_non_official_staging(
    client: TestClient,
) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))
    response = client.post(
        "/api/v1/data-imports",
        json={
            "student_profile_id": student_id,
            "import_type": "SECTION_SCHEDULE",
            "file_name": "browser-extension-section-schedule.csv",
            "file_mime_type": "text/csv",
            "content": "\n".join(
                [
                    "term_code,course_code,section_code,modality,status,credits",
                    "2025FA,FIN 403,001,IN_PERSON,OPEN,3",
                ]
            ),
            "source_type": "BROWSER_EXTENSION",
            "source_reference": (
                "Browser extension visible-page import: https://portal.example.edu/section-search"
            ),
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["source"]["source_type"] == "BROWSER_EXTENSION"
    assert payload["source"]["is_official"] is False
    assert payload["official_application_ready"] is False

    preview = client.get(f"/api/v1/data-imports/{payload['id']}/preview")
    assert preview.status_code == 200
    assert preview.json()["official_application_ready"] is False
    assert any(
        "Browser extension imports are staging-only" in disclaimer
        for disclaimer in preview.json()["disclaimers"]
    )


def test_kean_browser_extension_import_is_labeled_non_official_and_review_gated(
    client: TestClient,
) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))
    response = client.post(
        "/api/v1/data-imports",
        json={
            "student_profile_id": student_id,
            "import_type": "UNOFFICIAL_TRANSCRIPT",
            "file_name": "kean-student-portal-unofficial-transcript.csv",
            "file_mime_type": "text/csv",
            "content": "\n".join(
                [
                    "term_code,course_code,course_title,credits,grade,attempt_status,source_label",
                    (
                        "2024FA,FIN 300,Mock Managerial Finance,3.0,B,COMPLETED,"
                        "Kean visible transcript table"
                    ),
                ]
            ),
            "source_type": "BROWSER_EXTENSION",
            "source_reference": (
                "KEAN_STUDENT_PORTAL browser extension import: "
                "https://kean-ss.colleague.elluciancloud.com/Student/AcademicHistory"
            ),
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["source"]["source_type"] == "BROWSER_EXTENSION"
    assert payload["source"]["is_official"] is False
    assert payload["official_application_ready"] is False

    preview = client.get(f"/api/v1/data-imports/{payload['id']}/preview")
    assert preview.status_code == 200
    preview_payload = preview.json()
    assert preview_payload["official_application_ready"] is False
    assert preview_payload["summary_payload"]["source_label"] == "KEAN_STUDENT_PORTAL"
    assert any("Kean Student Portal" in item for item in preview_payload["disclaimers"])
    assert any("Phase 7B review is required" in item for item in preview_payload["disclaimers"])

    review_response = client.post(
        "/api/v1/data-import-reviews",
        json={
            "data_import_run_id": payload["id"],
            "reviewer_label": "Kean student self-review",
        },
    )
    assert review_response.status_code == 201
    assert review_response.json()["status"] == "IN_REVIEW"


def test_kean_myprogress_summary_is_parser_verified_but_review_gated(
    session: Session,
) -> None:
    service = DataImportApplicationService(session)

    run = service.create_import(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.DEGREE_AUDIT_EXPORT,
        file_name="kean-student-portal-my-progress.json",
        file_mime_type="application/json",
        content=kean_finance_myprogress_json(),
        source_type=SourceType.BROWSER_EXTENSION,
        source_reference=(
            "KEAN_STUDENT_PORTAL browser extension import: "
            "https://kean-ss.colleague.elluciancloud.com/Student/Planning/Programs/MyProgress"
        ),
    )

    assert run.status is DataImportStatus.PARSED
    assert run.source_confidence == "browser_extension"
    assert run.record_count == 2
    assert run.valid_record_count == 2
    assert run.error_count == 0
    assert run.official_application_ready is False

    preview = session.scalar(
        select(ImportPreviewSummary).where(ImportPreviewSummary.data_import_run_id == run.id)
    )
    assert preview is not None
    payload = cast(dict[str, Any], preview.summary_payload)
    assert payload["real_import_status"] == "REAL_IMPORTED_DATA_PENDING_REVIEW"
    assert payload["mock_data_mixed_with_real_import"] is False
    assert payload["can_apply_verified_import"] is False
    assert payload["review_required"] is True
    assert payload["downstream_analysis_allowed"] is True
    assert payload["exception_count"] == 0
    assert payload["auto_confirmed_field_count"] >= 14
    assert payload["auto_confirmed_course_row_count"] == 0
    assert payload["overall_confidence_score"] == 1.0
    assert payload["program_summary"] == {
        "programName": "Finance, BS",
        "degree": "Bachelor of Science",
        "major": "Finance",
        "department": "Accounting & Finance",
        "catalogYear": 2024,
        "cumulativeGpa": 3.916,
        "institutionGpa": 3.916,
        "anticipatedCompletionDate": "12/20/2028",
    }
    assert payload["credit_summary"] == {
        "totalAppliedCredits": 104,
        "totalRequiredCredits": 120,
        "completedCredits": 67,
        "inProgressCredits": 24,
        "plannedCredits": 13,
        "remainingCredits": 16,
        "completionPercent": 86.67,
    }
    requirement_groups = cast(list[dict[str, Any]], payload["requirement_groups"])
    assert requirement_groups[0]["name"] == "GE Foundation Requirements 13 S.H."
    assert "4 of 5 Completed" in requirement_groups[0]["statusText"]

    records = session.scalars(
        select(ImportedRecord)
        .where(ImportedRecord.data_import_run_id == run.id)
        .order_by(ImportedRecord.row_number)
    ).all()
    assert [record.record_type for record in records] == [
        ImportedRecordType.PROGRAM,
        ImportedRecordType.REQUIREMENT,
    ]
    assert all(record.status is ImportedRecordStatus.VALID for record in records)
    assert all(
        cast(dict[str, Any], record.normalized_payload)["requiresReview"] is True
        for record in records
    )
    program_record_payload = cast(dict[str, Any], records[0].normalized_payload)
    program_summary = cast(dict[str, Any], program_record_payload["programSummary"])
    credit_summary = cast(dict[str, Any], program_record_payload["creditSummary"])
    assert program_summary["programName"] == "Finance, BS"
    assert credit_summary["completedCredits"] == 67

    review = DataReviewApplicationService(session).create_review_session(
        data_import_run_id=run.id,
        reviewer_label="Kean student self-review",
    )
    assert review.status is DataImportReviewStatus.IN_REVIEW

    review_records = session.scalars(
        select(ImportedRecordReview).where(ImportedRecordReview.review_session_id == review.id)
    ).all()
    assert review_records
    assert {record_review.decision for record_review in review_records} == {
        ImportedRecordReviewDecision.UNREVIEWED
    }
    assert all(
        record_review.requires_advisor_confirmation is True for record_review in review_records
    )

    review_service = DataReviewApplicationService(session)
    for record_review in review_records:
        review_service.update_record_review(
            review_session_id=review.id,
            record_review_id=record_review.id,
            decision=ImportedRecordReviewDecision.CONFIRMED,
        )

    attempts_before = count_rows(session, StudentCourseAttempt)
    result = DataReviewApplicationService(session).apply_review_session(review.id, dry_run=True)
    assert count_rows(session, StudentCourseAttempt) == attempts_before
    assert {record.reason_code for record in result.applied_records} == {
        "APPLIED_MYPROGRESS_PROGRAM_SUMMARY",
        "APPLIED_MYPROGRESS_REQUIREMENT_SUMMARY",
    }
    assert all(record.status is AppliedImportStatus.SUCCESS for record in result.applied_records)
    assert all(record.reason_code != "UNSUPPORTED_TARGET_TYPE" for record in result.applied_records)


def test_kean_myprogress_preserves_85_rows_and_marks_course_readiness_partial(
    session: Session,
) -> None:
    service = DataImportApplicationService(session)

    run = service.create_import(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.DEGREE_AUDIT_EXPORT,
        file_name="kean-student-portal-my-progress-85-rows.json",
        file_mime_type="application/json",
        content=kean_myprogress_with_85_rows_json(),
        source_type=SourceType.BROWSER_EXTENSION,
        source_reference=(
            "KEAN_STUDENT_PORTAL browser extension import: "
            "https://kean-ss.colleague.elluciancloud.com/Student/Planning/Programs/MyProgress"
        ),
    )

    assert run.record_count == 87
    assert run.valid_record_count == 86
    assert run.error_count == 1

    preview = session.scalar(
        select(ImportPreviewSummary).where(ImportPreviewSummary.data_import_run_id == run.id)
    )
    assert preview is not None
    payload = cast(dict[str, Any], preview.summary_payload)
    assert payload["extracted_degree_audit_row_count"] == 85
    assert payload["parsed_course_like_row_count"] == 84
    assert payload["parsed_requirement_row_count"] == 1
    assert payload["exception_row_count"] == 1
    assert payload["ignored_row_count"] == 0
    assert payload["extraction_bounded"] is True
    assert payload["extraction_truncated"] is True

    readiness = cast(dict[str, Any], payload["readiness"])
    assert readiness["summary"]["status"] == "AUTO_VERIFIED"
    assert readiness["requirement_summary"]["status"] == "APPLIED_OR_READY"
    assert readiness["course_rows"]["status"] == "PARTIAL_REQUIRES_REVIEW"
    assert readiness["planner"]["status"] == "BLOCKED"
    assert readiness["course_eligibility"]["status"] == "DEMO_ONLY"
    assert readiness["schedule_builder"]["status"] == "DEMO_ONLY"

    course_rows = cast(list[dict[str, Any]], payload["course_rows"])
    assert len(course_rows) == 85
    assert course_rows[0]["course_code"] == "MATH 1044"
    assert course_rows[0]["status"] == "NOT_STARTED"
    assert course_rows[0]["source_table_index"] == "1"
    assert course_rows[2]["course_code"] == "ENG 2403"
    assert course_rows[2]["term"] == "2026SUW"
    assert course_rows[2]["status"] == "PLANNED"

    records = session.scalars(
        select(ImportedRecord)
        .where(ImportedRecord.data_import_run_id == run.id)
        .order_by(ImportedRecord.row_number)
    ).all()
    math_1044 = next(
        record for record in records if record.normalized_payload.get("course_code") == "MATH 1044"
    )
    assert math_1044.status is ImportedRecordStatus.VALID
    assert math_1044.normalized_payload["record_kind"] == "MY_PROGRESS_COURSE_ROW"
    math_raw_row_text = math_1044.normalized_payload["raw_row_text"]
    assert isinstance(math_raw_row_text, str)
    assert math_raw_row_text.startswith("NOT_STARTED MATH 1044")
    assert math_1044.normalized_payload["requirement_group_context"] == ("Mathematics Requirements")

    exception = next(
        record
        for record in records
        if record.normalized_payload.get("raw_row_text") == "Needs review Ambiguous placeholder row"
    )
    assert exception.status is ImportedRecordStatus.INVALID
    row_validation = cast(dict[str, Any], exception.normalized_payload["row_validation"])
    assert row_validation["reason_codes"] == [
        "MISSING_COURSE_CODE",
        "UNKNOWN_STATUS",
    ]


def test_data_import_api_stores_kean_myprogress_85_rows_from_extension_payload(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/data-imports",
        json={
            "student_profile_id": str(seed_uuid("student-profile:mock-student")),
            "import_type": "DEGREE_AUDIT_EXPORT",
            "file_name": "kean-student-portal-my-progress-85-rows.json",
            "file_mime_type": "application/json",
            "content": kean_myprogress_with_85_rows_json(),
            "source_type": "BROWSER_EXTENSION",
            "source_reference": (
                "KEAN_STUDENT_PORTAL browser extension import: "
                "https://kean-ss.colleague.elluciancloud.com/Student/Planning/Programs/MyProgress"
            ),
            "page_type": "KEAN_MY_PROGRESS_PAGE",
            "extracted_record_count": 85,
            "visible_row_count": 85,
            "academic_field_count": 748,
            "bounded": True,
            "truncated": True,
            "warnings": [
                {
                    "code": "EXTRACTION_LIMIT_REACHED",
                    "severity": "WARNING",
                    "message": "Extraction stopped early because the page is large.",
                }
            ],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["source"]["source_type"] == "BROWSER_EXTENSION"
    assert payload["record_count"] == 87

    preview = client.get(f"/api/v1/data-imports/{payload['id']}/preview")
    assert preview.status_code == 200
    summary = preview.json()["summary_payload"]
    assert summary["real_import_status"] == "REAL_IMPORTED_DATA_REQUIRES_EXCEPTION_REVIEW"
    assert summary["can_apply_verified_import"] is False
    assert summary["review_required"] is True
    assert summary["exception_count"] == 1
    assert summary["extracted_degree_audit_row_count"] == 85
    assert summary["parsed_course_like_row_count"] == 84
    assert summary["parsed_requirement_row_count"] == 1
    assert summary["exception_row_count"] == 1
    assert summary["course_rows"][0]["course_code"] == "MATH 1044"
    assert summary["course_rows"][2]["course_code"] == "ENG 2403"


def test_data_import_api_rejects_empty_kean_myprogress_extension_payload(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/data-imports",
        json={
            "student_profile_id": str(seed_uuid("student-profile:mock-student")),
            "import_type": "DEGREE_AUDIT_EXPORT",
            "file_name": "kean-student-portal-my-progress-empty.json",
            "file_mime_type": "application/json",
            "content": json.dumps(
                {
                    "source_type": "BROWSER_EXTENSION",
                    "staging_only": True,
                    "page_type": "KEAN_MY_PROGRESS_PAGE",
                    "courseRows": [],
                    "requirements": [],
                    "warnings": [],
                }
            ),
            "source_type": "BROWSER_EXTENSION",
            "source_reference": (
                "KEAN_STUDENT_PORTAL browser extension import: "
                "https://kean-ss.colleague.elluciancloud.com/Student/Planning/Programs/MyProgress"
            ),
            "page_type": "KEAN_MY_PROGRESS_PAGE",
            "extracted_record_count": 0,
            "visible_row_count": 85,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "missing_myprogress_payload"


def test_failed_kean_myprogress_validation_blocks_downstream_application(
    session: Session,
) -> None:
    service = DataImportApplicationService(session)

    run = service.create_import(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        import_type=DataImportType.DEGREE_AUDIT_EXPORT,
        file_name="kean-student-portal-my-progress.json",
        file_mime_type="application/json",
        content=failed_kean_myprogress_json(),
        source_type=SourceType.BROWSER_EXTENSION,
        source_reference=(
            "KEAN_STUDENT_PORTAL browser extension import: "
            "https://kean-ss.colleague.elluciancloud.com/Student/Planning/Programs/MyProgress"
        ),
    )

    preview = session.scalar(
        select(ImportPreviewSummary).where(ImportPreviewSummary.data_import_run_id == run.id)
    )
    assert preview is not None
    assert preview.summary_payload["real_import_status"] == (
        "REAL_IMPORTED_DATA_REQUIRES_EXCEPTION_REVIEW"
    )
    assert preview.summary_payload["can_apply_verified_import"] is False
    assert preview.summary_payload["downstream_analysis_allowed"] is False
    assert preview.summary_payload["exception_count"] == 2

    review_service = DataReviewApplicationService(session)
    review = review_service.create_review_session(
        data_import_run_id=run.id,
        reviewer_label="Kean student self-review",
    )
    review_record = session.scalars(
        select(ImportedRecordReview)
        .where(ImportedRecordReview.review_session_id == review.id)
        .order_by(ImportedRecordReview.created_at, ImportedRecordReview.id)
    ).first()
    assert review_record is not None
    assert review_record.decision is ImportedRecordReviewDecision.UNREVIEWED
    assert review_record.requires_advisor_confirmation is True

    review_service.update_record_review(
        review_session_id=review.id,
        record_review_id=review_record.id,
        decision=ImportedRecordReviewDecision.CONFIRMED,
    )
    result = review_service.apply_review_session(review.id, dry_run=True)
    assert result.applied_records
    assert {record.reason_code for record in result.applied_records} == {"IMPORT_VALIDATION_FAILED"}
