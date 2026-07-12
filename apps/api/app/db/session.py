import sqlite3
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args=(
        {"check_same_thread": False}
        if settings.is_local_database
        else {"connect_timeout": settings.database_connect_timeout_seconds}
    ),
)


def enable_sqlite_foreign_keys(
    dbapi_connection: sqlite3.Connection, _connection_record: object
) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


if settings.is_local_database:
    event.listen(engine, "connect", enable_sqlite_foreign_keys)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
