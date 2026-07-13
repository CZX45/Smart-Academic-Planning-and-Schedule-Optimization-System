from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from subprocess import Popen
from typing import TextIO
from uuid import UUID

from app.runtime.discovery import (
    RuntimeManifest,
    discover_runtime_manifest,
    read_runtime_manifest,
)


@dataclass(slots=True)
class ApiProcessSupervisor:
    """Own one local API child process with bounded, observable lifecycle control."""

    manifest_path: Path
    log_path: Path
    command: list[str] = field(default_factory=lambda: [sys.executable, "-m", "app.run"])
    cwd: Path | None = None
    env: dict[str, str] | None = None
    startup_timeout: float = 15.0
    poll_interval: float = 0.1
    shutdown_timeout: float = 5.0
    max_restarts: int = 1
    process: Popen[bytes] | None = field(default=None, init=False)
    restart_count: int = field(default=0, init=False)
    owned_instance_id: UUID | None = field(default=None, init=False)
    _log_file: TextIO | None = field(default=None, init=False)

    def start(self) -> RuntimeManifest:
        if self.process is not None and self.process.poll() is None:
            raise RuntimeError("The API process is already running.")
        self._cleanup_stale_manifest()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_file = self.log_path.open("a", encoding="utf-8")
        environment = os.environ.copy()
        if self.env is not None:
            environment.update(self.env)
        try:
            self.process = subprocess.Popen(
                self.command,
                cwd=self.cwd,
                env=environment,
                stdout=self._log_file,
                stderr=subprocess.STDOUT,
            )
            manifest = self.wait_until_ready()
            self.owned_instance_id = manifest.instance_id
            return manifest
        except Exception:
            self.stop()
            raise

    def wait_until_ready(self) -> RuntimeManifest:
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            self._raise_if_exited("API process exited before readiness.")
            manifest = discover_runtime_manifest(self.manifest_path)
            if (
                manifest is not None
                and self.process is not None
                and manifest.pid != self.process.pid
            ):
                raise RuntimeError(
                    self._diagnostics("Runtime manifest belongs to another API process.")
                )
            if manifest is not None and self._readiness_is_reachable(manifest.readiness_url):
                return manifest
            time.sleep(self.poll_interval)
        raise RuntimeError(self._diagnostics("API process did not become ready before timeout."))

    def monitor(self) -> None:
        self._raise_if_exited("API process exited unexpectedly.")

    def restart_if_crashed(self) -> RuntimeManifest:
        if self.process is None:
            raise RuntimeError("Cannot restart an API process that has not started.")
        if self.process.poll() is None:
            raise RuntimeError("Cannot restart a running API process.")
        if self.restart_count >= self.max_restarts:
            raise RuntimeError(self._diagnostics("API restart limit reached."))
        self.restart_count += 1
        return self.start()

    def stop(self) -> None:
        process = self.process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=self.shutdown_timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=self.shutdown_timeout)
        self.process = None
        if self._log_file is not None:
            self._log_file.close()
            self._log_file = None
        manifest = read_runtime_manifest(self.manifest_path)
        if manifest is not None and manifest.instance_id == self.owned_instance_id:
            self.manifest_path.unlink(missing_ok=True)
        self.owned_instance_id = None

    def _cleanup_stale_manifest(self) -> None:
        if self.manifest_path.exists() and discover_runtime_manifest(self.manifest_path) is None:
            self.manifest_path.unlink(missing_ok=True)
        elif discover_runtime_manifest(self.manifest_path) is not None:
            raise RuntimeError("Another API process already owns the runtime manifest.")

    def _raise_if_exited(self, message: str) -> None:
        if self.process is not None and self.process.poll() is not None:
            raise RuntimeError(self._diagnostics(message))

    @staticmethod
    def _readiness_is_reachable(url: str) -> bool:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:
                return int(response.status) == 200
        except (OSError, urllib.error.URLError):
            return False

    def _diagnostics(self, message: str) -> str:
        lines: list[str] = [message, f"log_path={self.log_path}"]
        if self.process is not None and self.process.returncode is not None:
            lines.append(f"exit_code={self.process.returncode}")
        try:
            tail = self.log_path.read_text(encoding="utf-8").splitlines()[-20:]
        except OSError:
            tail = []
        if tail:
            lines.append("log_tail=" + "\\n".join(tail))
        return "\n".join(lines)
