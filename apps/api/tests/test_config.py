import pytest
from pydantic import ValidationError

from app.config import LOCAL_DEVELOPMENT_DATABASE_URL, Settings


def test_settings_accept_local_development_defaults() -> None:
    settings = Settings()

    assert settings.environment == "development"
    assert settings.cors_origin_list == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


@pytest.mark.parametrize(
    "database_url",
    [
        "",
        "sqlite:///tmp.db",
        "postgresql://sapsos:sapsos_dev_password@localhost:5432/sapsos",
    ],
)
def test_settings_reject_missing_or_unsupported_database_url(database_url: str) -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL must use postgresql\\+psycopg://"):
        Settings(database_url=database_url)


def test_settings_reject_unknown_environment() -> None:
    with pytest.raises(ValidationError, match="ENVIRONMENT must be one of"):
        Settings(environment="prod")


def test_production_rejects_local_database_default() -> None:
    with pytest.raises(ValidationError, match="Production DATABASE_URL must not use"):
        Settings(
            environment="production",
            database_url=LOCAL_DEVELOPMENT_DATABASE_URL,
            cors_origins="https://planner.example.edu",
        )


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
    with pytest.raises(ValidationError, match="Production CORS_ORIGINS must not include"):
        Settings(
            environment="production",
            database_url="postgresql+psycopg://sapsos:prod-password@db.example.edu:5432/sapsos",
            cors_origins=cors_origins,
        )


def test_production_settings_accept_explicit_safe_origins() -> None:
    settings = Settings(
        environment="production",
        database_url="postgresql+psycopg://sapsos:prod-password@db.example.edu:5432/sapsos",
        cors_origins="https://planner.example.edu, https://advisor.example.edu",
    )

    assert settings.cors_origin_list == [
        "https://planner.example.edu",
        "https://advisor.example.edu",
    ]
