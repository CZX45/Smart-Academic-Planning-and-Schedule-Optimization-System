from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import threading
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

from app.config import APP_DATA_DIR_NAME, APP_ID

CONFIRMATION_TEXT = "DELETE SAPSOS LOCAL DATA"
PLAN_FORMAT_VERSION = 1
PLAN_TTL = timedelta(minutes=10)
FIXED_PLAN_PATH = Path(tempfile.gettempdir()) / "SAPSOS-local-data-removal" / "pending-plan.json"
FIXED_NONCE_LEDGER = FIXED_PLAN_PATH.with_name("consumed-nonces.json")
_receipt_lock = threading.Lock()
_validated_external_backups: dict[str, datetime] = {}


class LocalDataRemovalError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class RemovalState(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    PREFLIGHT_FAILED = "PREFLIGHT_FAILED"
    BACKUP_REQUIRED = "BACKUP_REQUIRED"
    BACKUP_FAILED = "BACKUP_FAILED"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    CONFIRMATION_CANCELLED = "CONFIRMATION_CANCELLED"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    TAMPER_REJECTED = "TAMPER_REJECTED"
    REPLAY_REJECTED = "REPLAY_REJECTED"


class RemovalCategory(StrEnum):
    PERSISTENT_USER_DATA = "PERSISTENT_USER_DATA"
    RECOVERABLE_OPERATIONAL_STATE = "RECOVERABLE_OPERATIONAL_STATE"
    EPHEMERAL_RUNTIME_STATE = "EPHEMERAL_RUNTIME_STATE"
    GENERATED_LOCAL_STATE = "GENERATED_LOCAL_STATE"


ALLOWLIST: Mapping[RemovalCategory, tuple[str, ...]] = {
    RemovalCategory.PERSISTENT_USER_DATA: (
        "sapsos.db",
        "sapsos.db-wal",
        "sapsos.db-shm",
        "sapsos.db-journal",
        "pairing.json",
        "preferences.json",
        "app-config.json",
    ),
    RemovalCategory.RECOVERABLE_OPERATIONAL_STATE: (
        "migration-safety",
        "restore-safety",
        "restore-staging",
        "migration-attempt.json",
        "pending-restore.json",
        "restore-status.json",
        "migration-journal.json",
        "interrupted-operation.json",
    ),
    RemovalCategory.EPHEMERAL_RUNTIME_STATE: (
        "runtime.json",
        "startup.lock",
        "startup-events.json",
        "local-runtime",
    ),
    RemovalCategory.GENERATED_LOCAL_STATE: (
        "diagnostics-staging",
        "cache",
        "deletion-staging",
    ),
}


def _absolute(path: Path) -> Path:
    if not str(path).strip():
        raise LocalDataRemovalError("path_empty", "A deletion path is required.")
    if path.is_absolute() is False:
        raise LocalDataRemovalError("path_not_absolute", "Deletion paths must be absolute.")
    return Path(os.path.abspath(path))


def _same_or_child(path: Path, root: Path) -> bool:
    try:
        normalized_path = os.path.normcase(str(_absolute(path)))
        normalized_root = os.path.normcase(str(_absolute(root))).rstrip("\\/")
        return os.path.commonpath((normalized_path, normalized_root)) == normalized_root
    except ValueError:
        return False


def _reject_reparse_ancestors(path: Path, stop: Path) -> None:
    cursor = path
    stop = _absolute(stop)
    while True:
        if cursor.exists() and _is_reparse_point(cursor):
            raise LocalDataRemovalError("reparse_point", "Reparse points are not allowed.")
        if cursor == stop or cursor.parent == cursor:
            break
        cursor = cursor.parent


def _is_reparse_point(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        return bool(
            getattr(path.lstat(), "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        )
    except OSError as error:
        raise LocalDataRemovalError(
            "path_unreadable", "A deletion path could not be inspected."
        ) from error


def resolve_app_data_root(*, local_app_data: Path | None = None) -> Path:
    """Resolve the production root; test roots are accepted only by test helpers."""

    base = local_app_data or Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return _absolute(base / APP_DATA_DIR_NAME)


def register_validated_external_backup(backup_id: UUID, *, now: datetime | None = None) -> str:
    receipt = f"external-backup:{backup_id}"
    with _receipt_lock:
        _validated_external_backups[receipt] = now or datetime.now(UTC)
    return receipt


def is_validated_external_backup(receipt: str, *, now: datetime | None = None) -> bool:
    with _receipt_lock:
        created = _validated_external_backups.get(receipt)
    if created is None:
        return False
    return (now or datetime.now(UTC)) - created <= PLAN_TTL


def resolve_test_root(root: Path) -> Path:
    """Resolve only a caller-created temporary test root, never a production override."""

    resolved = _absolute(root)
    temp = _absolute(Path(tempfile.gettempdir()))
    if not _same_or_child(resolved, temp) or resolved == temp:
        raise LocalDataRemovalError(
            "test_root_invalid", "Test data must be inside the temp directory."
        )
    _reject_reparse_ancestors(resolved, temp)
    return resolved


def validate_app_data_root(root: Path, *, test_mode: bool = False) -> Path:
    resolved = resolve_test_root(root) if test_mode else _absolute(root)
    if resolved.name.casefold() != APP_DATA_DIR_NAME.casefold():
        if not test_mode:
            raise LocalDataRemovalError("app_data_identity", "The AppData identity is not SAPSOS.")
    drive_root = Path(resolved.anchor)
    if resolved == drive_root:
        raise LocalDataRemovalError("drive_root", "A drive root cannot be deleted.")
    if resolved.parent == resolved:
        raise LocalDataRemovalError("root_invalid", "The data root is invalid.")
    _reject_reparse_ancestors(resolved, Path(resolved.anchor))
    return resolved


def _canonical_json(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def _plan_payload(plan: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in plan.items() if key != "integrity_hash"}


def _integrity_hash(plan: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical_json(_plan_payload(plan))).hexdigest()


def _logical_entries(categories: Iterable[RemovalCategory]) -> list[str]:
    entries: list[str] = []
    for category in categories:
        entries.extend(f"{category.value}/{entry}" for entry in ALLOWLIST[category])
    return sorted(set(entries))


@dataclass(frozen=True, slots=True)
class DeletionPlan:
    format_version: int
    created_at: str
    expires_at: str
    one_time_nonce: str
    application_identity: str
    application_version: str
    app_data_root_identity: str
    categories: tuple[str, ...]
    entries: tuple[str, ...]
    confirmation_completed: bool
    external_backup_verified: bool
    external_backup_summary: str
    integrity_hash: str
    execution_state: RemovalState

    def as_dict(self) -> dict[str, object]:
        return {
            "format_version": self.format_version,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "one_time_nonce": self.one_time_nonce,
            "application_identity": self.application_identity,
            "application_version": self.application_version,
            "app_data_root_identity": self.app_data_root_identity,
            "categories": list(self.categories),
            "entries": list(self.entries),
            "confirmation_completed": self.confirmation_completed,
            "external_backup_verified": self.external_backup_verified,
            "external_backup_summary": self.external_backup_summary,
            "integrity_hash": self.integrity_hash,
            "execution_state": self.execution_state.value,
        }


def create_deletion_plan(
    *,
    root: Path,
    application_version: str,
    categories: Iterable[RemovalCategory],
    confirmation: str,
    external_backup_verified: bool,
    external_backup_summary: str,
    now: datetime | None = None,
    nonce: UUID | None = None,
    test_mode: bool = False,
) -> DeletionPlan:
    validated_root = validate_app_data_root(root, test_mode=test_mode)
    selected = tuple(dict.fromkeys(categories))
    if not selected:
        raise LocalDataRemovalError("categories_empty", "No local-data category was selected.")
    if confirmation != CONFIRMATION_TEXT:
        raise LocalDataRemovalError(
            "confirmation_mismatch", "The exact confirmation text is required."
        )
    if not external_backup_verified or not external_backup_summary.strip():
        raise LocalDataRemovalError("backup_required", "A validated external backup is required.")
    timestamp = now or datetime.now(UTC)
    created_at = timestamp.astimezone(UTC).isoformat()
    expires_at = (timestamp + PLAN_TTL).astimezone(UTC).isoformat()
    raw: dict[str, object] = {
        "format_version": PLAN_FORMAT_VERSION,
        "created_at": created_at,
        "expires_at": expires_at,
        "one_time_nonce": str(nonce or uuid4()),
        "application_identity": APP_ID,
        "application_version": application_version,
        "app_data_root_identity": str(validated_root).casefold(),
        "categories": [category.value for category in selected],
        "entries": _logical_entries(selected),
        "confirmation_completed": True,
        "external_backup_verified": True,
        "external_backup_summary": external_backup_summary.strip()[:200],
        "execution_state": RemovalState.READY.value,
    }
    raw["integrity_hash"] = _integrity_hash(raw)
    return DeletionPlan(
        format_version=PLAN_FORMAT_VERSION,
        created_at=created_at,
        expires_at=expires_at,
        one_time_nonce=str(raw["one_time_nonce"]),
        application_identity=APP_ID,
        application_version=application_version,
        app_data_root_identity=str(validated_root).casefold(),
        categories=tuple(str(item) for item in cast(list[object], raw["categories"])),
        entries=tuple(str(item) for item in cast(list[object], raw["entries"])),
        confirmation_completed=True,
        external_backup_verified=True,
        external_backup_summary=str(raw["external_backup_summary"]),
        integrity_hash=str(raw["integrity_hash"]),
        execution_state=RemovalState.READY,
    )


def serialize_plan(plan: DeletionPlan) -> bytes:
    return _canonical_json(plan.as_dict()) + b"\n"


def _parse_plan(payload: Mapping[str, object]) -> DeletionPlan:
    try:
        return DeletionPlan(
            format_version=int(cast(int, payload["format_version"])),
            created_at=str(payload["created_at"]),
            expires_at=str(payload["expires_at"]),
            one_time_nonce=str(payload["one_time_nonce"]),
            application_identity=str(payload["application_identity"]),
            application_version=str(payload["application_version"]),
            app_data_root_identity=str(payload["app_data_root_identity"]),
            categories=tuple(str(item) for item in cast(list[object], payload["categories"])),
            entries=tuple(str(item) for item in cast(list[object], payload["entries"])),
            confirmation_completed=bool(payload["confirmation_completed"]),
            external_backup_verified=bool(payload["external_backup_verified"]),
            external_backup_summary=str(payload["external_backup_summary"]),
            integrity_hash=str(payload["integrity_hash"]),
            execution_state=RemovalState(str(payload["execution_state"])),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise LocalDataRemovalError("plan_invalid", "The deletion plan is invalid.") from error


def read_and_validate_plan(
    plan_path: Path,
    *,
    root: Path,
    application_version: str,
    now: datetime | None = None,
    test_mode: bool = False,
) -> DeletionPlan:
    plan_file = _absolute(plan_path)
    validated_root = validate_app_data_root(root, test_mode=test_mode)
    if _same_or_child(plan_file, validated_root):
        raise LocalDataRemovalError(
            "plan_inside_root", "The deletion plan must be outside the deletion root."
        )
    try:
        payload = json.loads(plan_file.read_text(encoding="utf-8"))
        plan = _parse_plan(payload)
    except (OSError, json.JSONDecodeError) as error:
        raise LocalDataRemovalError("plan_invalid", "The deletion plan cannot be read.") from error
    if plan.format_version != PLAN_FORMAT_VERSION or plan.integrity_hash != _integrity_hash(
        payload
    ):
        raise LocalDataRemovalError("tamper_rejected", "The deletion plan integrity check failed.")
    if plan.execution_state != RemovalState.READY:
        raise LocalDataRemovalError("replay_rejected", "The deletion plan is no longer executable.")
    if plan.application_identity != APP_ID or plan.application_version != application_version:
        raise LocalDataRemovalError(
            "identity_mismatch", "The deletion plan belongs to another application."
        )
    if plan.app_data_root_identity != str(validated_root).casefold():
        raise LocalDataRemovalError(
            "root_mismatch", "The deletion plan belongs to another AppData root."
        )
    if not plan.confirmation_completed or not plan.external_backup_verified:
        raise LocalDataRemovalError(
            "preflight_incomplete", "The deletion plan is missing required safeguards."
        )
    if tuple(plan.entries) != tuple(sorted(plan.entries)):
        raise LocalDataRemovalError(
            "entries_changed", "The deletion plan entries are not canonical."
        )
    try:
        categories = tuple(RemovalCategory(category) for category in plan.categories)
    except ValueError as error:
        raise LocalDataRemovalError(
            "categories_changed", "The deletion plan category list is invalid."
        ) from error
    if tuple(plan.entries) != tuple(_logical_entries(categories)):
        raise LocalDataRemovalError(
            "entries_changed", "The deletion plan entry list is not allowlisted."
        )
    expires_at = datetime.fromisoformat(plan.expires_at)
    if (now or datetime.now(UTC)) >= expires_at:
        raise LocalDataRemovalError("expired", "The deletion plan has expired.")
    return plan


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _consumed_nonces() -> set[str]:
    try:
        payload = json.loads(FIXED_NONCE_LEDGER.read_text(encoding="utf-8"))
        return {str(value) for value in payload if isinstance(value, str)}
    except (OSError, json.JSONDecodeError, TypeError):
        return set()


def _record_consumed_nonce(nonce: str) -> None:
    FIXED_NONCE_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    values = sorted(_consumed_nonces() | {nonce})[-256:]
    _atomic_write(FIXED_NONCE_LEDGER, _canonical_json(values) + b"\n")


def _delete_entry(root: Path, relative: str) -> None:
    target = root / relative
    if not _same_or_child(target, root) or target == root:
        raise LocalDataRemovalError("path_escape", "A deletion entry escapes the AppData root.")
    _reject_reparse_ancestors(target, root)
    if not target.exists():
        return
    if target.is_dir():
        for child in sorted(target.iterdir(), key=lambda item: item.name.casefold()):
            if _is_reparse_point(child):
                raise LocalDataRemovalError(
                    "reparse_point", "A deletion entry contains a reparse point."
                )
            _delete_entry(root, str(child.relative_to(root)))
        target.rmdir()
    else:
        target.unlink()


def execute_deletion_plan(
    plan_path: Path,
    *,
    root: Path,
    application_version: str,
    now: datetime | None = None,
    test_mode: bool = False,
) -> tuple[RemovalState, tuple[str, ...]]:
    plan = read_and_validate_plan(
        plan_path,
        root=root,
        application_version=application_version,
        now=now,
        test_mode=test_mode,
    )
    if plan.one_time_nonce in _consumed_nonces():
        raise LocalDataRemovalError(
            "replay_rejected", "The deletion plan nonce has already been consumed."
        )
    try:
        _record_consumed_nonce(plan.one_time_nonce)
    except OSError as error:
        raise LocalDataRemovalError(
            "plan_state_unavailable", "The one-time deletion state could not be persisted."
        ) from error
    payload = plan.as_dict()
    payload["execution_state"] = RemovalState.IN_PROGRESS.value
    payload["integrity_hash"] = _integrity_hash(payload)
    _atomic_write(_absolute(plan_path), serialize_plan(_parse_plan(payload)))
    deleted: list[str] = []
    try:
        for entry in plan.entries:
            _, relative = entry.split("/", maxsplit=1)
            _delete_entry(validate_app_data_root(root, test_mode=test_mode), relative)
            deleted.append(entry)
    except (OSError, LocalDataRemovalError) as error:
        failed = dict(payload)
        failed["execution_state"] = RemovalState.FAILED.value
        failed["integrity_hash"] = _integrity_hash(failed)
        _atomic_write(_absolute(plan_path), serialize_plan(_parse_plan(failed)))
        state = RemovalState.PARTIALLY_COMPLETED if deleted else RemovalState.FAILED
        if isinstance(error, LocalDataRemovalError):
            raise LocalDataRemovalError(state.value, error.message) from error
        raise LocalDataRemovalError(
            state.value, "Local data removal stopped safely after a filesystem failure."
        ) from error
    completed = dict(payload)
    completed["execution_state"] = RemovalState.COMPLETED.value
    completed["integrity_hash"] = _integrity_hash(completed)
    _atomic_write(_absolute(plan_path), serialize_plan(_parse_plan(completed)))
    return RemovalState.COMPLETED, tuple(deleted)
