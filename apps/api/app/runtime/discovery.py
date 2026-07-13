from __future__ import annotations

import json
import os
import socket
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

RUNTIME_PROTOCOL_VERSION = 1
RUNTIME_MANIFEST_NAME = "runtime.json"


class RuntimeManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol_version: int = Field(default=RUNTIME_PROTOCOL_VERSION, ge=1)
    instance_id: UUID
    pid: int = Field(gt=0)
    host: str
    port: int = Field(gt=0, le=65535)
    base_url: str
    readiness_url: str
    status: str
    started_at: datetime


def allocate_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def default_runtime_manifest_path(data_directory: Path) -> Path:
    return data_directory / RUNTIME_MANIFEST_NAME


def new_runtime_manifest(*, host: str, port: int, pid: int | None = None) -> RuntimeManifest:
    resolved_pid = pid if pid is not None else os.getpid()
    url_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    base_url = f"http://{url_host}:{port}"
    return RuntimeManifest(
        instance_id=uuid4(),
        pid=resolved_pid,
        host=host,
        port=port,
        base_url=base_url,
        readiness_url=f"{base_url}/ready",
        status="starting",
        started_at=datetime.now(UTC),
    )


def publish_runtime_manifest(path: Path, manifest: RuntimeManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(f"{path.suffix}.lock")
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        if time.time() - lock_path.stat().st_mtime > 30:
            lock_path.unlink()
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        else:
            raise RuntimeError(f"Runtime manifest is locked: {path}") from error
    try:
        os.close(lock_fd)
        existing = discover_runtime_manifest(path)
        if existing is not None and existing.instance_id != manifest.instance_id:
            raise RuntimeError(f"Another runtime instance owns the manifest: {path}")
        fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as temporary_file:
                temporary_file.write(json.dumps(manifest.model_dump(mode="json"), sort_keys=True))
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_name, path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
    finally:
        if lock_path.exists():
            lock_path.unlink()


def _process_is_alive(pid: int) -> bool:
    if pid == os.getpid():
        return True
    try:
        os.kill(pid, 0)
    except (OSError, PermissionError):
        return False
    return True


def _port_is_reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return True
    except OSError:
        return False


def is_runtime_manifest_stale(manifest: RuntimeManifest) -> bool:
    if manifest.protocol_version != RUNTIME_PROTOCOL_VERSION:
        return True
    if not _process_is_alive(manifest.pid):
        return True
    return manifest.status == "ready" and not _port_is_reachable(manifest.host, manifest.port)


def discover_runtime_manifest(path: Path) -> RuntimeManifest | None:
    manifest = read_runtime_manifest(path)
    if manifest is None or is_runtime_manifest_stale(manifest):
        return None
    return manifest


def read_runtime_manifest(path: Path) -> RuntimeManifest | None:
    try:
        return RuntimeManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError):
        return None
