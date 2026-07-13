from datetime import datetime

from pydantic import BaseModel, Field


class PairingStatusResponse(BaseModel):
    paired: bool
    extension_id: str | None = None
    protocol_version: int = Field(ge=1)


class PairingSessionResponse(BaseModel):
    code: str = Field(min_length=20, max_length=64)
    expires_at: datetime
    protocol_version: int = Field(ge=1)


class PairingCompleteRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    protocol_version: int = Field(ge=1)


class PairingCompleteResponse(BaseModel):
    credential: str = Field(min_length=20)
    protocol_version: int = Field(ge=1)
    extension_id: str = Field(min_length=32, max_length=32)


class PairingErrorResponse(BaseModel):
    code: str
    message: str
