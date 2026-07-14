from __future__ import annotations

import time
from pathlib import Path

import pytest
from starlette.requests import Request

from app.config import settings
from app.security.local_request import (
    _cors_headers,
    _parse_host,
    _validate_local_request,
)
from app.security.pairing import PAIRING_PROTOCOL_VERSION, PairingStore

EXTENSION_ID = "abcdefghijklmnopabcdefghijklmnop"


def request_for(
    *,
    path: str,
    headers: dict[str, str],
    client_host: str = "127.0.0.1",
) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
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


def test_unpaired_extension_origin_is_not_granted_cors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "runtime_manifest_path", tmp_path / "runtime.json")
    origin = "chrome-extension://ponmlkjihgfedcbaponmlkjihgfedcba"

    assert _cors_headers(origin) == {}
