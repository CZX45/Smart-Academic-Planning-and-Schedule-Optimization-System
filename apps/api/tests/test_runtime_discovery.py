from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

import pytest

from app.runtime.discovery import (
    RUNTIME_PROTOCOL_VERSION,
    allocate_loopback_port,
    discover_runtime_manifest,
    new_runtime_manifest,
    publish_runtime_manifest,
    runtime_instance_id_from_environment,
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


def test_runtime_manifest_brackets_ipv6_urls() -> None:
    manifest = new_runtime_manifest(host="::1", port=8000)

    assert manifest.base_url == "http://[::1]:8000"
    assert manifest.readiness_url == "http://[::1]:8000/ready"


def test_runtime_instance_id_without_environment_is_random(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SAPSOS_RUNTIME_INSTANCE_ID", raising=False)

    first = runtime_instance_id_from_environment()
    second = runtime_instance_id_from_environment()

    assert first != second


def test_runtime_instance_id_uses_valid_environment_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = UUID("12345678-1234-4234-8234-123456789abc")
    monkeypatch.setenv("SAPSOS_RUNTIME_INSTANCE_ID", str(expected))

    assert runtime_instance_id_from_environment() == expected
    manifest = new_runtime_manifest(host="127.0.0.1", port=8000, instance_id=expected)
    assert manifest.model_dump(mode="json")["instance_id"] == str(expected)


def test_runtime_instance_id_rejects_invalid_environment_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SAPSOS_RUNTIME_INSTANCE_ID", "not-a-uuid")

    with pytest.raises(RuntimeError, match="valid UUID"):
        runtime_instance_id_from_environment()
