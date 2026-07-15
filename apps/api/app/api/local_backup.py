from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.db.session import engine
from app.services.local_backup import (
    BACKUP_MEDIA_TYPE,
    BackupError,
    BackupStatus,
    backup_status,
    cleanup_backup_archive,
    create_backup_archive,
)

router = APIRouter(prefix="/api/v1/local-backup", tags=["local-backup"])


@router.get("/status", response_model=BackupStatus)
def get_backup_status() -> BackupStatus:
    return backup_status(engine)


@router.post(
    "",
    responses={
        200: {"content": {BACKUP_MEDIA_TYPE: {}}},
        503: {"description": "Backup unavailable"},
    },
)
def create_backup() -> FileResponse:
    try:
        archive_path, manifest = create_backup_archive(engine)
    except BackupError as error:
        status_code = 503 if error.code == "local_desktop_only" else 409
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        ) from error
    filename = f"SAPSOS-backup-{manifest.created_at.strftime('%Y%m%d-%H%M%S')}.sapsos-backup"
    return FileResponse(
        archive_path,
        media_type=BACKUP_MEDIA_TYPE,
        filename=filename,
        background=BackgroundTask(cleanup_backup_archive, archive_path),
    )
