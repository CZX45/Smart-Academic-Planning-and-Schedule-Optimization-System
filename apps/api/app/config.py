from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Smart Academic Planning API"
    database_url: str = "postgresql+psycopg://sapsos:sapsos_dev_password@localhost:5432/sapsos"
    database_connect_timeout_seconds: int = 3
    environment: str = "development"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(env_file=("../../.env", ".env"), extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
