from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from typing import Any

from app.models.academic import DataImportType, ImportedRecordType
from app.services.data_imports.exceptions import DataImportValidationError
from app.services.data_imports.normalizers import normalize_course_code


@dataclass(frozen=True)
class ParsedImportRecord:
    row_number: int
    record_type: ImportedRecordType
    raw_label: str
    external_identifier: str | None
    normalized_payload: dict[str, str]


def parse_import_content(
    *,
    import_type: DataImportType,
    file_name: str,
    file_mime_type: str,
    content: str,
) -> list[ParsedImportRecord]:
    if _looks_like_json(file_name, file_mime_type, content):
        return _parse_json(import_type, content)
    return _parse_csv(import_type, content)


def record_type_for_import(import_type: DataImportType) -> ImportedRecordType:
    if import_type is DataImportType.UNOFFICIAL_TRANSCRIPT:
        return ImportedRecordType.COURSE_ATTEMPT
    if import_type is DataImportType.DEGREE_AUDIT_EXPORT:
        return ImportedRecordType.REQUIREMENT
    if import_type is DataImportType.COURSE_CATALOG:
        return ImportedRecordType.COURSE
    if import_type is DataImportType.SECTION_SCHEDULE:
        return ImportedRecordType.SECTION
    return ImportedRecordType.UNKNOWN


def _looks_like_json(file_name: str, file_mime_type: str, content: str) -> bool:
    stripped = content.lstrip()
    return (
        file_mime_type == "application/json"
        or file_name.lower().endswith(".json")
        or stripped.startswith("{")
        or stripped.startswith("[")
    )


def _parse_csv(import_type: DataImportType, content: str) -> list[ParsedImportRecord]:
    reader = csv.DictReader(io.StringIO(content), skipinitialspace=True)
    if not reader.fieldnames:
        raise DataImportValidationError("empty_import", "Import content must include a header row.")
    records: list[ParsedImportRecord] = []
    for index, row in enumerate(reader, start=2):
        normalized = _normalize_row(row)
        if not any(normalized.values()):
            continue
        records.append(_parsed_record(import_type, index, normalized))
    return records


def _parse_json(import_type: DataImportType, content: str) -> list[ParsedImportRecord]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as error:
        raise DataImportValidationError(
            "invalid_json", "Import content is not valid JSON."
        ) from error

    rows = _json_rows(payload)
    records: list[ParsedImportRecord] = []
    for index, row in enumerate(rows, start=1):
        normalized = _normalize_row(row)
        if not any(normalized.values()):
            continue
        records.append(_parsed_record(import_type, index, normalized))
    return records


def _json_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("records", "attempts", "courses", "sections", "requirements"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
        return [payload]
    raise DataImportValidationError(
        "unsupported_json_shape",
        "JSON imports must be an object or a list of objects.",
    )


def _normalize_row(row: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in row.items():
        if key is None:
            continue
        normalized[_normalize_key(str(key))] = "" if value is None else str(value).strip()

    course_code = _first_value(
        normalized,
        "course_code",
        "course",
        "code",
        "subject_course",
        "catalog_number",
    )
    normalized_course_code = normalize_course_code(course_code)
    if normalized_course_code is not None:
        normalized["course_code"] = normalized_course_code

    normalized.setdefault("term", _first_value(normalized, "term_code", "term", "semester") or "")
    normalized.setdefault("title", _first_value(normalized, "title", "course_title", "name") or "")
    normalized.setdefault("grade", _first_value(normalized, "grade", "final_grade") or "")
    normalized.setdefault("credits", _first_value(normalized, "credits", "credit_hours") or "")
    normalized.setdefault("status", _first_value(normalized, "status", "course_status") or "")
    return normalized


def _normalize_key(value: str) -> str:
    return "_".join(value.strip().lower().replace("-", "_").replace(" ", "_").split("_"))


def _first_value(row: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value:
            return value
    return None


def _parsed_record(
    import_type: DataImportType,
    row_number: int,
    row: dict[str, str],
) -> ParsedImportRecord:
    course_code = row.get("course_code")
    title = row.get("title")
    raw_label_parts = [part for part in (course_code, title) if part]
    raw_label = " ".join(raw_label_parts) or f"Import row {row_number}"
    return ParsedImportRecord(
        row_number=row_number,
        record_type=record_type_for_import(import_type),
        raw_label=raw_label,
        external_identifier=course_code or row.get("external_identifier") or None,
        normalized_payload=row,
    )
