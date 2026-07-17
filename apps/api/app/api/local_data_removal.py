from __future__ import annotations

import json
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.config import APP_ID, settings
from app.services.local_data_removal import (
    CONFIRMATION_TEXT,
    FIXED_PLAN_PATH,
    LocalDataRemovalError,
    RemovalCategory,
    RemovalState,
    create_deletion_plan,
    is_validated_external_backup,
    resolve_app_data_root,
    serialize_plan,
    validate_app_data_root,
)

router = APIRouter(prefix="/api/v1/local-data-removal", tags=["local-data-removal"])
APPLICATION_VERSION = "0.1.0"
PLAN_PATH = FIXED_PLAN_PATH
PLAN_DIRECTORY = FIXED_PLAN_PATH.parent
ACTIVE_OPERATION_MARKERS = (
    "active-import.json",
    "active-review-apply.json",
    "active-schedule-write.json",
    "active-backup.json",
    "active-restore.json",
    "active-migration.json",
    "active-diagnostics-export.json",
    "active-pairing-mutation.json",
)


class LocalDataRemovalStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: RemovalState
    application_identity: Literal["com.sapsos.smart-academic-planner"] = APP_ID  # type: ignore[assignment]
    default_uninstall_preserves_data: bool = True
    confirmation_text: str = CONFIRMATION_TEXT
    categories: tuple[str, ...]
    external_files_preserved: tuple[str, ...]
    message: str


class PrepareLocalDataRemovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation: str = Field(min_length=1, max_length=64)
    backup_receipt: str = Field(min_length=1, max_length=100)


class PrepareLocalDataRemovalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: RemovalState
    plan_id: UUID
    application_identity: Literal["com.sapsos.smart-academic-planner"] = APP_ID  # type: ignore[assignment]
    categories: tuple[str, ...]
    message: str


def _app_data_root() -> Path:
    if settings.runtime_manifest_path is not None:
        return settings.runtime_manifest_path.parent
    return resolve_app_data_root()


def _raise(error: LocalDataRemovalError) -> HTTPException:
    status = 409 if error.code not in {"local_desktop_only"} else 404
    return HTTPException(status_code=status, detail={"code": error.code, "message": error.message})


def _plan_state() -> RemovalState:
    if not PLAN_PATH.is_file():
        return RemovalState.NOT_STARTED
    try:
        payload = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        return RemovalState(str(payload.get("execution_state", RemovalState.FAILED)))
    except (OSError, json.JSONDecodeError, ValueError):
        return RemovalState.FAILED


@router.get("/status", response_model=LocalDataRemovalStatus)
def get_local_data_removal_status() -> LocalDataRemovalStatus:
    if settings.product_mode != "LOCAL_DESKTOP":
        raise HTTPException(
            status_code=404,
            detail={
                "code": "local_data_removal_unavailable",
                "message": "Local data removal is unavailable in SERVER mode.",
            },
        )
    return LocalDataRemovalStatus(
        state=_plan_state(),
        categories=tuple(category.value for category in RemovalCategory),
        external_files_preserved=(
            "external backups",
            "external diagnostics ZIPs",
            "Documents",
            "Downloads",
            "Desktop",
        ),
        message=(
            "Default uninstall preserves local data. Complete removal is a separate, "
            "irreversible operation."
        ),
    )


@router.post("/prepare", response_model=PrepareLocalDataRemovalResponse)
def prepare_local_data_removal(
    request: PrepareLocalDataRemovalRequest,
) -> PrepareLocalDataRemovalResponse:
    if settings.product_mode != "LOCAL_DESKTOP":
        raise HTTPException(
            status_code=404,
            detail={
                "code": "local_data_removal_unavailable",
                "message": "Local data removal is unavailable in SERVER mode.",
            },
        )
    if _plan_state() not in {
        RemovalState.NOT_STARTED,
        RemovalState.FAILED,
        RemovalState.EXPIRED,
    }:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "plan_not_ready",
                "message": (
                    "Another local-data removal operation is already pending or in progress."
                ),
            },
        )
    root = _app_data_root()
    try:
        validated_root = validate_app_data_root(root)
        active = [
            marker for marker in ACTIVE_OPERATION_MARKERS if (validated_root / marker).is_file()
        ]
        if active:
            raise LocalDataRemovalError(
                "active_operation", "A local operation is still in progress."
            )
        if request.confirmation != CONFIRMATION_TEXT:
            raise LocalDataRemovalError(
                "confirmation_mismatch", "The exact confirmation text is required."
            )
        if not is_validated_external_backup(request.backup_receipt):
            raise LocalDataRemovalError(
                "backup_required", "Create and validate a new external backup first."
            )
        plan = create_deletion_plan(
            root=validated_root,
            application_version=APPLICATION_VERSION,
            categories=tuple(RemovalCategory),
            confirmation=request.confirmation,
            external_backup_verified=True,
            external_backup_summary="validated external backup receipt",
        )
        PLAN_DIRECTORY.mkdir(parents=True, exist_ok=True)
        PLAN_PATH.write_bytes(serialize_plan(plan))
    except LocalDataRemovalError as error:
        raise _raise(error) from error
    return PrepareLocalDataRemovalResponse(
        state=RemovalState.READY,
        plan_id=UUID(plan.one_time_nonce),
        categories=plan.categories,
        message=(
            "The one-time deletion plan is ready. The trusted desktop cleanup step "
            "must execute it after shutdown."
        ),
    )


@router.post("/cancel", response_model=LocalDataRemovalStatus)
def cancel_local_data_removal() -> LocalDataRemovalStatus:
    if settings.product_mode != "LOCAL_DESKTOP":
        raise HTTPException(
            status_code=404,
            detail={
                "code": "local_data_removal_unavailable",
                "message": "Local data removal is unavailable in SERVER mode.",
            },
        )
    if PLAN_PATH.is_file():
        PLAN_PATH.unlink(missing_ok=True)
    return get_local_data_removal_status()
