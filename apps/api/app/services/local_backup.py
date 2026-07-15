from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
import threading
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.engine import Engine, make_url

from app.config import APP_ID, settings
from app.db.bootstrap import LOCAL_SCHEMA_VERSION

BACKUP_FORMAT = "sapsos-backup"
BACKUP_FORMAT_VERSION = 1
DATABASE_PAYLOAD_NAME = "database.sqlite"
MANIFEST_NAME = "manifest.json"
BACKUP_MEDIA_TYPE = "application/vnd.sapsos.backup+zip"
MAX_MANIFEST_BYTES = 64 * 1024
MAX_DATABASE_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_BYTES = 768 * 1024 * 1024

_backup_lock = threading.Lock()


class BackupManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format_identifier: str = Field(pattern=r"^sapsos-backup$")
    format_version: int = Field(ge=1)
    application_id: str
    backup_id: UUID
    created_at: datetime
    source_product_mode: str
    source_application_version: str | None = None
    schema_name: str = Field(pattern=r"^LOCAL_DESKTOP$")
    schema_version: int = Field(ge=1)
    database_payload_filename: str = Field(pattern=r"^database\.sqlite$")
    database_size_bytes: int = Field(ge=0)
    database_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    archive_content_allowlist: list[str]
    includes_pairing_credentials: bool
    includes_runtime_state: bool
    encrypted: bool
    source_data_notice: str
    minimum_restore_application_version: str | None = None


class BackupStatus(BaseModel):
    available: bool
    product_mode: str
    schema_name: str
    schema_version: int
    message: str


class BackupError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def active_sqlite_path(engine: Engine) -> Path:
    if settings.product_mode != "LOCAL_DESKTOP":
        raise BackupError("local_desktop_only", "Backup is available only in LOCAL_DESKTOP mode.")
    if engine.dialect.name != "sqlite":
        raise BackupError("sqlite_required", "Backup requires the LOCAL_DESKTOP SQLite database.")
    database = make_url(str(engine.url)).database
    if not database or database == ":memory:":
        raise BackupError("file_database_required", "An in-memory database cannot be backed up.")
    path = Path(database).expanduser().resolve()
    if not path.is_file():
        raise BackupError("database_missing", "The local application database is not available.")
    controlled_root = (
        settings.runtime_manifest_path.parent
        if settings.runtime_manifest_path is not None
        else path.parent
    ).resolve()
    try:
        path.relative_to(controlled_root)
    except ValueError as error:
        raise BackupError(
            "database_path_invalid",
            "The local database is outside the controlled app-data root.",
        ) from error
    return path


def _check_database(connection: sqlite3.Connection) -> None:
    header = connection.execute("PRAGMA application_id").fetchone()
    if header is None:
        raise BackupError("invalid_sqlite", "The local database could not be opened as SQLite.")
    quick = connection.execute("PRAGMA quick_check").fetchall()
    if quick != [("ok",)]:
        raise BackupError("quick_check_failed", "The local database failed SQLite quick_check.")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise BackupError(
            "foreign_key_check_failed", "The local database has foreign-key violations."
        )
    row = connection.execute(
        "SELECT schema_name, schema_version FROM local_schema_versions "
        "WHERE schema_name = 'LOCAL_DESKTOP'"
    ).fetchone()
    if row is None:
        raise BackupError("schema_version_missing", "The local schema-version record is missing.")
    if row != ("LOCAL_DESKTOP", LOCAL_SCHEMA_VERSION):
        raise BackupError("schema_version_unsupported", "The local schema version is unsupported.")


def _snapshot(source: Path, destination: Path) -> None:
    try:
        source_connection = sqlite3.connect(str(source), timeout=10)
        destination_connection = sqlite3.connect(str(destination))
    except sqlite3.Error as error:
        raise BackupError(
            "sqlite_open_failed", "The local database could not be opened."
        ) from error
    try:
        source_connection.backup(destination_connection)
        destination_connection.commit()
        _check_database(destination_connection)
    except sqlite3.Error as error:
        raise BackupError(
            "snapshot_failed", "The local database snapshot could not be created."
        ) from error
    finally:
        source_connection.close()
        destination_connection.close()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_zip_entry(name: str) -> None:
    if "\\" in name or name.startswith("/"):
        raise BackupError("archive_path_invalid", "Backup archive contains an invalid path.")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or name != str(path):
        raise BackupError("archive_path_invalid", "Backup archive contains a traversal path.")


