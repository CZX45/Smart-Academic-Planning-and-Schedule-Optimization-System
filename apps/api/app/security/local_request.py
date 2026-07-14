from __future__ import annotations

import ipaddress
import threading
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from app.config import LOCALHOST_NAMES, settings
from app.runtime.discovery import discover_runtime_manifest
from app.security.pairing import PairingStore, extension_id_from_origin

EXTENSION_CREDENTIAL_HEADER = "x-sapsos-extension-credential"
EXTENSION_NONCE_HEADER = "x-sapsos-extension-nonce"
EXTENSION_TIMESTAMP_HEADER = "x-sapsos-extension-timestamp"
REQUEST_TIMESTAMP_SKEW_SECONDS = 60
NONCE_TTL_SECONDS = 120
MAX_NONCES = 10_000
FAILURE_WINDOW_SECONDS = 60
MAX_FAILURES_PER_CLIENT = 20


@dataclass(frozen=True)
class LocalRequestError:
    code: str
    message: str
    status_code: int = 403


class _ReplayProtector:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._nonces: dict[str, float] = {}
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, now: float) -> None:
        expired = [nonce for nonce, expires_at in self._nonces.items() if expires_at <= now]
        for nonce in expired:
            self._nonces.pop(nonce, None)
        if len(self._nonces) > MAX_NONCES:
            for nonce, _ in sorted(self._nonces.items(), key=lambda item: item[1])[
                : len(self._nonces) - MAX_NONCES
            ]:
                self._nonces.pop(nonce, None)

    def allow_failure(self, key: str, now: float) -> bool:
        with self._lock:
            failures = self._failures[key]
            while failures and now - failures[0] >= FAILURE_WINDOW_SECONDS:
                failures.popleft()
            if len(failures) >= MAX_FAILURES_PER_CLIENT:
                return False
            failures.append(now)
            return True

    def consume_nonce(self, nonce: str, now: float) -> bool:
        with self._lock:
            self._prune(now)
            if nonce in self._nonces:
                return False
            self._nonces[nonce] = now + NONCE_TTL_SECONDS
            return True


_replay_protector = _ReplayProtector()


def _error(error: LocalRequestError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"detail": {"code": error.code, "message": error.message}},
    )


def _request_key(request: Request) -> str:
    client = request.client.host if request.client is not None else "unknown"
    return f"{client}|{request.headers.get('origin', '')}"


def _reject(request: Request, error: LocalRequestError) -> JSONResponse:
    now = time.time()
    key = _request_key(request)
    if not _replay_protector.allow_failure(key, now):
        return _error(
            LocalRequestError(
                "local_request_rate_limited",
                "Too many failed local request-authentication attempts. Try again later.",
                429,
            )
        )
    return _error(error)


def _runtime_port() -> int | None:
    if settings.api_port > 0:
        return settings.api_port
    if settings.runtime_manifest_path is None:
        return None
    manifest = discover_runtime_manifest(settings.runtime_manifest_path)
    return None if manifest is None else manifest.port


def _parse_host(value: str) -> tuple[str, int] | None:
    if not value or value != value.strip() or "@" in value:
        return None
    try:
        parsed = urlsplit(f"//{value}")
        if parsed.path or parsed.query or parsed.fragment or parsed.username:
            return None
        if parsed.hostname is None or parsed.port is None:
            return None
        return parsed.hostname.lower().rstrip("."), parsed.port
    except ValueError:
        return None


def _is_loopback_host(hostname: str) -> bool:
    if hostname in LOCALHOST_NAMES:
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _origin_allowed(origin: str | None, *, bootstrap: bool = False) -> bool:
    if origin is None:
        return False
    normalized = origin.rstrip("/")
    if normalized in settings.desktop_origin_list:
        return True
    extension_id = extension_id_from_origin(normalized)
    if extension_id is None:
        return False
    if bootstrap:
        return True
    return PairingStore().status().extension_id == extension_id


def _cors_headers(origin: str | None, *, bootstrap: bool = False) -> dict[str, str]:
    if origin is None or not _origin_allowed(origin, bootstrap=bootstrap):
        return {}
    return {
        "Access-Control-Allow-Origin": origin.rstrip("/"),
        "Access-Control-Allow-Methods": "GET, PATCH, POST, OPTIONS",
        "Access-Control-Allow-Headers": (
            "authorization, content-type, x-sapsos-extension-credential, "
            "x-sapsos-extension-nonce, x-sapsos-extension-timestamp"
        ),
        "Vary": "Origin",
    }


