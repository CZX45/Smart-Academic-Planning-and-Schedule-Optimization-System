from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.db.session import engine
from app.services.local_backup import (
    BackupError,
    RestoreConfirmation,
    RestorePreview,
    RestoreStageResult,
    RestoreStatus,
    cancel_restore,
    confirm_restore,
    restore_status,
    validate_and_stage_restore,
)

router = APIRouter(prefix="/api/v1/local-backup/restore", tags=["local-restore"])


def _raise(error: BackupError) -> HTTPException:
    status = 503 if error.code == "local_desktop_only" else 409
    return HTTPException(status_code=status, detail={"code": error.code, "message": error.message})


@router.get("/status", response_model=RestoreStatus)
def get_restore_status() -> RestoreStatus:
    return restore_status(engine)


@router.post("/validate", response_model=RestorePreview)
def validate_restore(file: Annotated[UploadFile, File(...)]) -> RestorePreview:
    try:
        return validate_and_stage_restore(engine, file)
    except BackupError as error:
        raise _raise(error) from error


@router.delete("/sessions/{session_id}", status_code=204)
def cancel_restore_session(session_id: UUID) -> None:
    try:
        cancel_restore(engine, session_id)
    except BackupError as error:
        raise _raise(error) from error


@router.post("/sessions/{session_id}/confirm", response_model=RestoreStageResult)
def confirm_restore_session(session_id: UUID, request: RestoreConfirmation) -> RestoreStageResult:
    try:
        return confirm_restore(engine, session_id, request.confirmation)
    except BackupError as error:
        raise _raise(error) from error
