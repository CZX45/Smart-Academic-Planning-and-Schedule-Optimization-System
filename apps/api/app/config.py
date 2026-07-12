from typing import Self
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DEVELOPMENT_DATABASE_URL = (
    "postgresql+psycopg://sapsos:sapsos_dev_password@localhost:5432/sapsos"
)
LOCAL_DEVELOPMENT_WEB_PORTS = (3000, 3001, 3010, 3011)
LOCAL_DEVELOPMENT_CORS_ORIGINS = ",".join(
    f"http://{host}:{port}"
    for port in LOCAL_DEVELOPMENT_WEB_PORTS
    for host in ("localhost", "127.0.0.1")
)
ALLOWED_ENVIRONMENTS = {"development", "test", "staging", "production"}
ALLOWED_AUTH_MODES = {"development", "bearer"}
LOCALHOST_NAMES = {"localhost", "127.0.0.1", "::1"}


def parse_cors_origins(value: str) -> list[str]:
    return [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]


class Settings(BaseSettings):
    app_name: str = "Smart Academic Planning API"
    database_url: str = LOCAL_DEVELOPMENT_DATABASE_URL
    database_connect_timeout_seconds: int = Field(default=3, gt=0, le=60)
    environment: str = "development"
    cors_origins: str = LOCAL_DEVELOPMENT_CORS_ORIGINS
    auth_mode: str = "development"
    bearer_token_min_length: int = Field(default=32, ge=32, le=256)

    model_config = SettingsConfigDict(env_file=("../../.env", ".env"), extra="ignore")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_ENVIRONMENTS:
            allowed = ", ".join(sorted(ALLOWED_ENVIRONMENTS))
            raise ValueError(f"ENVIRONMENT must be one of: {allowed}")
        return normalized

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use postgresql+psycopg://")
        return normalized

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = parse_cors_origins(value)
        if not origins:
            raise ValueError("CORS_ORIGINS must include at least one explicit origin")
        for origin in origins:
            if "*" in origin:
                raise ValueError("CORS_ORIGINS must not include wildcard origins")
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("CORS_ORIGINS must contain http(s) origins")
        return ",".join(origins)

    @field_validator("auth_mode")
    @classmethod
    def validate_auth_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_AUTH_MODES:
            allowed = ", ".join(sorted(ALLOWED_AUTH_MODES))
            raise ValueError(f"AUTH_MODE must be one of: {allowed}")
        return normalized

    @model_validator(mode="after")
    def validate_production_defaults(self) -> Self:
        if self.environment != "production":
            return self
        if self.auth_mode != "bearer":
            raise ValueError("Production AUTH_MODE must be bearer")
        if self.database_url == LOCAL_DEVELOPMENT_DATABASE_URL:
            raise ValueError("Production DATABASE_URL must not use the local development default")
        for origin in self.cors_origin_list:
            parsed = urlparse(origin)
            if parsed.hostname in LOCALHOST_NAMES:
                raise ValueError("Production CORS_ORIGINS must not include localhost origins")
            if parsed.scheme != "https":
                raise ValueError("Production CORS_ORIGINS must use https origins")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return parse_cors_origins(self.cors_origins)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