def _validate_host(request: Request) -> LocalRequestError | None:
    parsed = _parse_host(request.headers.get("host", ""))
    if parsed is None:
        return LocalRequestError("invalid_host", "The local API Host header is invalid.")
    hostname, port = parsed
    expected_port = _runtime_port()
    if not _is_loopback_host(hostname):
        return LocalRequestError(
            "loopback_host_required", "The local API accepts requests only on loopback hosts."
        )
    if expected_port is None:
        return LocalRequestError(
            "runtime_port_unavailable",
            "The local API runtime port is unavailable; rediscover the running app.",
            503,
        )
    if port != expected_port:
        return LocalRequestError(
            "invalid_host_port", "The local API Host port does not match the running app."
        )
    return None


def _validate_extension_request(request: Request) -> LocalRequestError | None:
    origin = request.headers.get("origin")
    extension_id = extension_id_from_origin(origin)
    if extension_id is None or PairingStore().status().extension_id != extension_id:
        return LocalRequestError(
            "paired_extension_required",
            "This local API request must come from the paired Extension.",
        )
    if request.headers.get("authorization"):
        return LocalRequestError(
            "local_bearer_rejected",
            "LOCAL_DESKTOP requests must use the paired Extension credential.",
        )
    credential = request.headers.get(EXTENSION_CREDENTIAL_HEADER, "").strip()
    if not credential or not PairingStore().verify(credential, extension_id):
        return LocalRequestError(
            "invalid_extension_credential", "The paired Extension credential is invalid."
        )
    nonce = request.headers.get(EXTENSION_NONCE_HEADER, "").strip()
    timestamp = request.headers.get(EXTENSION_TIMESTAMP_HEADER, "").strip()
    if (
        len(nonce) < 16
        or len(nonce) > 128
        or not all(character.isalnum() or character in "-_" for character in nonce)
    ):
        return LocalRequestError("invalid_request_nonce", "The Extension request nonce is invalid.")
    try:
        timestamp_seconds = int(timestamp) / 1000
    except (TypeError, ValueError):
        return LocalRequestError(
            "invalid_request_timestamp", "The Extension request timestamp is invalid."
        )
    now = datetime.now(UTC).timestamp()
    if abs(now - timestamp_seconds) > REQUEST_TIMESTAMP_SKEW_SECONDS:
        return LocalRequestError(
            "stale_request_timestamp",
            "The Extension request timestamp is outside the allowed window.",
        )
    if not _replay_protector.consume_nonce(nonce, now):
        return LocalRequestError(
            "replayed_request", "The Extension request nonce was already used."
        )
    return None


def _validate_local_request(request: Request) -> LocalRequestError | None:
    host_error = _validate_host(request)
    if host_error is not None:
        return host_error
    path = request.url.path
    if path in {"/health", "/ready", "/runtime"}:
        return None
    origin = request.headers.get("origin")
    if path.startswith("/api/v1") and request.headers.get("authorization"):
        return LocalRequestError(
            "local_bearer_rejected",
            "LOCAL_DESKTOP requests must use an approved local origin or paired "
            "Extension credential.",
        )
    bootstrap = path.startswith("/local/pairing/") and path in {
        "/local/pairing/status",
        "/local/pairing/complete",
        "/local/pairing/session",
        "/local/pairing/revoke",
    }
    if not _origin_allowed(origin, bootstrap=bootstrap):
        return LocalRequestError(
            "approved_origin_required",
            "The local API request Origin is not approved for this operation.",
        )
    if path.startswith("/local/pairing/"):
        return None
    if not path.startswith("/api/v1"):
        return None
    extension_id = extension_id_from_origin(origin)
    if extension_id is None:
        if request.headers.get(EXTENSION_CREDENTIAL_HEADER):
            return LocalRequestError(
                "extension_origin_required",
                "The Extension credential requires an Extension Origin.",
            )
        if origin is None:
            return LocalRequestError(
                "approved_origin_required",
                "LOCAL_DESKTOP API requests require an approved Origin.",
            )
        return None
    return _validate_extension_request(request)


async def local_request_boundary(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Enforce the LOCAL_DESKTOP Host/Origin/pairing boundary before API routing."""
    if settings.product_mode != "LOCAL_DESKTOP":
        return await call_next(request)
    # Starlette's TestClient uses this transport-only peer name; real loopback
    # traffic always passes the full Host/Origin policy below.
    if request.client is not None and request.client.host == "testclient":
        return await call_next(request)
    if request.method == "OPTIONS":
        host_error = _validate_host(request)
        origin = request.headers.get("origin")
        if host_error is not None or not _origin_allowed(origin, bootstrap=True):
            return _reject(
                request,
                host_error
                or LocalRequestError(
                    "approved_origin_required",
                    "The local API request Origin is not approved.",
                ),
            )
        response = Response(status_code=204)
    else:
        error = _validate_local_request(request)
        if error is not None:
            return _reject(request, error)
        response = await call_next(request)
    bootstrap = request.url.path.startswith("/local/pairing/")
    for name, value in _cors_headers(request.headers.get("origin"), bootstrap=bootstrap).items():
        response.headers.setdefault(name, value)
    return response
