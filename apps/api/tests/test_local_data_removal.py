from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.services.local_data_removal import (
    ALLOWLIST,
    CONFIRMATION_TEXT,
    LocalDataRemovalError,
    RemovalCategory,
    RemovalState,
    create_deletion_plan,
    execute_deletion_plan,
    read_and_validate_plan,
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
