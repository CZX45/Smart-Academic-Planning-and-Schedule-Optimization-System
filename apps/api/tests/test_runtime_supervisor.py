from __future__ import annotations

from pathlib import Path

import pytest

from app.runtime.discovery import new_runtime_manifest
from app.runtime.supervisor import ApiProcessSupervisor


class FakeProcess:
    def __init__(self, returncode: int | None = None, pid: int = 1234) -> None:
        self.returncode = returncode
        self.pid = pid
        self.terminated = False

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = 0

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode or 0

    def kill(self) -> None:
        self.returncode = -9


def test_supervisor_waits_for_manifest_and_readiness(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    process = FakeProcess()
    manifest = new_runtime_manifest(host="127.0.0.1", port=54321, pid=process.pid)
    monkeypatch.setattr("app.runtime.supervisor.subprocess.Popen", lambda *_, **__: process)
    discoveries = iter([None, manifest])
    monkeypatch.setattr(
        "app.runtime.supervisor.discover_runtime_manifest", lambda _: next(discoveries)
    )
    monkeypatch.setattr(ApiProcessSupervisor, "_readiness_is_reachable", lambda *_: True)

    supervisor = ApiProcessSupervisor(
        manifest_path=tmp_path / "runtime.json",
        log_path=tmp_path / "api.log",
        poll_interval=0,
    )

    assert supervisor.start() is manifest
    supervisor.stop()
    assert process.terminated is True
    assert not (tmp_path / "api.log").exists() or (tmp_path / "api.log").read_text() == ""


def test_supervisor_reports_child_crash_with_log_tail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "api.log"
    log_path.write_text("startup failed\nmissing dependency\n", encoding="utf-8")
    process = FakeProcess(returncode=3)
    supervisor = ApiProcessSupervisor(
        manifest_path=tmp_path / "runtime.json",
        log_path=log_path,
    )
    supervisor.process = process  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="missing dependency"):
        supervisor.monitor()


def test_supervisor_rejects_second_live_instance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    live_manifest = new_runtime_manifest(host="127.0.0.1", port=54321)
    monkeypatch.setattr("app.runtime.supervisor.discover_runtime_manifest", lambda _: live_manifest)
    supervisor = ApiProcessSupervisor(
        manifest_path=tmp_path / "runtime.json",
        log_path=tmp_path / "api.log",
    )

    with pytest.raises(RuntimeError, match="already owns"):
        supervisor.start()


def test_supervisor_restart_policy_is_bounded(tmp_path: Path) -> None:
    process = FakeProcess(returncode=7)
    supervisor = ApiProcessSupervisor(
        manifest_path=tmp_path / "runtime.json",
        log_path=tmp_path / "api.log",
        max_restarts=0,
    )
    supervisor.process = process  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="restart limit reached"):
        supervisor.restart_if_crashed()


def test_supervisor_rejects_a_manifest_from_another_process(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    process = FakeProcess(pid=1234)
    other_manifest = new_runtime_manifest(host="127.0.0.1", port=54321, pid=5678)
    monkeypatch.setattr("app.runtime.supervisor.subprocess.Popen", lambda *_, **__: process)
    discoveries = iter([None, other_manifest])
    monkeypatch.setattr(
        "app.runtime.supervisor.discover_runtime_manifest", lambda _: next(discoveries)
    )

    supervisor = ApiProcessSupervisor(
        manifest_path=tmp_path / "runtime.json",
        log_path=tmp_path / "api.log",
        poll_interval=0,
    )

    with pytest.raises(RuntimeError, match="belongs to another"):
        supervisor.start()
