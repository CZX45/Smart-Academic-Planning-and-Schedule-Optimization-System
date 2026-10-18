from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app


def test_api_sets_safe_default_security_headers() -> None:
    response = TestClient(app).get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == "geolocation=(), microphone=(), camera=()"
    assert response.headers["cache-control"] == "no-store"


def test_local_web_fallback_port_is_allowed_by_cors() -> None:
    cors_app = FastAPI()
    cors_app.add_middleware(
        CORSMiddleware,
        allow_origins=Settings(_env_file=None).cors_origin_list,
        allow_credentials=False,
        allow_methods=["DELETE", "GET", "PATCH", "POST"],
        allow_headers=["authorization", "content-type"],
    )

    @cors_app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    response = TestClient(cors_app).get(
        "/health",
        headers={"Origin": "http://127.0.0.1:3011"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3011"


def test_cors_preflight_allows_authorization_header() -> None:
    cors_app = FastAPI()
    cors_app.add_middleware(
        CORSMiddleware,
        allow_origins=Settings(_env_file=None).cors_origin_list,
        allow_credentials=False,
        allow_methods=["DELETE", "GET", "PATCH", "POST"],
        allow_headers=["authorization", "content-type"],
    )

    @cors_app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    response = TestClient(cors_app).options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:3011",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3011"
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