def validate_backup_archive(archive_path: Path) -> BackupManifest:
    if archive_path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise BackupError("archive_too_large", "Backup archive exceeds the supported size limit.")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if names != [MANIFEST_NAME, DATABASE_PAYLOAD_NAME] or len(set(names)) != 2:
                raise BackupError(
                    "archive_entries_invalid",
                    "Backup archive must contain exactly manifest.json and database.sqlite.",
                )
            for info in infos:
                _validate_zip_entry(info.filename)
                if info.flag_bits & 0x1:
                    raise BackupError(
                        "archive_encrypted", "Encrypted backup entries are not supported."
                    )
                if info.is_dir() or (info.external_attr >> 16) & 0o170000 in {0o120000, 0o060000}:
                    raise BackupError(
                        "archive_entry_type_invalid",
                        "Backup archive contains an unsupported entry type.",
                    )
                if info.file_size > (
                    MAX_MANIFEST_BYTES if info.filename == MANIFEST_NAME else MAX_DATABASE_BYTES
                ):
                    raise BackupError(
                        "archive_entry_too_large",
                        "Backup archive entry exceeds the supported size limit.",
                    )
                if info.compress_size and info.file_size / info.compress_size > 1000:
                    raise BackupError(
                        "archive_compression_invalid",
                        "Backup archive compression ratio is unsafe.",
                    )
            manifest_bytes = archive.read(MANIFEST_NAME)
            if len(manifest_bytes) > MAX_MANIFEST_BYTES:
                raise BackupError(
                    "manifest_too_large", "Backup manifest exceeds the supported size limit."
                )
            try:
                manifest = BackupManifest.model_validate_json(manifest_bytes)
            except ValueError as error:
                raise BackupError("manifest_invalid", "Backup manifest is invalid.") from error
            if (
                manifest.format_version != BACKUP_FORMAT_VERSION
                or manifest.application_id != APP_ID
            ):
                raise BackupError(
                    "backup_version_unsupported",
                    "Backup format or application version is unsupported.",
                )
            if manifest.archive_content_allowlist != [MANIFEST_NAME, DATABASE_PAYLOAD_NAME]:
                raise BackupError(
                    "archive_allowlist_invalid", "Backup manifest allowlist is invalid."
                )
            database_bytes = archive.read(DATABASE_PAYLOAD_NAME)
    except zipfile.BadZipFile as error:
        raise BackupError("archive_invalid", "Backup file is not a valid ZIP archive.") from error
    if (
        len(database_bytes) != manifest.database_size_bytes
        or hashlib.sha256(database_bytes).hexdigest() != manifest.database_sha256
    ):
        raise BackupError(
            "database_checksum_mismatch",
            "Backup database checksum or size does not match the manifest.",
        )
    with tempfile.TemporaryDirectory(prefix="sapsos-backup-validate-") as directory:
        candidate = Path(directory) / DATABASE_PAYLOAD_NAME
        candidate.write_bytes(database_bytes)
        connection = sqlite3.connect(candidate)
        try:
            _check_database(connection)
        except sqlite3.Error as error:
            raise BackupError(
                "sqlite_integrity_failed", "Backup database integrity validation failed."
            ) from error
        finally:
            connection.close()
    return manifest


def create_backup_archive(engine: Engine) -> tuple[Path, BackupManifest]:
    with _backup_lock:
        source = active_sqlite_path(engine)
        directory = Path(tempfile.mkdtemp(prefix="sapsos-backup-"))
        snapshot = directory / DATABASE_PAYLOAD_NAME
        archive_path = directory / "SAPSOS-backup.zip"
        try:
            source_connection = sqlite3.connect(source)
            try:
                _check_database(source_connection)
            finally:
                source_connection.close()
            _snapshot(source, snapshot)
            manifest = BackupManifest(
                format_identifier=BACKUP_FORMAT,
                format_version=BACKUP_FORMAT_VERSION,
                application_id=APP_ID,
                backup_id=uuid4(),
                created_at=datetime.now(UTC),
                source_product_mode=settings.product_mode,
                source_application_version="0.1.0",
                schema_name="LOCAL_DESKTOP",
                schema_version=LOCAL_SCHEMA_VERSION,
                database_payload_filename=DATABASE_PAYLOAD_NAME,
                database_size_bytes=snapshot.stat().st_size,
                database_sha256=_sha256(snapshot),
                archive_content_allowlist=[MANIFEST_NAME, DATABASE_PAYLOAD_NAME],
                includes_pairing_credentials=False,
                includes_runtime_state=False,
                encrypted=False,
                source_data_notice=(
                    "This archive contains personal academic data and is not official "
                    "school policy."
                ),
            )
            with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(
                    MANIFEST_NAME,
                    json.dumps(
                        manifest.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
                    ),
                )
                archive.write(snapshot, DATABASE_PAYLOAD_NAME)
            validate_backup_archive(archive_path)
            return archive_path, manifest
        except Exception:
            shutil.rmtree(directory, ignore_errors=True)
            raise


def cleanup_backup_archive(archive_path: Path) -> None:
    shutil.rmtree(archive_path.parent, ignore_errors=True)


def backup_status(engine: Engine) -> BackupStatus:
    if settings.product_mode != "LOCAL_DESKTOP":
        return BackupStatus(
            available=False,
            product_mode=settings.product_mode,
            schema_name="LOCAL_DESKTOP",
            schema_version=LOCAL_SCHEMA_VERSION,
            message="本地备份仅适用于 LOCAL_DESKTOP。",
        )
    try:
        source = active_sqlite_path(engine)
        connection = sqlite3.connect(source)
        try:
            _check_database(connection)
        finally:
            connection.close()
    except (BackupError, sqlite3.Error) as error:
        message = error.message if isinstance(error, BackupError) else "本地数据库完整性检查失败。"
        return BackupStatus(
            available=False,
            product_mode=settings.product_mode,
            schema_name="LOCAL_DESKTOP",
            schema_version=LOCAL_SCHEMA_VERSION,
            message=message,
        )
    return BackupStatus(
        available=True,
        product_mode=settings.product_mode,
        schema_name="LOCAL_DESKTOP",
        schema_version=LOCAL_SCHEMA_VERSION,
        message="可以创建手动本地备份。",
    )
