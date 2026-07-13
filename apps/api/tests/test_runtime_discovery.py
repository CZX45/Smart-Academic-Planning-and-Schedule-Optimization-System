from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.runtime.discovery import (
    RUNTIME_PROTOCOL_VERSION,
    allocate_loopback_port,
    discover_runtime_manifest,
    new_runtime_manifest,
    publish_runtime_manifest,
)


def test_allocate_loopback_port_returns_ephemeral_port() -> None:
    port = allocate_loopback_port()

    assert 1 <= port <= 65535


def test_runtime_manifest_is_atomic_and_discoverable(tmp_path: Path) -> None:
    path = tmp_path / "runtime.json"
    manifest = new_runtime_manifest(host="127.0.0.1", port=allocate_loopback_port())

    publish_runtime_manifest(path, manifest)
    discovered = discover_runtime_manifest(path)

    assert discovered is not None
    assert discovered.instance_id == manifest.instance_id
    assert discovered.protocol_version == RUNTIME_PROTOCOL_VERSION
    assert discovered.readiness_url.endswith("/ready")


def test_runtime_manifest_with_dead_process_is_stale(tmp_path: Path) -> None:
    path = tmp_path / "runtime.json"
    manifest = new_runtime_manifest(
        host="127.0.0.1", port=allocate_loopback_port(), pid=os.getpid()
    )
    manifest = manifest.model_copy(update={"pid": 999_999_999, "status": "ready"})
    publish_runtime_manifest(path, manifest)

    assert discover_runtime_manifest(path) is None


def test_runtime_manifest_prevents_a_second_live_instance(tmp_path: Path) -> None:
    path = tmp_path / "runtime.json"
    first = new_runtime_manifest(host="127.0.0.1", port=allocate_loopback_port())
    second = new_runtime_manifest(host="127.0.0.1", port=allocate_loopback_port())
    publish_runtime_manifest(path, first)

    with pytest.raises(RuntimeError, match="Another runtime instance"):
        publish_runtime_manifest(path, second)
