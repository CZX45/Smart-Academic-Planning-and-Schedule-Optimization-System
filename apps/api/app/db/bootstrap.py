from __future__ import annotations

from pathlib import Path

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    func,
    insert,
    select,
    text,
)
from sqlalchemy.engine import Engine, make_url

from app.db.base import Base

LOCAL_SCHEMA_VERSION = 1

_local_metadata = MetaData()
local_schema_versions = Table(
    "local_schema_versions",
    _local_metadata,
    Column("id", Integer, primary_key=True),
    Column("schema_version", Integer, nullable=False),
    Column("schema_name", String(80), nullable=False, unique=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


def _ensure_database_directory(engine: Engine) -> None:
    database = make_url(str(engine.url)).database
    if database and database != ":memory:":
        Path(database).expanduser().parent.mkdir(parents=True, exist_ok=True)


def initialize_database(engine: Engine) -> None:
    """Initialize the deterministic LOCAL_DESKTOP schema without running SERVER migrations."""

    if engine.dialect.name != "sqlite":
        return

    _ensure_database_directory(engine)
    _local_metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
        existing_version = connection.scalar(
            select(local_schema_versions.c.schema_version).where(
                local_schema_versions.c.schema_name == "LOCAL_DESKTOP"
            )
        )
        if existing_version is None:
            Base.metadata.create_all(connection)
            connection.execute(
                insert(local_schema_versions).values(
                    id=1,
                    schema_version=LOCAL_SCHEMA_VERSION,
                    schema_name="LOCAL_DESKTOP",
                )
            )
        elif existing_version != LOCAL_SCHEMA_VERSION:
            raise RuntimeError(
                "Unsupported LOCAL_DESKTOP schema version: "
                f"{existing_version}; expected {LOCAL_SCHEMA_VERSION}."
            )
        else:
            Base.metadata.create_all(connection)
