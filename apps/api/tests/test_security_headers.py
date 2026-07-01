from fastapi.testclient import TestClient

from app.main import app


def test_api_sets_safe_default_security_headers() -> None:
    response = TestClient(app).get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == "geolocation=(), microphone=(), camera=()"
    assert response.headers["cache-control"] == "no-store"
