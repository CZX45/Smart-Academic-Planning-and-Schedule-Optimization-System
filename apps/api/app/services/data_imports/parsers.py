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

SUPPORTED_MYPROGRESS_STATUSES = {
    "COMPLETED",
    "IN_PROGRESS",
    "PLANNED",
    "NOT_STARTED",
    "TRANSFERRED",
    "WAIVED",
    "SUBSTITUTED",
    "UNKNOWN",
}
MYPROGRESS_STATUS_ALIASES = {
    "CURRENT": "IN_PROGRESS",
    "REGISTERED": "IN_PROGRESS",
    "FULLY_PLANNED": "PLANNED",
    "SATISFIED": "COMPLETED",
    "ATTEMPTED": "COMPLETED",
}


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
    course_rows = list_value(payload.get("courseRows")) or list_value(payload.get("requirements"))
    raw_snapshot = object_value(payload.get("rawSnapshot"))
    if _is_empty_kean_myprogress_payload(
        program_summary=program_summary,
        credit_summary=credit_summary,
        requirement_groups=requirement_groups,
        course_rows=course_rows,
        raw_snapshot=raw_snapshot,
    ):
        raise DataImportValidationError(
            "missing_myprogress_payload",
            (
                "Kean MyProgress browser-extension import did not include summary fields, "
                "requirement groups, or course rows. Re-extract the page before confirming."
            ),
        )
    raw_diagnostics = object_value(raw_snapshot.get("diagnostics"))
    extraction_bounded = bool(
        payload.get("bounded")
        or raw_diagnostics.get("bounded")
        or raw_diagnostics.get("truncated")
        or object_value(payload.get("diagnostics")).get("bounded")
    )
    extraction_truncated = bool(
        payload.get("truncated")
        or raw_diagnostics.get("truncated")
        or object_value(payload.get("diagnostics")).get("truncated")
    )
    extraction_warnings = list_value(payload.get("warnings"))
    source_page_type = str(payload.get("page_type") or "KEAN_MY_PROGRESS_PAGE")
    source_type = str(payload.get("source_type") or "BROWSER_EXTENSION")
    confidence = decimal_confidence(validation.get("overallConfidenceScore"))
    # AUTO_VERIFIED describes parser consistency only. Imported MyProgress data
    # must still pass the explicit user Review step before it is applyable.
    requires_review = True
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
                "rawSnapshot": raw_snapshot,
                "validation": validation,
                "extractionWarnings": extraction_warnings,
                "extractionBounded": extraction_bounded,
                "extractionTruncated": extraction_truncated,
                "requiresReview": requires_review,
                "source_label": "KEAN_STUDENT_PORTAL",
                "source_type": source_type,
                "is_official": False,
                "advisory_only": True,
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
        group_requires_review = True
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
                    "raw_text": str(group.get("rawText") or status_text or name),
                    "confidence": str(group.get("confidence") or "high"),
                    "requiresReview": group_requires_review,
                    "source_label": "KEAN_STUDENT_PORTAL",
                    "source_type": source_type,
                    "is_official": False,
                    "advisory_only": True,
                },
                confidence_score=group_confidence,
                requires_review=group_requires_review,
            )
        )
        row_number += 1
    for course_row in course_rows:
        if not isinstance(course_row, dict):
            continue
        normalized = _normalize_myprogress_course_row(
            course_row,
            source_page_type=source_page_type,
            source_type=source_type,
            extraction_bounded=extraction_bounded,
            extraction_truncated=extraction_truncated,
        )
        row_requires_review = True
        row_confidence = decimal_confidence(normalized.get("confidence_score"))
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
                    "source_type": source_type,
                    "is_official": False,
                    "advisory_only": True,
                },
                confidence_score=row_confidence,
                requires_review=row_requires_review,
            )
        )
        row_number += 1
    return records


def _is_empty_kean_myprogress_payload(
    *,
    program_summary: dict[str, Any],
    credit_summary: dict[str, Any],
    requirement_groups: list[Any],
    course_rows: list[Any],
    raw_snapshot: dict[str, Any],
) -> bool:
    raw_diagnostics = object_value(raw_snapshot.get("diagnostics"))
    raw_row_count = raw_diagnostics.get("rowCount") or raw_diagnostics.get("courseLikeRowCount")
    return (
        not any(program_summary.values())
        and not any(credit_summary.values())
        and not requirement_groups
        and not course_rows
        and not raw_row_count
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
    row: dict[str, Any],
) -> ParsedImportRecord:
    if import_type is DataImportType.SECTION_SCHEDULE:
        return _parsed_section_record(row_number, row)
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


