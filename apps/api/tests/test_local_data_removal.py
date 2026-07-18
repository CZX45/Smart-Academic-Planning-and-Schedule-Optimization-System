from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

import app.api.local_data_removal as local_data_removal_api
import app.services.local_data_removal as local_data_removal_service
from app.config import settings
from app.services.local_data_removal import (
    ALLOWLIST,
    CONFIRMATION_TEXT,
    LocalDataRemovalError,
    RemovalCategory,
    RemovalState,
    create_deletion_plan,
    execute_deletion_plan,
    get_persisted_plan_state,
    read_and_validate_plan,
    register_validated_external_backup,
    serialize_plan,
)


def make_root(tmp_path: Path) -> Path:
    root = tmp_path / "SAPSOS"
    root.mkdir()
    for category, entries in ALLOWLIST.items():
        for entry in entries:
            target = root / entry
            if (
                entry.endswith("-safety")
                or entry.endswith("-staging")
                or entry
                in {
                    "local-runtime",
                    "diagnostics-staging",
                    "cache",
                    "deletion-staging",
                }
            ):
                target.mkdir(parents=True, exist_ok=True)
                (target / f"{category.value}.sentinel").write_text("owned", encoding="utf-8")
            else:
                target.write_text(f"{category.value}:{entry}", encoding="utf-8")
    return root


def make_plan(tmp_path: Path, root: Path) -> Path:
    plan = create_deletion_plan(
        root=root,
        application_version="0.1.0",
        categories=tuple(RemovalCategory),
        confirmation=CONFIRMATION_TEXT,
        external_backup_verified=True,
        external_backup_summary="validated backup outside app data",
        now=datetime.now(UTC),
        test_mode=False,
    )
    plan_path = tmp_path / "deletion-plan.json"
    plan_path.write_bytes(serialize_plan(plan))
    return plan_path


def test_plan_requires_exact_confirmation_and_external_backup(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    with pytest.raises(LocalDataRemovalError, match="exact confirmation"):
        create_deletion_plan(
            root=root,
            application_version="0.1.0",
            categories=(RemovalCategory.PERSISTENT_USER_DATA,),
            confirmation="delete sapsos local data",
            external_backup_verified=True,
            external_backup_summary="outside",
            test_mode=False,
        )
    with pytest.raises(LocalDataRemovalError, match="validated external backup"):
        create_deletion_plan(
            root=root,
            application_version="0.1.0",
            categories=(RemovalCategory.PERSISTENT_USER_DATA,),
            confirmation=CONFIRMATION_TEXT,
            external_backup_verified=False,
            external_backup_summary="",
            test_mode=False,
        )


def test_plan_rejects_tampering_expiry_and_replay(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    plan_path = make_plan(tmp_path, root)
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    payload["entries"].append("PERSISTENT_USER_DATA/../outside.sqlite")
    plan_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(LocalDataRemovalError, match="integrity"):
        read_and_validate_plan(plan_path, root=root, application_version="0.1.0", test_mode=False)

    expired = create_deletion_plan(
        root=root,
        application_version="0.1.0",
        categories=(RemovalCategory.PERSISTENT_USER_DATA,),
        confirmation=CONFIRMATION_TEXT,
        external_backup_verified=True,
        external_backup_summary="outside",
        now=datetime(2026, 1, 1, tzinfo=UTC),
        test_mode=False,
    )
    expired_path = tmp_path / "expired.json"
    expired_path.write_bytes(serialize_plan(expired))
    with pytest.raises(LocalDataRemovalError, match="expired"):
        read_and_validate_plan(
            expired_path,
            root=root,
            application_version="0.1.0",
            now=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=11),
            test_mode=False,
        )


def test_successful_execution_deletes_only_fixed_allowlist_and_is_not_replayable(
    tmp_path: Path,
) -> None:
    root = make_root(tmp_path)
    external = tmp_path / "external-backup.sapsos-backup"
    external.write_text("keep", encoding="utf-8")
    outside = tmp_path / "outside.sqlite"
    outside.write_text("keep", encoding="utf-8")
    plan_path = make_plan(tmp_path, root)
    ready_plan = plan_path.read_bytes()

    state, deleted = execute_deletion_plan(
        plan_path,
        root=root,
        application_version="0.1.0",
        test_mode=False,
    )

    assert state is RemovalState.COMPLETED
    assert deleted
    assert root.exists()
    assert not any(root.iterdir())
    assert external.read_text(encoding="utf-8") == "keep"
    assert outside.read_text(encoding="utf-8") == "keep"
    with pytest.raises(LocalDataRemovalError, match="no longer executable"):
        execute_deletion_plan(
            plan_path,
            root=root,
            application_version="0.1.0",
            test_mode=False,
        )
    plan_path.write_bytes(ready_plan)
    with pytest.raises(LocalDataRemovalError, match="nonce"):
        execute_deletion_plan(
            plan_path,
            root=root,
            application_version="0.1.0",
            test_mode=False,
        )


def test_reparse_point_is_rejected_before_recursive_delete(tmp_path: Path) -> None:
    if os.name != "nt":
        pytest.skip("junction validation uses the Windows cmd/mklink boundary")
    root = make_root(tmp_path)
    target = tmp_path / "outside"
    target.mkdir()
    junction = root / "cache"
    for child in junction.iterdir():
        child.unlink()
    junction.rmdir()
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"junction creation unavailable: {result.stderr or result.stdout}")
    plan_path = make_plan(tmp_path, root)
    with pytest.raises(LocalDataRemovalError, match="(?i)reparse"):
        execute_deletion_plan(
            plan_path,
            root=root,
            application_version="0.1.0",
            test_mode=False,
        )
    assert target.exists()


