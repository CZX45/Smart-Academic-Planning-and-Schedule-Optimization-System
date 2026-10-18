from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    service: str
    database_configured: bool


class ReadinessResponse(BaseModel):
    status: str = Field(examples=["ready", "not_ready"])
    service: str
    database_ready: bool
