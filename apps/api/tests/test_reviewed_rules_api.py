from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


def payload() -> dict[str, Any]:
    return {
        "rule_set_id": str(uuid4()),
        "version": 1,
        "source": {
            "institution_id": "synthetic-institution",
            "program_id": "synthetic-program",
            "program_name": "Synthetic Program",
            "catalog_year": "2026",
            "source_type": "MOCK",
            "source_title": "Synthetic fixture",
            "source_url_or_document_id": "fixture:synthetic-program-2026",
            "source_location": "fixture:requirements",
            "source_evidence": "Synthetic test evidence; not university policy.",
            "imported_at": datetime.now(UTC).isoformat(),
        },
        "courses": [],
        "requirements": [],
        "unsupported_statements": [],
    }


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection: Any, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_staging_requires_explicit_review_and_activation(client: TestClient) -> None:
    staged = client.post("/api/v1/reviewed-rule-sets", json=payload())
    assert staged.status_code == 201
    rule_set_id = staged.json()["rule_set"]["rule_set_id"]
    assert staged.json()["rule_set"]["lifecycle"] == "DRAFT"

    blocked = client.post(f"/api/v1/reviewed-rule-sets/{rule_set_id}/activate")
    assert blocked.status_code == 409

    reviewed = client.post(f"/api/v1/reviewed-rule-sets/{rule_set_id}/review")
    assert reviewed.status_code == 200
    assert reviewed.json()["rule_set"]["lifecycle"] == "REVIEWED"

    activated = client.post(f"/api/v1/reviewed-rule-sets/{rule_set_id}/activate")
    assert activated.status_code == 200
    assert activated.json()["rule_set"]["lifecycle"] == "ACTIVE"
