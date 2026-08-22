import pytest
from pydantic import ValidationError

from app.config import (
    APP_DATA_DIR_NAME,
    APP_ID,
    APPLICATION_VERSION,
    FUTURE_DATA_ROOT,
    LOCAL_DESKTOP_DATABASE_URL,
    LOCAL_DEVELOPMENT_DATABASE_URL,
    Settings,
)


def test_settings_accept_local_development_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment == "development"
    assert settings.product_mode == "LOCAL_DESKTOP"
    assert settings.auth_mode == "local"
    assert settings.database_url == LOCAL_DESKTOP_DATABASE_URL
    assert settings.is_local_database is True
    assert settings.api_host == "127.0.0.1"
    assert settings.cors_origin_list == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3010",
        "http://127.0.0.1:3010",
        "http://localhost:3011",
        "http://127.0.0.1:3011",
    ]
    assert "http://tauri.localhost" in settings.desktop_origin_list


@pytest.mark.parametrize(
    "database_url",
    [
        "",
        "sqlite:///tmp.db",
        "postgresql://sapsos:sapsos_dev_password@localhost:5432/sapsos",
    ],
)
def test_settings_reject_missing_or_unsupported_database_url(database_url: str) -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL must use"):
        Settings(database_url=database_url)


def test_settings_reject_unknown_environment() -> None:
    with pytest.raises(ValidationError, match="ENVIRONMENT must be one of"):
        Settings(environment="prod")


def test_production_rejects_local_database_default() -> None:
    with pytest.raises(ValidationError, match="Production DATABASE_URL must not use"):
        Settings(
            environment="production",
            product_mode="SERVER",
            auth_mode="bearer",
            database_url=LOCAL_DEVELOPMENT_DATABASE_URL,
            cors_origins="https://planner.example.edu",
        )


def test_server_requires_bearer_authentication() -> None:
    with pytest.raises(ValidationError, match="SERVER PRODUCT_MODE must use AUTH_MODE=bearer"):
        Settings(
            environment="production",
            product_mode="SERVER",
            auth_mode="local",
            database_url="postgresql+psycopg://sapsos:prod-password@db.example.edu:5432/sapsos",
            cors_origins="https://planner.example.edu",
        )


def test_production_local_desktop_is_valid_without_bearer_authentication() -> None:
    settings = Settings(
        environment="production",
        product_mode="LOCAL_DESKTOP",
        auth_mode="local",
        cors_origins="http://localhost:3000",
    )

    assert settings.product_mode == "LOCAL_DESKTOP"


@pytest.mark.parametrize("api_host", ["0.0.0.0", "192.168.1.20", "planner.example.edu"])
def test_local_desktop_rejects_non_loopback_api_hosts(api_host: str) -> None:
    with pytest.raises(ValidationError, match="LOCAL_DESKTOP API_HOST"):
        Settings(api_host=api_host)


def test_server_accepts_container_host_and_requires_bearer() -> None:
    settings = Settings(
        product_mode="SERVER",
        auth_mode="bearer",
        api_host="0.0.0.0",
        database_url=LOCAL_DEVELOPMENT_DATABASE_URL,
        cors_origins="http://localhost:3000",
    )

    assert settings.api_host == "0.0.0.0"


def test_stable_local_app_contracts() -> None:
    assert APP_ID == "com.sapsos.smart-academic-planner"
    assert APP_DATA_DIR_NAME == "SAPSOS"
    assert FUTURE_DATA_ROOT == "%LOCALAPPDATA%\\SAPSOS\\"


def test_openapi_retains_server_bearer_security_scheme() -> None:
    from app.main import app

    security_schemes = app.openapi()["components"]["securitySchemes"]

    assert "HTTPBearer" in security_schemes
    assert security_schemes["HTTPBearer"]["scheme"] == "bearer"


def test_openapi_reports_the_desktop_application_version() -> None:
    from app.main import app

    assert app.openapi()["info"]["version"] == APPLICATION_VERSION == "0.1.6"


@pytest.mark.parametrize("cors_origins", ["", "*", "https://planner.example.edu,*"])
def test_settings_reject_overbroad_cors_origins(cors_origins: str) -> None:
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(cors_origins=cors_origins)


@pytest.mark.parametrize(
    "cors_origins",
    [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
)
def test_production_rejects_localhost_cors_origins(cors_origins: str) -> None:
    with pytest.raises(ValidationError, match="Production SERVER CORS_ORIGINS must not include"):
        Settings(
            environment="production",
            product_mode="SERVER",
            auth_mode="bearer",
            database_url="postgresql+psycopg://sapsos:prod-password@db.example.edu:5432/sapsos",
            cors_origins=cors_origins,
        )


def test_production_settings_accept_explicit_safe_origins() -> None:
    settings = Settings(
        environment="production",
        product_mode="SERVER",
        auth_mode="bearer",
        database_url="postgresql+psycopg://sapsos:prod-password@db.example.edu:5432/sapsos",
        cors_origins="https://planner.example.edu, https://advisor.example.edu",
    )

    assert settings.cors_origin_list == [
        "https://planner.example.edu",
        "https://advisor.example.edu",
    ]
