from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Never

import pytest
from starlette.requests import Request

from app.config import settings
from app.security.local_request import (
    _cors_headers,
    _parse_host,
    _validate_local_request,
    local_request_boundary,
)
from app.security.pairing import PAIRING_PROTOCOL_VERSION, PairingStore

EXTENSION_ID = "abcdefghijklmnopabcdefghijklmnop"


def request_for(
    *,
    path: str,
    headers: dict[str, str],
    client_host: str = "127.0.0.1",
    method: str = "POST",
) -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": [
            (key.lower().encode("ascii"), value.encode("ascii")) for key, value in headers.items()
        ],
        "client": (client_host, 12345),
        "server": ("127.0.0.1", 8000),
        "scheme": "http",
    }
    return Request(scope)


def test_host_parser_rejects_ambiguous_and_public_hosts() -> None:
    assert _parse_host("127.0.0.1:8000") == ("127.0.0.1", 8000)
    assert _parse_host("192.168.1.10:8000") == ("192.168.1.10", 8000)
    assert _parse_host("[::1]:8000") == ("::1", 8000)
    assert _parse_host("::1:8000") is None
    assert _parse_host("127.0.0.1") is None
    assert _parse_host("user@127.0.0.1:8000") is None


def test_local_api_rejects_bearer_and_missing_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "api_port", 8000)
    bearer_request = request_for(
        path="/api/v1/institutions",
        headers={"Host": "127.0.0.1:8000", "Authorization": "Bearer local-token"},
    )
    missing_origin_request = request_for(
        path="/api/v1/institutions",
        headers={"Host": "127.0.0.1:8000"},
    )

    bearer_error = _validate_local_request(bearer_request)
    missing_origin_error = _validate_local_request(missing_origin_request)
    assert bearer_error is not None
    assert bearer_error.code == "local_bearer_rejected"
    assert missing_origin_error is not None
    assert missing_origin_error.code == "approved_origin_required"


def test_paired_extension_request_requires_fresh_nonce(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "api_port", 8000)
    monkeypatch.setattr(settings, "runtime_manifest_path", tmp_path / "runtime.json")
    store = PairingStore()
    code, _ = store.create_code()
    completion = store.complete(code, EXTENSION_ID, PAIRING_PROTOCOL_VERSION)
    origin = f"chrome-extension://{EXTENSION_ID}"
    nonce = "a" * 32
    headers = {
        "Host": "127.0.0.1:8000",
        "Origin": origin,
        "X-SAPSOS-Extension-Credential": completion.credential,
        "X-SAPSOS-Extension-Nonce": nonce,
        "X-SAPSOS-Extension-Timestamp": str(int(time.time() * 1000)),
    }

    assert (
        _validate_local_request(request_for(path="/api/v1/data-imports", headers=headers)) is None
    )
    replayed = _validate_local_request(request_for(path="/api/v1/data-imports", headers=headers))
    assert replayed is not None
    assert replayed.code == "replayed_request"
    assert _cors_headers(origin)["Access-Control-Allow-Origin"] == origin


def test_paired_extension_request_accepts_explicit_id_when_chromium_omits_origin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "api_port", 8000)
    monkeypatch.setattr(settings, "runtime_manifest_path", tmp_path / "runtime.json")
    store = PairingStore()
    code, _ = store.create_code()
    completion = store.complete(code, EXTENSION_ID, PAIRING_PROTOCOL_VERSION)
    headers = {
        "Host": "127.0.0.1:8000",
        "X-SAPSOS-Extension-Id": EXTENSION_ID,
        "X-SAPSOS-Extension-Credential": completion.credential,
        "X-SAPSOS-Extension-Nonce": "b" * 32,
        "X-SAPSOS-Extension-Timestamp": str(int(time.time() * 1000)),
    }

    assert (
        _validate_local_request(request_for(path="/api/v1/data-imports", headers=headers)) is None
    )


def test_extension_origin_and_explicit_id_must_match(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "api_port", 8000)
    monkeypatch.setattr(settings, "runtime_manifest_path", tmp_path / "runtime.json")
    store = PairingStore()
    code, _ = store.create_code()
    completion = store.complete(code, EXTENSION_ID, PAIRING_PROTOCOL_VERSION)
    headers = {
        "Host": "127.0.0.1:8000",
        "Origin": f"chrome-extension://{EXTENSION_ID}",
        "X-SAPSOS-Extension-Id": "ponmlkjihgfedcbaponmlkjihgfedcba",
        "X-SAPSOS-Extension-Credential": completion.credential,
        "X-SAPSOS-Extension-Nonce": "c" * 32,
        "X-SAPSOS-Extension-Timestamp": str(int(time.time() * 1000)),
    }

    error = _validate_local_request(request_for(path="/api/v1/data-imports", headers=headers))

    assert error is not None
    assert error.code == "extension_identity_mismatch"


def test_preflight_bootstrap_is_limited_to_pairing_endpoints(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "api_port", 8000)
    monkeypatch.setattr(settings, "runtime_manifest_path", tmp_path / "runtime.json")
    store = PairingStore()
    code, _ = store.create_code()
    store.complete(code, EXTENSION_ID, PAIRING_PROTOCOL_VERSION)
    wrong_origin = "chrome-extension://ponmlkjihgfedcbaponmlkjihgfedcba"
    headers = {"Host": "127.0.0.1:8000", "Origin": wrong_origin}

    async def unused_call_next(_request: Request) -> Never:
        raise AssertionError("OPTIONS must be handled by the local boundary")

    async def exercise_preflights() -> tuple[int, int]:
        api_response = await local_request_boundary(
            request_for(
                path="/api/v1/local-onboarding/student-profiles",
                headers=headers,
                method="OPTIONS",
            ),
            unused_call_next,
        )
        pairing_response = await local_request_boundary(
            request_for(
                path="/local/pairing/complete",
                headers=headers,
                method="OPTIONS",
            ),
            unused_call_next,
        )
        return api_response.status_code, pairing_response.status_code

    api_status, pairing_status = asyncio.run(exercise_preflights())

    assert api_status == 403
    assert pairing_status == 204


def test_unpaired_extension_origin_is_not_granted_cors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "runtime_manifest_path", tmp_path / "runtime.json")
    origin = "chrome-extension://ponmlkjihgfedcbaponmlkjihgfedcba"

    assert _cors_headers(origin) == {}