def test_partial_failure_is_persisted_and_status_is_not_replayable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_root(tmp_path)
    external = tmp_path / "external-backup.sapsos-backup"
    external.write_text("keep", encoding="utf-8")
    plan = create_deletion_plan(
        root=root,
        application_version="0.1.0",
        categories=(RemovalCategory.PERSISTENT_USER_DATA,),
        confirmation=CONFIRMATION_TEXT,
        external_backup_verified=True,
        external_backup_summary="validated backup outside app data",
        test_mode=False,
    )
    plan_path = tmp_path / "deletion-plan.json"
    plan_path.write_bytes(serialize_plan(plan))
    original_delete = local_data_removal_service._delete_entry
    calls = 0

    def delete_then_fail(data_root: Path, relative: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            original_delete(data_root, relative)
            return
        raise OSError("simulated deletion failure")

    monkeypatch.setattr(local_data_removal_service, "_delete_entry", delete_then_fail)
    with pytest.raises(LocalDataRemovalError) as error:
        execute_deletion_plan(plan_path, root=root, application_version="0.1.0", test_mode=False)
    assert error.value.code == RemovalState.PARTIALLY_COMPLETED.value
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    assert payload["execution_state"] == RemovalState.PARTIALLY_COMPLETED.value
    assert payload["integrity_hash"] == local_data_removal_service._integrity_hash(payload)
    assert external.read_text(encoding="utf-8") == "keep"
    monkeypatch.setattr(local_data_removal_api, "PLAN_PATH", plan_path)
    monkeypatch.setattr(settings, "product_mode", "LOCAL_DESKTOP")
    assert (
        local_data_removal_api.get_local_data_removal_status().state
        is RemovalState.PARTIALLY_COMPLETED
    )
    with pytest.raises(LocalDataRemovalError, match="no longer executable"):
        execute_deletion_plan(plan_path, root=root, application_version="0.1.0", test_mode=False)


def test_expired_ready_plan_transitions_atomically_and_allows_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_root(tmp_path)
    plan_path = make_plan(tmp_path, root)
    expired_at = datetime.now(UTC) + timedelta(minutes=1)
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    payload["expires_at"] = expired_at.isoformat()
    payload["integrity_hash"] = local_data_removal_service._integrity_hash(payload)
    plan_path.write_text(json.dumps(payload), encoding="utf-8")
    observed_now = expired_at + timedelta(seconds=1)
    assert get_persisted_plan_state(plan_path, now=observed_now) is RemovalState.EXPIRED
    persisted = json.loads(plan_path.read_text(encoding="utf-8"))
    assert persisted["execution_state"] == RemovalState.EXPIRED.value
    assert persisted["integrity_hash"] == local_data_removal_service._integrity_hash(persisted)
    monkeypatch.setattr(local_data_removal_api, "PLAN_PATH", plan_path)
    monkeypatch.setattr(local_data_removal_api, "_app_data_root", lambda: root)
    monkeypatch.setattr(settings, "product_mode", "LOCAL_DESKTOP")
    assert local_data_removal_api.get_local_data_removal_status().state is RemovalState.EXPIRED
    with pytest.raises(LocalDataRemovalError, match="no longer executable"):
        execute_deletion_plan(plan_path, root=root, application_version="0.1.0", test_mode=False)
    receipt = register_validated_external_backup(uuid4())
    response = local_data_removal_api.prepare_local_data_removal(
        local_data_removal_api.PrepareLocalDataRemovalRequest(
            confirmation=CONFIRMATION_TEXT, backup_receipt=receipt
        )
    )
    assert response.state is RemovalState.READY


def test_tampered_expired_ready_plan_is_not_legalized(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    plan_path = make_plan(tmp_path, root)
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    payload["expires_at"] = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    plan_path.write_text(json.dumps(payload), encoding="utf-8")
    assert get_persisted_plan_state(plan_path) is RemovalState.TAMPER_REJECTED
    persisted = json.loads(plan_path.read_text(encoding="utf-8"))
    assert persisted["execution_state"] == RemovalState.READY.value
