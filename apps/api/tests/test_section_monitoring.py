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
    SectionMonitorAlert,
    SectionMonitorAlertType,
    SectionMonitorSnapshot,
    SectionMonitorTarget,
    SourceType,
)
from app.seed_dev import seed_mock_data, seed_uuid
from app.services.section_monitoring.engine import SectionMonitoringApplicationService
from app.services.section_monitoring.exceptions import SectionMonitoringValidationError


class SnapshotComparisonLogRecord(Protocol):
    student_profile_id: str
    source_type: str
    snapshot_count: int
    alert_count: int


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


def snapshot_payload(
    *,
    status: str,
    seats_available: int,
    waitlist_available: int,
    meeting_time: str = "09:00-10:15",
    instructor: str = "Mock Instructor",
    location: str = "Mock Hall 101",
) -> dict[str, object]:
    return {
        "course_code": "FIN 403",
        "section_code": "001",
        "term": "2025FA",
        "status": status,
        "seats_available": seats_available,
        "seats_capacity": 30,
        "waitlist_available": waitlist_available,
        "waitlist_capacity": 10,
        "meeting_days": "MONDAY",
        "meeting_time": meeting_time,
        "location": location,
        "instructor": instructor,
        "raw_payload": {
            "source_label": "Visible section-search table",
            "status": status,
        },
    }


def alert_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(SectionMonitorAlert)) or 0


def test_section_monitoring_models_are_advisory_and_never_official(
    session: Session,
) -> None:
    target = SectionMonitorTarget(
        id=seed_uuid("section-monitor-target:test-model"),
        student_profile_id=seed_uuid("student-profile:mock-student"),
        course_code="FIN 403",
        section_code="001",
        term="2025FA",
        title="Mock International Finance",
        instructor="Mock Instructor",
        status="CLOSED",
        is_active=True,
        source_type=SourceType.STUDENT_PROVIDED,
        is_official=False,
        source_confidence="student_provided",
    )
    session.add(target)
    session.flush()

    snapshot = SectionMonitorSnapshot(
        id=seed_uuid("section-monitor-snapshot:test-model"),
        student_profile_id=seed_uuid("student-profile:mock-student"),
        target_id=target.id,
        data_import_id=None,
        course_code=target.course_code,
        section_code=target.section_code,
        term=target.term,
        status="CLOSED",
        seats_available=0,
        seats_capacity=30,
        waitlist_available=5,
        waitlist_capacity=10,
        meeting_days="MONDAY",
        meeting_time="09:00-10:15",
        location="Mock Hall 101",
        instructor="Mock Instructor",
        raw_payload={"source_label": "Visible section-search table"},
        snapshot_hash="model-snapshot-hash",
        source_type=SourceType.BROWSER_EXTENSION,
        is_official=False,
        source_reference="Browser extension visible-page import",
        source_confidence="browser_extension",
    )
    session.add(snapshot)
    session.commit()

    reloaded = session.get(SectionMonitorSnapshot, snapshot.id)
    assert reloaded is not None
    assert reloaded.source_type is SourceType.BROWSER_EXTENSION
    assert reloaded.is_official is False
    assert reloaded.raw_payload["source_label"] == "Visible section-search table"

    bad_snapshot = SectionMonitorSnapshot(
        id=seed_uuid("section-monitor-snapshot:bad-official"),
        student_profile_id=seed_uuid("student-profile:mock-student"),
        target_id=target.id,
        course_code=target.course_code,
        section_code=target.section_code,
        term=target.term,
        status="OPEN",
        raw_payload={},
        snapshot_hash="bad-official-hash",
        source_type=SourceType.OFFICIAL,
        is_official=True,
        source_confidence="official",
    )
    session.add(bad_snapshot)
    with pytest.raises(IntegrityError):
        session.commit()


