from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


def verify(database_path: Path) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {
        "database_exists": database_path.is_file(),
        "local_schema_versions_table": False,
        "row_count": 0,
        "schema_name_values": [],
        "schema_version_values": [],
        "schema_name": None,
        "schema_version": None,
        "valid": False,
    }
    if not database_path.is_file():
        result["error"] = "database_missing"
        return result, 2

    try:
        uri = f"file:{database_path.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type = 'table' AND name = 'local_schema_versions'"
            ).fetchone()
            if table is None:
                result["error"] = "local_schema_versions_table_missing"
                return result, 1
            result["local_schema_versions_table"] = True
            rows = connection.execute(
                "SELECT schema_name, schema_version FROM local_schema_versions ORDER BY id"
            ).fetchall()
            result["row_count"] = len(rows)
            result["schema_name_values"] = [row[0] for row in rows]
            result["schema_version_values"] = [row[1] for row in rows]
            if len(rows) == 1:
                result["schema_name"], result["schema_version"] = rows[0]
            result["valid"] = rows == [("LOCAL_DESKTOP", 1)]
            if not result["valid"]:
                result["error"] = "unsupported_local_desktop_schema_marker"
                return result, 1
    except (OSError, sqlite3.Error) as error:
        result["error"] = type(error).__name__
        return result, 1
    return result, 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    arguments = parser.parse_args()
    result, exit_code = verify(arguments.database.expanduser().resolve())
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
