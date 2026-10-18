"""Read-only schema gate for the actual packaged first-launch database."""

import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from app.db.bootstrap import LOCAL_SCHEMA_VERSION

VERIFIER = Path(__file__).parents[1] / "scripts/verify_local_desktop_schema.py"


@pytest.mark.parametrize(
    "rows,expected_exit",
    [
        ([("LOCAL_DESKTOP", LOCAL_SCHEMA_VERSION)], 0),
        ([("LOCAL_DESKTOP", LOCAL_SCHEMA_VERSION - 1)], 1),
        ([("LOCAL_DESKTOP", LOCAL_SCHEMA_VERSION + 1)], 1),
        ([("OTHER_SCHEMA", LOCAL_SCHEMA_VERSION)], 1),
        ([("LOCAL_DESKTOP", LOCAL_SCHEMA_VERSION)] * 2, 1),
    ],
)
def test_packaged_schema_gate_accepts_only_current_unique_marker_without_writes(
    tmp_path: Path, rows: list[tuple[str, int]], expected_exit: int
) -> None:
    database = tmp_path / "合成 #database.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE local_schema_versions "
            "(id INTEGER PRIMARY KEY, schema_name TEXT, schema_version INTEGER)"
        )
        connection.executemany(
            "INSERT INTO local_schema_versions (schema_name, schema_version) VALUES (?, ?)", rows
        )
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    result = subprocess.run(
        [sys.executable, str(VERIFIER), str(database)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == expected_exit, result.stderr
    payload = json.loads(result.stdout)
    assert payload["valid"] is (expected_exit == 0)
    assert payload["row_count"] == len(rows)
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before


def test_packaged_schema_gate_does_not_create_a_missing_database(tmp_path: Path) -> None:
    database = tmp_path / "missing.sqlite"
    result = subprocess.run(
        [sys.executable, str(VERIFIER), str(database)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["error"] == "database_missing"
    assert not database.exists()
