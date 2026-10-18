from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.academic import (
    AuthApiToken,
    AuthTenant,
    AuthUser,
    AuthUserRole,
    SourceType,
    StudentProfile,
    StudentProfileAccess,
)
from app.security.auth import token_hash
from app.seed_dev import seed_mock_data, seed_uuid

ALLOWED_TOKEN = "allowed-test-token-with-at-least-thirty-two-chars"
DENIED_TOKEN = "denied-test-token-with-at-least-thirty-two-chars"
REVOKED_TOKEN = "revoked-test-token-with-at-least-thirty-two-chars"
NULL_TENANT_ADMIN_TOKEN = "null-tenant-admin-token-with-at-least-thirty-two-chars"


@pytest.fixture()
def auth_client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
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
        seed_auth_data(seed_session)

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session() as db:
            yield db

    monkeypatch.setattr(settings, "product_mode", "SERVER")
    monkeypatch.setattr(settings, "auth_mode", "bearer")
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def seed_auth_data(session: Session) -> None:
    institution_id = seed_uuid("institution:mock-university")
    tenant = AuthTenant(
        id=seed_uuid("auth-tenant:mocku"),
        institution_id=institution_id,
        slug="mocku",
        display_name="Mock University",
        is_active=True,
    )
    null_institution_tenant = AuthTenant(
        id=seed_uuid("auth-tenant:null-institution"),
        institution_id=None,
        slug="null-institution",
        display_name="Unscoped Tenant",
        is_active=True,
    )
    allowed_user = AuthUser(
        id=seed_uuid("auth-user:allowed-student"),
        tenant_id=tenant.id,
        external_subject="student|allowed",
        email="allowed@example.edu",
        display_name="Allowed Student",
        role=AuthUserRole.STUDENT,
        is_active=True,
    )
    denied_user = AuthUser(
        id=seed_uuid("auth-user:denied-student"),
        tenant_id=tenant.id,
        external_subject="student|denied",
        email="denied@example.edu",
        display_name="Denied Student",
        role=AuthUserRole.STUDENT,
        is_active=True,
    )
    null_tenant_admin = AuthUser(
        id=seed_uuid("auth-user:null-tenant-admin"),
        tenant_id=null_institution_tenant.id,
        external_subject="tenant-admin|null-institution",
        email="admin@example.edu",
        display_name="Unscoped Tenant Admin",
        role=AuthUserRole.TENANT_ADMIN,
        is_active=True,
    )
    student_id = seed_uuid("student-profile:mock-student")
    session.add_all(
        [
            tenant,
            null_institution_tenant,
            allowed_user,
            denied_user,
            null_tenant_admin,
            StudentProfile(
                id=seed_uuid("student-profile:other-student"),
                home_institution_id=institution_id,
                home_campus_id=seed_uuid("campus:mock-main"),
                expected_graduation_term_id=None,
                external_ref="OTHER-STUDENT",
                display_name="Other Student",
                class_standing="SENIOR",
                source_type=SourceType.MOCK,
                is_official=False,
                source_reference="Auth authorization test fixture",
                source_confidence="mock",
            ),
        ]
    )
    session.flush()
    session.add_all(
        [
            AuthApiToken(
                id=seed_uuid("auth-token:allowed"),
                user_id=allowed_user.id,
                token_hash=token_hash(ALLOWED_TOKEN),
                label="allowed-test-token",
            ),
            AuthApiToken(
                id=seed_uuid("auth-token:denied"),
                user_id=denied_user.id,
                token_hash=token_hash(DENIED_TOKEN),
                label="denied-test-token",
            ),
            AuthApiToken(
                id=seed_uuid("auth-token:revoked"),
                user_id=allowed_user.id,
                token_hash=token_hash(REVOKED_TOKEN),
                label="revoked-test-token",
                revoked_at=datetime.now(UTC),
            ),
            AuthApiToken(
                id=seed_uuid("auth-token:null-tenant-admin"),
                user_id=null_tenant_admin.id,
                token_hash=token_hash(NULL_TENANT_ADMIN_TOKEN),
                label="null-tenant-admin-test-token",
            ),
            StudentProfileAccess(
                id=seed_uuid("student-access:allowed"),
                user_id=allowed_user.id,
                student_profile_id=student_id,
                role=AuthUserRole.STUDENT,
                grant_reason="Self-service student access test grant",
            ),
        ]
    )
    session.commit()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_bearer_mode_requires_authorization(auth_client: TestClient) -> None:
    response = auth_client.get("/api/v1/institutions")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "missing_bearer_token"


def test_local_desktop_does_not_require_authorization(
    auth_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "product_mode", "LOCAL_DESKTOP")
    monkeypatch.setattr(settings, "auth_mode", "local")

    response = auth_client.get("/api/v1/institutions")

    assert response.status_code != 401


def test_valid_bearer_token_can_read_public_catalog(auth_client: TestClient) -> None:
    response = auth_client.get("/api/v1/institutions", headers=auth_header(ALLOWED_TOKEN))

    assert response.status_code == 200
    assert response.json()[0]["code"] == "MOCKU"


def test_student_grant_allows_owned_student_object(auth_client: TestClient) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))

    response = auth_client.get(f"/api/v1/students/{student_id}", headers=auth_header(ALLOWED_TOKEN))

    assert response.status_code == 200
    assert response.json()["id"] == student_id


def test_student_grant_hides_unowned_student_object(auth_client: TestClient) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))

    response = auth_client.get(f"/api/v1/students/{student_id}", headers=auth_header(DENIED_TOKEN))

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "not_found"


def test_unscoped_tenant_admin_does_not_receive_global_student_access(
    auth_client: TestClient,
) -> None:
    student_id = str(seed_uuid("student-profile:mock-student"))

    response = auth_client.get(
        f"/api/v1/students/{student_id}",
        headers=auth_header(NULL_TENANT_ADMIN_TOKEN),
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "not_found"


def test_revoked_token_is_rejected(auth_client: TestClient) -> None:
    response = auth_client.get("/api/v1/institutions", headers=auth_header(REVOKED_TOKEN))

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_bearer_token"


def test_student_body_scope_blocks_unowned_mutation(auth_client: TestClient) -> None:
    other_student_id = str(seed_uuid("student-profile:other-student"))
    program_version_id = str(seed_uuid("program-version:bs-finance-2024"))

    response = auth_client.post(
        "/api/v1/degree-audits",
        headers=auth_header(ALLOWED_TOKEN),
        json={
            "student_profile_id": other_student_id,
            "program_version_id": program_version_id,
            "calculation_mode": "CURRENT",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "not_found"


def test_malformed_path_uuid_returns_validation_error_not_server_error(
    auth_client: TestClient,
) -> None:
    response = auth_client.get(
        "/api/v1/students/not-a-uuid",
        headers=auth_header(ALLOWED_TOKEN),
    )

    assert response.status_code == 422


def test_malformed_body_uuid_list_returns_validation_error_not_server_error(
    auth_client: TestClient,
) -> None:
    response = auth_client.post(
        "/api/v1/academic-plans/compare",
        headers=auth_header(ALLOWED_TOKEN),
        json={"academic_plan_ids": ["not-a-uuid"]},
    )

    assert response.status_code == 422
