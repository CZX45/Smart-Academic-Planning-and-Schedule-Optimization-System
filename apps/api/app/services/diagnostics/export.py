from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime
from typing import Final

from app.services.diagnostics.models import DiagnosticsSnapshot

MAX_BUNDLE_BYTES: Final = 2 * 1024 * 1024
MAX_EVENT_COUNT: Final = 20
BUNDLE_FORMAT_VERSION: Final = 1
REDACTION_POLICY_VERSION: Final = 1
ALLOWLIST: Final = (
    "manifest.json",
    "diagnostics.json",
    "startup-events.json",
    "README.txt",
)


class DiagnosticsBundleError(ValueError):
    pass


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _files_for_snapshot(snapshot: DiagnosticsSnapshot, generated_at: datetime) -> dict[str, bytes]:
    typed_snapshot = snapshot.model_dump(mode="json")
    events = [event.model_dump(mode="json") for event in snapshot.recent_startup_status.events]
    events = events[-MAX_EVENT_COUNT:]
    files: dict[str, bytes] = {
        "diagnostics.json": _json_bytes(typed_snapshot),
        "startup-events.json": _json_bytes(events),
        "README.txt": b"".join(
            (
                b"This diagnostics bundle was generated manually by the local application.\n",
                b"It is stored on your device unless you choose to share it.\n",
                b"It does not contain the database, school account data, or school credentials.\n",
                b"Please inspect the contents before sharing. It is not an official "
                b"school record.\n",
                b"Delete this file using your normal file manager when it is no longer needed.\n",
            )
        ),
    }
    hashes = {name: hashlib.sha256(files[name]).hexdigest() for name in files}
    files["manifest.json"] = _json_bytes(
        {
            "bundle_format_version": BUNDLE_FORMAT_VERSION,
            "generated_at": generated_at.isoformat(),
            "application_version": snapshot.application_version,
            "application_mode": snapshot.application_mode,
            "platform_summary": snapshot.platform_summary.model_dump(mode="json"),
            "diagnostics_contract_version": snapshot.contract_version,
            "file_list": list(ALLOWLIST),
            "sha256": hashes,
            "privacy_statement": (
                "Fixed allowlist; no database, school data, credentials, or secrets."
            ),
            "explicit_exclusions": [
                "database files and SQLite sidecars",
                "backup archives",
                "raw logs, tracebacks, commands, and arbitrary files",
                "student data, school portal data, credentials, and pairing secrets",
            ],
            "redaction_policy_version": REDACTION_POLICY_VERSION,
        }
    )
    return {name: files[name] for name in ALLOWLIST}


def _validate_archive(archive: bytes, files: dict[str, bytes]) -> None:
    if len(archive) > MAX_BUNDLE_BYTES:
        raise DiagnosticsBundleError("diagnostics_bundle_too_large")
    with zipfile.ZipFile(io.BytesIO(archive), "r") as bundle:
        names = bundle.namelist()
        if names != list(ALLOWLIST):
            raise DiagnosticsBundleError("diagnostics_bundle_entries_invalid")
        for name in names:
            if name not in files or name.startswith("/") or ".." in name.split("/"):
                raise DiagnosticsBundleError("diagnostics_bundle_path_invalid")
            if bundle.getinfo(name).is_dir():
                raise DiagnosticsBundleError("diagnostics_bundle_directory_invalid")
            if bundle.read(name) != files[name]:
                raise DiagnosticsBundleError("diagnostics_bundle_content_invalid")
        manifest = json.loads(files["manifest.json"])
        if manifest["file_list"] != names:
            raise DiagnosticsBundleError("diagnostics_bundle_manifest_invalid")
        for name in names[1:]:
            if manifest["sha256"][name] != hashlib.sha256(files[name]).hexdigest():
                raise DiagnosticsBundleError("diagnostics_bundle_hash_invalid")


def build_diagnostics_bundle(snapshot: DiagnosticsSnapshot) -> bytes:
    if snapshot.application_mode != "LOCAL_DESKTOP":
        raise DiagnosticsBundleError("local_diagnostics_unavailable")
    generated_at = datetime.now(UTC)
    files = _files_for_snapshot(snapshot, generated_at)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in ALLOWLIST:
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, files[name])
    archive = buffer.getvalue()
    _validate_archive(archive, files)
    return archive
