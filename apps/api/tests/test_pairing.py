from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.security.pairing import (
    PAIRING_CODE_BYTES,
    PAIRING_PROTOCOL_VERSION,
    PairingError,
    PairingStore,
    extension_id_from_origin,
)

EXTENSION_ID = "abcdefghijklmnopabcdefghijklmnop"


def test_pairing_code_is_random_usable_and_single_use(tmp_path: Path) -> None:
    store = PairingStore(tmp_path / "pairing.json")
    code, expires_at = store.create_code()

    assert len(code) >= PAIRING_CODE_BYTES
    assert expires_at > datetime.now(UTC)
    completion = store.complete(code, EXTENSION_ID, PAIRING_PROTOCOL_VERSION)
    assert completion.credential.startswith("sapsos_ext_")
    assert store.status().paired is True
    with pytest.raises(PairingError, match="invalid"):
        store.complete(code, EXTENSION_ID, PAIRING_PROTOCOL_VERSION)


def test_pairing_rejects_wrong_protocol_and_expired_code(tmp_path: Path) -> None:
    path = tmp_path / "pairing.json"
    store = PairingStore(path)
    code, _ = store.create_code()
    with pytest.raises(PairingError, match="protocol"):
        store.complete(code, EXTENSION_ID, PAIRING_PROTOCOL_VERSION + 1)

    state = json.loads(path.read_text(encoding="utf-8"))
    state["session"]["expires_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    path.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(PairingError, match="expired"):
        store.complete(code, EXTENSION_ID, PAIRING_PROTOCOL_VERSION)


def test_pairing_attempts_are_rate_limited_and_revocable(tmp_path: Path) -> None:
    store = PairingStore(tmp_path / "pairing.json")
    store.create_code()
    for _ in range(8):
        with pytest.raises(PairingError, match="invalid"):
            store.complete("wrong-code", EXTENSION_ID, PAIRING_PROTOCOL_VERSION)
    with pytest.raises(PairingError, match="Too many"):
        store.complete("wrong-code", EXTENSION_ID, PAIRING_PROTOCOL_VERSION)

    store = PairingStore(tmp_path / "other-pairing.json")
    code, _ = store.create_code()
    completion = store.complete(code, EXTENSION_ID, PAIRING_PROTOCOL_VERSION)
    assert store.verify(completion.credential, EXTENSION_ID)
    store.revoke()
    assert store.verify(completion.credential, EXTENSION_ID) is False


def test_pairing_verifier_persists_without_plaintext_credential(tmp_path: Path) -> None:
    path = tmp_path / "pairing.json"
    store = PairingStore(path)
    code, _ = store.create_code()
    completion = store.complete(code, EXTENSION_ID, PAIRING_PROTOCOL_VERSION)
    persisted = path.read_text(encoding="utf-8")
    assert completion.credential not in persisted
    restarted = PairingStore(path)
    assert restarted.verify(completion.credential, EXTENSION_ID)


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        (f"chrome-extension://{EXTENSION_ID}", EXTENSION_ID),
        ("https://example.test", None),
        ("chrome-extension://not-an-extension", None),
        ("null", None),
        (None, None),
    ],
)
def test_extension_origin_is_strictly_parsed(origin: str | None, expected: str | None) -> None:
    assert extension_id_from_origin(origin) == expected


def test_pairing_http_flow_requires_expected_origins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "runtime_manifest_path", tmp_path / "runtime.json")
    client = TestClient(app)
    desktop_headers = {"Origin": "http://tauri.localhost"}
    extension_headers = {"Origin": f"chrome-extension://{EXTENSION_ID}"}

    denied = client.post("/local/pairing/session", headers={"Origin": "https://example.test"})
    assert denied.status_code == 403
    session = client.post("/local/pairing/session", headers=desktop_headers)
    assert session.status_code == 200
    code = session.json()["code"]
    completed = client.post(
        "/local/pairing/complete",
        headers=extension_headers,
        json={"code": code, "protocol_version": PAIRING_PROTOCOL_VERSION},
    )
    assert completed.status_code == 200
    assert completed.json()["credential"].startswith("sapsos_ext_")
    status = client.get("/local/pairing/status", headers=extension_headers)
    assert status.status_code == 200
    assert status.json() == {
        "paired": True,
        "extension_id": EXTENSION_ID,
        "protocol_version": PAIRING_PROTOCOL_VERSION,
    }
