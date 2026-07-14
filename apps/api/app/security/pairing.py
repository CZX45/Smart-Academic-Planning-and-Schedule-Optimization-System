from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.config import settings
from app.runtime.discovery import discover_runtime_manifest

PAIRING_PROTOCOL_VERSION = 1
PAIRING_CODE_TTL = timedelta(minutes=5)
PAIRING_CODE_BYTES = 15
EXTENSION_TOKEN_BYTES = 32
MAX_PAIRING_ATTEMPTS = 8
PAIRING_ATTEMPT_WINDOW = timedelta(minutes=5)


@dataclass(frozen=True)
class PairingStatus:
    paired: bool
    extension_id: str | None
    protocol_version: int


@dataclass(frozen=True)
class PairingCompletion:
    credential: str
    extension_id: str
    protocol_version: int


class PairingError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class PairingStore:
    """Small, local-only security store. Secrets are persisted as SHA-256 verifiers."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings.local_pairing_store_path
        self._lock = threading.Lock()
        self._attempts: dict[str, list[datetime]] = {}

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _instance_id(self) -> str:
        manifest_path = settings.runtime_manifest_path
        if manifest_path is not None:
            manifest = discover_runtime_manifest(manifest_path)
            if manifest is not None:
                return str(manifest.instance_id)
        return f"pid:{os.getpid()}"

    def _empty_state(self) -> dict[str, Any]:
        return {
            "installation_id": secrets.token_hex(16),
            "instance_id": self._instance_id(),
            "session": None,
            "credential": None,
        }

    def _read(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, ValueError):
            return self._empty_state()
        if not isinstance(value, dict):
            return self._empty_state()
        if value.get("instance_id") != self._instance_id():
            value["instance_id"] = self._instance_id()
            value["session"] = None
        value.setdefault("installation_id", secrets.token_hex(16))
        value.setdefault("credential", None)
        return value

    def _write(self, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)

    def status(self) -> PairingStatus:
        with self._lock:
            credential = self._read().get("credential")
            return PairingStatus(
                paired=isinstance(credential, dict) and credential.get("revoked_at") is None,
                extension_id=(credential or {}).get("extension_id")
                if isinstance(credential, dict)
                else None,
                protocol_version=PAIRING_PROTOCOL_VERSION,
            )

    def create_code(self) -> tuple[str, datetime]:
        code = secrets.token_urlsafe(PAIRING_CODE_BYTES)
        expires_at = datetime.now(UTC) + PAIRING_CODE_TTL
        with self._lock:
            state = self._read()
            state["session"] = {
                "code_hash": self._hash(code),
                "expires_at": expires_at.isoformat(),
                "instance_id": self._instance_id(),
            }
            self._write(state)
        return code, expires_at

    def complete(self, code: str, extension_id: str, protocol_version: int) -> PairingCompletion:
        now = datetime.now(UTC)
        with self._lock:
            attempts = [
                t for t in self._attempts.get(extension_id, []) if now - t < PAIRING_ATTEMPT_WINDOW
            ]
            if len(attempts) >= MAX_PAIRING_ATTEMPTS:
                raise PairingError(
                    "pairing_rate_limited", "Too many pairing attempts. Try again later.", 429
                )
            attempts.append(now)
            self._attempts[extension_id] = attempts
            state = self._read()
            session = state.get("session")
            if protocol_version != PAIRING_PROTOCOL_VERSION:
                raise PairingError(
                    "incompatible_protocol",
                    "The desktop app and Extension protocol versions differ.",
                    409,
                )
            if not isinstance(session, dict) or session.get("instance_id") != self._instance_id():
                raise PairingError("pairing_code_invalid", "The pairing code is invalid.", 400)
            try:
                expires_at = datetime.fromisoformat(str(session["expires_at"]))
            except (KeyError, ValueError):
                raise PairingError(
                    "pairing_code_invalid", "The pairing code is invalid.", 400
                ) from None
            if expires_at <= now:
                state["session"] = None
                self._write(state)
                raise PairingError("pairing_code_expired", "The pairing code has expired.", 400)
            if not secrets.compare_digest(
                str(session.get("code_hash", "")), self._hash(code.strip())
            ):
                raise PairingError("pairing_code_invalid", "The pairing code is invalid.", 400)
            credential = f"sapsos_ext_{secrets.token_urlsafe(EXTENSION_TOKEN_BYTES)}"
            state["session"] = None
            state["credential"] = {
                "verifier": self._hash(credential),
                "installation_id": state["installation_id"],
                "extension_id": extension_id,
                "protocol_version": protocol_version,
                "created_at": now.isoformat(),
                "revoked_at": None,
            }
            self._write(state)
            return PairingCompletion(credential, extension_id, protocol_version)

    def revoke(self) -> None:
        with self._lock:
            state = self._read()
            credential = state.get("credential")
            if isinstance(credential, dict):
                credential["revoked_at"] = datetime.now(UTC).isoformat()
                state["credential"] = credential
            self._write(state)

    def verify(self, credential: str, extension_id: str) -> bool:
        with self._lock:
            stored = self._read().get("credential")
            return (
                isinstance(stored, dict)
                and stored.get("revoked_at") is None
                and stored.get("extension_id") == extension_id
                and secrets.compare_digest(str(stored.get("verifier", "")), self._hash(credential))
            )


def extension_id_from_origin(origin: str | None) -> str | None:
    if not origin:
        return None
    parsed = urlparse(origin)
    if parsed.scheme != "chrome-extension" or not parsed.hostname:
        return None
    extension_id = parsed.hostname.lower()
    if len(extension_id) != 32 or any(
        character not in "abcdefghijklmnop" for character in extension_id
    ):
        return None
    return extension_id
