from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.config import settings
from app.schemas.pairing import (
    PairingCompleteRequest,
    PairingCompleteResponse,
    PairingSessionResponse,
    PairingStatusResponse,
)
from app.security.pairing import (
    PAIRING_PROTOCOL_VERSION,
    PairingError,
    PairingStore,
    extension_id_from_origin,
)

router = APIRouter(prefix="/local/pairing", tags=["local-pairing"])


def _origin(request: Request) -> str | None:
    return request.headers.get("origin")


def _require_desktop_origin(request: Request) -> None:
    origin = _origin(request)
    if origin not in settings.desktop_origin_list:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "desktop_origin_required",
                "message": "Pairing management requires the local desktop UI.",
            },
        )


def _require_extension_origin(request: Request) -> str:
    extension_id = extension_id_from_origin(_origin(request))
    if extension_id is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "extension_origin_required",
                "message": "Pairing completion requires a Chromium Extension origin.",
            },
        )
    return extension_id


def _pairing_error(error: PairingError) -> HTTPException:
    return HTTPException(
        status_code=error.status_code, detail={"code": error.code, "message": error.message}
    )


@router.get("/status", response_model=PairingStatusResponse)
def pairing_status() -> PairingStatusResponse:
    status = PairingStore().status()
    return PairingStatusResponse(
        paired=status.paired,
        extension_id=status.extension_id,
        protocol_version=status.protocol_version,
    )


@router.post("/session", response_model=PairingSessionResponse)
def create_pairing_session(request: Request) -> PairingSessionResponse:
    _require_desktop_origin(request)
    code, expires_at = PairingStore().create_code()
    return PairingSessionResponse(
        code=code,
        expires_at=expires_at,
        protocol_version=PAIRING_PROTOCOL_VERSION,
    )


@router.post("/complete", response_model=PairingCompleteResponse)
def complete_pairing(request: Request, payload: PairingCompleteRequest) -> PairingCompleteResponse:
    extension_id = _require_extension_origin(request)
    try:
        completion = PairingStore().complete(payload.code, extension_id, payload.protocol_version)
    except PairingError as error:
        raise _pairing_error(error) from error
    return PairingCompleteResponse(
        credential=completion.credential,
        protocol_version=completion.protocol_version,
        extension_id=completion.extension_id,
    )


@router.post("/revoke", response_model=PairingStatusResponse)
def revoke_pairing(request: Request) -> PairingStatusResponse:
    _require_desktop_origin(request)
    PairingStore().revoke()
    status = PairingStore().status()
    return PairingStatusResponse(
        paired=status.paired,
        extension_id=status.extension_id,
        protocol_version=status.protocol_version,
    )