def test_section_monitoring_service_creates_targets_and_archives_them(
    session: Session,
) -> None:
    service = SectionMonitoringApplicationService(session)

    target = service.create_target(
        student_profile_id=seed_uuid("student-profile:mock-student"),
        course_code="FIN 403",
        section_code="001",
        term="2025FA",
        title="Mock International Finance",
        instructor="Mock Instructor",
        status="CLOSED",
    )
    session.commit()

    assert target.is_active is True
    assert target.is_official is False
    assert service.list_targets(seed_uuid("student-profile:mock-student")) == [target]
    with pytest.raises(SectionMonitoringValidationError) as duplicate_error:
        service.create_target(
            student_profile_id=seed_uuid("student-profile:mock-student"),
            course_code="fin 403",
            section_code="001",
            term="2025fa",
        )
    assert duplicate_error.value.code == "duplicate_target"

    archived = service.update_target(target.id, is_active=False)
    session.commit()

    assert archived.is_active is False
    assert service.list_targets(seed_uuid("student-profile:mock-student")) == [archived]


def test_section_monitoring_service_compares_snapshots_and_deduplicates_alerts(
    session: Session,
) -> None:
    service = SectionMonitoringApplicationService(session)
    student_id = seed_uuid("student-profile:mock-student")
    service.create_target(
        student_profile_id=student_id,
        course_code="FIN 403",
        section_code="001",
        term="2025FA",
        title="Mock International Finance",
        instructor="Mock Instructor",
        status="CLOSED",
    )
    session.commit()

    first = service.compare_snapshots(
        student_profile_id=student_id,
        snapshots=[snapshot_payload(status="CLOSED", seats_available=0, waitlist_available=5)],
        source_type=SourceType.BROWSER_EXTENSION,
    )
    session.commit()
    assert len(first.snapshots) == 1
    assert first.alerts == []

    second = service.compare_snapshots(
        student_profile_id=student_id,
        snapshots=[
            snapshot_payload(
                status="OPEN",
                seats_available=4,
                waitlist_available=2,
                meeting_time="10:00-11:15",
                instructor="New Instructor",
                location="Mock Hall 202",
            )
        ],
        source_type=SourceType.BROWSER_EXTENSION,
    )
    session.commit()

    alert_types = {alert.alert_type for alert in second.alerts}
    assert {
        SectionMonitorAlertType.SECTION_OPENED,
        SectionMonitorAlertType.SEATS_CHANGED,
        SectionMonitorAlertType.WAITLIST_CHANGED,
        SectionMonitorAlertType.MEETING_TIME_CHANGED,
        SectionMonitorAlertType.INSTRUCTOR_CHANGED,
        SectionMonitorAlertType.LOCATION_CHANGED,
    } <= alert_types
    assert all(alert.is_advisory for alert in second.alerts)
    assert all(alert.requires_manual_review for alert in second.alerts)
    assert all("manual" in alert.message.lower() for alert in second.alerts)
    assert not any("automatically register" in alert.message.lower() for alert in second.alerts)
    seats_alert = next(
        alert
        for alert in second.alerts
        if alert.alert_type is SectionMonitorAlertType.SEATS_CHANGED
    )
    assert seats_alert.previous_value == "0"
    assert seats_alert.current_value == "4"

    count_after_second = alert_count(session)
    duplicate = service.compare_snapshots(
        student_profile_id=student_id,
        snapshots=[
            snapshot_payload(
                status="OPEN",
                seats_available=4,
                waitlist_available=2,
                meeting_time="10:00-11:15",
                instructor="New Instructor",
                location="Mock Hall 202",
            )
        ],
        source_type=SourceType.BROWSER_EXTENSION,
    )
    session.commit()

    assert duplicate.alerts == []
    assert alert_count(session) == count_after_second

    closed = service.compare_snapshots(
        student_profile_id=student_id,
        snapshots=[snapshot_payload(status="CLOSED", seats_available=0, waitlist_available=3)],
        source_type=SourceType.BROWSER_EXTENSION,
    )
    session.commit()

    assert any(
        alert.alert_type is SectionMonitorAlertType.SECTION_CLOSED for alert in closed.alerts
    )


