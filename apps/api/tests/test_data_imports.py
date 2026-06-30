from collections.abc import Generator
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.academic import (
    AuditWarningSeverity,
    DataImportFile,
    DataImportRun,
    DataImportStatus,
    DataImportStorageStrategy,
    DataImportType,
    ImportedRecord,
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
