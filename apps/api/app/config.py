from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Smart Academic Planning API"
    database_url: str = "postgresql+psycopg://sapsos:sapsos_dev_password@localhost:5432/sapsos"
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