def test_section_monitoring_api_exposes_targets_snapshots_alerts_and_acknowledgement(
    client: TestClient,
) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))
    target_response = client.post(
        "/api/v1/section-monitoring/targets",
        json={
            "student_profile_id": student_id,
            "course_code": "FIN 403",
            "section_code": "001",
            "term": "2025FA",
            "title": "Mock International Finance",
            "instructor": "Mock Instructor",
            "status": "CLOSED",
        },
    )
    assert target_response.status_code == 201
    target = target_response.json()
    UUID(target["id"])
    assert target["is_active"] is True
    assert target["is_official"] is False
    assert "registration" not in target

    targets = client.get(
        "/api/v1/section-monitoring/targets",
        params={"student_profile_id": student_id},
    )
    assert targets.status_code == 200
    assert [item["id"] for item in targets.json()] == [target["id"]]

    archive = client.patch(
        f"/api/v1/section-monitoring/targets/{target['id']}",
        json={"is_active": False},
    )
    assert archive.status_code == 200
    assert archive.json()["is_active"] is False

    first = client.post(
        "/api/v1/section-monitoring/snapshots/compare",
        json={
            "student_profile_id": student_id,
            "source_type": "BROWSER_EXTENSION",
            "snapshots": [
                snapshot_payload(status="CLOSED", seats_available=0, waitlist_available=5)
            ],
        },
    )
    assert first.status_code == 201
    assert first.json()["alerts"] == []
    assert first.json()["snapshots"][0]["source_type"] == "BROWSER_EXTENSION"
    assert first.json()["snapshots"][0]["is_official"] is False
    assert any("not official" in item.lower() for item in first.json()["disclaimers"])

    second = client.post(
        "/api/v1/section-monitoring/snapshots/compare",
        json={
            "student_profile_id": student_id,
            "source_type": "BROWSER_EXTENSION",
            "snapshots": [snapshot_payload(status="OPEN", seats_available=4, waitlist_available=2)],
        },
    )
    assert second.status_code == 201
    alerts = second.json()["alerts"]
    assert {alert["alert_type"] for alert in alerts} >= {"SECTION_OPENED", "SEATS_CHANGED"}
    assert all(alert["is_advisory"] for alert in alerts)
    assert all(alert["requires_manual_review"] for alert in alerts)

    listed_alerts = client.get(
        "/api/v1/section-monitoring/alerts",
        params={"student_profile_id": student_id},
    )
    assert listed_alerts.status_code == 200
    assert len(listed_alerts.json()) == len(alerts)

    acknowledged = client.patch(
        f"/api/v1/section-monitoring/alerts/{alerts[0]['id']}",
        json={"is_acknowledged": True},
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["is_acknowledged"] is True
    assert acknowledged.json()["acknowledged_at"] is not None


def test_section_monitoring_api_does_not_introduce_registration_automation() -> None:
    paths = app.openapi()["paths"]
    monitoring_paths = [path for path in paths if path.startswith("/api/v1/section-monitoring")]
    assert monitoring_paths
    prohibited_path_terms = [
        "register",
        "registration",
        "drop",
        "swap",
        "waitlist/join",
        "reserve",
        "submit",
        "login",
        "poll",
    ]
    for path in monitoring_paths:
        normalized = path.lower()
        assert not any(term in normalized for term in prohibited_path_terms)

    forbidden_model_fields = {
        "portal_password",
        "credential",
        "registration_action",
        "portal_action",
        "auto_register",
        "auto_drop",
        "auto_swap",
        "seat_reservation",
        "polling_interval",
    }
    for model in (SectionMonitorTarget, SectionMonitorSnapshot, SectionMonitorAlert):
        assert forbidden_model_fields.isdisjoint(model.__table__.columns.keys())


def test_section_monitoring_logs_safe_comparison_metadata(
    session: Session,
    caplog: LogCaptureFixture,
) -> None:
    service = SectionMonitoringApplicationService(session)
    student_id = seed_uuid("student-profile:mock-student")

    with caplog.at_level("INFO", logger="app.services.section_monitoring.engine"):
        result = service.compare_snapshots(
            student_profile_id=student_id,
            source_type=SourceType.BROWSER_EXTENSION,
            snapshots=[
                snapshot_payload(status="CLOSED", seats_available=0, waitlist_available=5),
            ],
        )

    assert len(result.snapshots) == 1
    records = [
        record
        for record in caplog.records
        if record.message == "section_monitoring.snapshots_compared"
    ]
    assert len(records) == 1
    log_record = cast(SnapshotComparisonLogRecord, records[0])
    assert log_record.student_profile_id == str(student_id)
    assert log_record.source_type == "BROWSER_EXTENSION"
    assert log_record.snapshot_count == 1
    assert log_record.alert_count == 0
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "FIN 403" not in log_text
    assert "Visible section-search table" not in log_text
