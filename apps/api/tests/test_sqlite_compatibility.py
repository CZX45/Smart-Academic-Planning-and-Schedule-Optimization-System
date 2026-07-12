from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.base import Base, DevSeedRecord


def _sqlite_engine(path: Path) -> Engine:
    engine = create_engine(f"sqlite:///{path}")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(
        dbapi_connection: sqlite3.Connection, _connection_record: object
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def test_sqlite_model_metadata_initializes_repeatedly(tmp_path: Path) -> None:
    database_path = tmp_path / "local.db"
    engine = _sqlite_engine(database_path)

    Base.metadata.create_all(engine)
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    assert len(inspector.get_table_names()) == 68
    assert (
        sum(len(inspector.get_foreign_keys(table)) for table in inspector.get_table_names()) == 176
    )
    assert sum(len(inspector.get_indexes(table)) for table in inspector.get_table_names()) == 86


def test_sqlite_uuid_json_and_server_default_round_trip(tmp_path: Path) -> None:
    engine = _sqlite_engine(tmp_path / "local.db")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        record = DevSeedRecord(
            seed_key="sqlite-proof",
            label="SQLite compatibility proof",
            payload={"source": "test", "rows": [1, 2, 3]},
        )
        session.add(record)
        session.commit()
        record_id = record.id

    with Session(engine) as session:
        loaded = session.get(DevSeedRecord, record_id)
        assert loaded is not None
        assert isinstance(loaded.id, UUID)
        assert loaded.payload == {"source": "test", "rows": [1, 2, 3]}
        assert isinstance(loaded.created_at, datetime)


def test_sqlite_enforces_foreign_keys_and_rolls_back_transactions(tmp_path: Path) -> None:
    engine = _sqlite_engine(tmp_path / "local.db")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE parent (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE child ("
                "id INTEGER PRIMARY KEY, "
                "parent_id INTEGER NOT NULL REFERENCES parent(id) ON DELETE CASCADE)"
            )
        )

    with Session(engine) as session:
        session.execute(text("INSERT INTO parent (id) VALUES (1)"))
        session.execute(text("INSERT INTO child (id, parent_id) VALUES (1, 1)"))
        session.commit()

    with Session(engine) as session:
        session.execute(text("DELETE FROM parent WHERE id = 1"))
        session.rollback()
        assert session.scalar(text("SELECT count(*) FROM parent")) == 1
        assert session.scalar(text("SELECT count(*) FROM child")) == 1

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM parent WHERE id = 1"))
        assert connection.scalar(text("SELECT count(*) FROM child")) == 0

    with Session(engine) as session:
        session.add(DevSeedRecord(seed_key="rollback-proof", label="rollback", payload={}))
        session.rollback()
        assert session.scalar(text("SELECT count(*) FROM dev_seed_records")) == 0
