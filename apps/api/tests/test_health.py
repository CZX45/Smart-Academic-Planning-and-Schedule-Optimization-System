from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.main import app


def test_health_endpoint() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database_configured"] is True
    assert "database_url" not in payload


def test_ready_endpoint_when_database_is_available(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("app.main.check_database_ready", lambda: True)

    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "Smart Academic Planning API",
        "database_ready": True,
    }


def test_ready_endpoint_when_database_is_unavailable(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("app.main.check_database_ready", lambda: False)

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "service": "Smart Academic Planning API",
        "database_ready": False,
    }