def _parsed_section_record(row_number: int, row: dict[str, Any]) -> ParsedImportRecord:
    payload = _normalize_section_row(row)
    course_code = str(payload.get("course_code") or "").strip()
    section_code = str(payload.get("section_code") or "").strip()
    raw_label = " ".join(
        part for part in (course_code, section_code, payload.get("course_title")) if part
    )
    state = str(payload.get("validation_state") or "REQUIRES_EXCEPTION_REVIEW")
    confidence = Decimal("0.95") if state == "AUTO_VERIFIED" else Decimal("0.60")
    if state == "FAILED":
        confidence = Decimal("0.00")
    return ParsedImportRecord(
        row_number=row_number,
        record_type=ImportedRecordType.SECTION,
        raw_label=raw_label or f"Section row {row_number}",
        external_identifier=str(payload.get("external_reference") or "") or None,
        normalized_payload=payload,
        confidence_score=confidence,
        requires_review=True,
    )


def _normalize_section_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = dict(_normalize_row(row))
    normalized["course_title"] = _first_value(normalized, "course_title", "title", "name") or ""
    normalized["term"] = _first_value(normalized, "term_code", "term", "semester") or ""
    normalized["section_code"] = (
        _first_value(normalized, "section_code", "section", "class_section") or ""
    )
    normalized["external_reference"] = _first_value(
        normalized, "external_reference", "crn", "external_id", "class_id"
    ) or ""
    for json_field in (
        "meetings_json",
        "field_provenance_json",
        "availability_evidence_json",
        "mapping_candidates_json",
    ):
        raw_value = normalized.get(json_field, "")
        if isinstance(raw_value, str) and raw_value:
            try:
                parsed = json.loads(raw_value)
            except json.JSONDecodeError:
                parsed = {"raw": raw_value}
            normalized[json_field] = parsed
    normalized["source_type"] = (
        "BROWSER_EXTENSION"
        if normalized.get("source_type") == ""
        else normalized.get("source_type")
    )
    normalized["is_official"] = False
    normalized["advisory_only"] = True
    normalized["requires_review"] = True
    normalized["section_validation_state"] = (
        normalized.get("validation_state") or "REQUIRES_EXCEPTION_REVIEW"
    )
    normalized["structural_import"] = True
    return normalized


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


def _normalize_myprogress_course_row(
    row: dict[str, Any],
    *,
    source_page_type: str,
    source_type: str,
    extraction_bounded: bool,
    extraction_truncated: bool,
) -> dict[str, Any]:
    normalized_strings = _normalize_row(row)
    normalized: dict[str, Any] = dict(normalized_strings)
    status = _normalize_myprogress_status(normalized_strings.get("status", ""))
    if status is not None:
        normalized["status"] = status

    requirement_context = _first_value(
        normalized_strings,
        "requirement_group_context",
        "requirement_section",
        "requirements",
        "requirement",
    )
    raw_row_text = _first_value(normalized_strings, "raw_row_text", "raw_text") or " ".join(
        part
        for part in (
            normalized_strings.get("status"),
            normalized_strings.get("course_code"),
            normalized_strings.get("title"),
            normalized_strings.get("term"),
            normalized_strings.get("credits"),
        )
        if part
    )
    confidence_label = _first_value(normalized_strings, "confidence", "confidence_level") or "high"
    reason_codes: list[str] = []
    warnings: list[str] = []
    if not normalized.get("course_code"):
        reason_codes.append("MISSING_COURSE_CODE")
    if normalized.get("course_code") and not normalized.get("title"):
        reason_codes.append("MISSING_TITLE")
    if status is None:
        reason_codes.append("UNKNOWN_STATUS")
    if confidence_label.lower() not in {"high", "medium"}:
        warnings.append("LOW_CONFIDENCE_COURSE_ROW")
    if extraction_bounded or extraction_truncated:
        warnings.append("BOUNDED_OR_TRUNCATED_EXTRACTION")

    normalized.update(
        {
            "term": normalized.get("term", ""),
            "title": normalized.get("title", ""),
            "requirement_group_context": requirement_context or "",
            "raw_row_text": raw_row_text,
            "source_table_index": normalized.get("source_table_index", ""),
            "source_row_index": normalized.get("source_row_index", ""),
            "source_field_provenance": object_value(
                row.get("field_provenance") or row.get("fieldProvenance")
            ),
            "source_page_type": source_page_type,
            "source_type": source_type,
            "extraction_bounded": extraction_bounded,
            "extraction_truncated": extraction_truncated,
            "row_warnings": [*warnings, *[str(item) for item in list_value(row.get("warnings"))]],
            "row_validation": {
                "reason_codes": reason_codes,
                "warnings": warnings,
            },
            "confidence_score": "0.95"
            if confidence_label.lower() == "high" and not reason_codes
            else "0.70"
            if confidence_label.lower() == "medium" and not reason_codes
            else "0.30",
        }
    )
    return normalized


def _normalize_myprogress_status(value: str) -> str | None:
    status = value.strip().upper().replace("-", "_").replace(" ", "_")
    status = MYPROGRESS_STATUS_ALIASES.get(status, status)
    return status if status in SUPPORTED_MYPROGRESS_STATUSES else None


def _course_row_requires_review(row: dict[str, str]) -> bool:
    return not row.get("course_code") or row.get("status", "").upper() in {
        "",
        "UNKNOWN",
        "MANUAL_REVIEW_REQUIRED",
    }
