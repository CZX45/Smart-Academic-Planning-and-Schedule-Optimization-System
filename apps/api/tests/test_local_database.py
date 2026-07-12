from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, select

from app.config import Settings
from app.db.bootstrap import LOCAL_SCHEMA_VERSION, initialize_database, local_schema_versions
from app.db.session import enable_sqlite_foreign_keys


def test_local_desktop_settings_default_to_sqlite_without_environment_file() -> None:
    settings = Settings(_env_file=None)

    assert settings.product_mode == "LOCAL_DESKTOP"
    assert settings.is_local_database is True
    assert settings.database_url.startswith("sqlite+pysqlite:///")


def test_initialize_local_database_is_repeatable_and_versioned(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'sapsos.db'}")

    initialize_database(engine)
    initialize_database(engine)

    with engine.connect() as connection:
        rows = connection.execute(select(local_schema_versions)).all()

    assert len(rows) == 1
    assert rows[0].schema_name == "LOCAL_DESKTOP"
    assert rows[0].schema_version == LOCAL_SCHEMA_VERSION


def test_local_sqlite_connection_enables_foreign_keys() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        enable_sqlite_foreign_keys(connection, None)
        assert connection.execute("PRAGMA foreign_keys").fetchone() == (1,)
    finally:
        connection.close()
