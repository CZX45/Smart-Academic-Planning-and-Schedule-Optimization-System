from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
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
    normalized_payload: dict[str, Any]
    confidence_score: Decimal = Decimal("0.80")
    requires_review: bool = True


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

    if _is_kean_myprogress_payload(import_type, payload):
        return _parse_kean_myprogress_payload(payload)

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


def _is_kean_myprogress_payload(import_type: DataImportType, payload: Any) -> bool:
    return (
        import_type is DataImportType.DEGREE_AUDIT_EXPORT
        and isinstance(payload, dict)
        and payload.get("page_type") == "KEAN_MY_PROGRESS_PAGE"
    )


def _parse_kean_myprogress_payload(payload: dict[str, Any]) -> list[ParsedImportRecord]:
    program_summary = object_value(payload.get("programSummary"))
    credit_summary = object_value(payload.get("creditSummary"))
    validation = object_value(payload.get("validation"))
    requirement_groups = list_value(payload.get("requirementGroups"))
    course_rows = list_value(payload.get("courseRows"))
    source_page_type = str(payload.get("page_type") or "KEAN_MY_PROGRESS_PAGE")
    validation_status = str(validation.get("status") or "")
    confidence = decimal_confidence(validation.get("overallConfidenceScore"))
    requires_review = validation_status != "AUTO_VERIFIED"
    program_name = str(program_summary.get("programName") or "Kean MyProgress summary")
    records = [
        ParsedImportRecord(
            row_number=1,
            record_type=ImportedRecordType.PROGRAM,
            raw_label=program_name,
            external_identifier=program_name,
            normalized_payload={
                "source_page_type": source_page_type,
                "record_kind": "MY_PROGRESS_PROGRAM_SUMMARY",
                "programSummary": program_summary,
                "creditSummary": credit_summary,
                "progressBarSegments": list_value(payload.get("progressBarSegments")),
                "fieldProvenance": object_value(payload.get("fieldProvenance")),
                "rawSnapshot": object_value(payload.get("rawSnapshot")),
                "validation": validation,
                "requiresReview": requires_review,
                "source_label": "KEAN_STUDENT_PORTAL",
            },
            confidence_score=confidence,
            requires_review=requires_review,
        )
    ]
    row_number = 2
    for group in requirement_groups:
        if not isinstance(group, dict):
            continue
        name = str(group.get("name") or f"MyProgress requirement group {row_number}")
        status_text = str(group.get("statusText") or "")
        group_requires_review = bool(group.get("requiresReview") or requires_review)
        group_confidence = Decimal("0.95") if not group_requires_review else Decimal("0.60")
        records.append(
            ParsedImportRecord(
                row_number=row_number,
                record_type=ImportedRecordType.REQUIREMENT,
                raw_label=name,
                external_identifier=name,
                normalized_payload={
                    "source_page_type": source_page_type,
                    "record_kind": "MY_PROGRESS_REQUIREMENT_GROUP",
                    "requirements": name,
                    "status_text": status_text,
                    "requirementGroup": group,
                    "requiresReview": group_requires_review,
                    "source_label": "KEAN_STUDENT_PORTAL",
                },
                confidence_score=group_confidence,
                requires_review=group_requires_review,
            )
        )
        row_number += 1
    for course_row in course_rows:
        if not isinstance(course_row, dict):
            continue
        normalized = _normalize_row(course_row)
        row_requires_review = requires_review or _course_row_requires_review(normalized)
        records.append(
            ParsedImportRecord(
                row_number=row_number,
                record_type=ImportedRecordType.REQUIREMENT,
                raw_label=normalized.get("course_code")
                or normalized.get("requirements")
                or f"MyProgress row {row_number}",
                external_identifier=normalized.get("course_code") or None,
                normalized_payload={
                    **normalized,
                    "source_page_type": source_page_type,
                    "record_kind": "MY_PROGRESS_COURSE_ROW",
                    "requiresReview": row_requires_review,
                    "source_label": "KEAN_STUDENT_PORTAL",
                },
                confidence_score=Decimal("0.95") if not row_requires_review else Decimal("0.60"),
                requires_review=row_requires_review,
            )
        )
        row_number += 1
    return records


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
    row: dict[str, Any],
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


def object_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def decimal_confidence(value: Any) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")
    if parsed < 0:
        return Decimal("0.00")
    if parsed > 1:
        return Decimal("1.00")
    return parsed.quantize(Decimal("0.01"))


def _course_row_requires_review(row: dict[str, str]) -> bool:
    return not row.get("course_code") or row.get("status", "").upper() in {
        "",
        "UNKNOWN",
        "MANUAL_REVIEW_REQUIRED",
    }
