"""Validate imported summary shape without promoting it to academic policy."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

TEXT_FIELDS = {"programName", "degree", "major", "department"}
NAVIGATION = re.compile(
    r"\b(?:show|hide|view|print|notes?|progress|completion|requirements?|status|course|"
    r"grade|term|credits?|completed|not started|home|announcements?|help|sign out|"
    r"log out|copyright|privacy)\b",
    re.IGNORECASE,
)
COURSE_CODE = re.compile(r"\b[A-Z]{2,8}[ *-]?\d{3,4}[A-Z]?\b", re.IGNORECASE)


def summary_value_is_plausible(key: str, value: Any) -> bool:
    if key in TEXT_FIELDS:
        return (
            isinstance(value, str)
            and bool(value.strip())
            and len(value) <= 80
            and len(value.split()) <= 10
            and "|" not in value
            and NAVIGATION.search(value) is None
            and COURSE_CODE.search(value) is None
        )
    if key == "catalogYear":
        return (
            not isinstance(value, bool) and re.fullmatch(r"(?:19|20)\d{2}", str(value)) is not None
        )
    if key in {"cumulativeGpa", "institutionGpa"}:
        if isinstance(value, bool):
            return False
        try:
            number = Decimal(str(value))
            return number.is_finite() and Decimal(0) <= number <= Decimal(5)
        except (InvalidOperation, ValueError):
            return False
    return True


def validate_summary(
    summary: dict[str, Any],
    validation: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    rejected = {
        key: value for key, value in summary.items() if not summary_value_is_plausible(key, value)
    }
    if not rejected:
        return summary, validation, rejected
    accepted = {key: value for key, value in summary.items() if key not in rejected}
    raw_exceptions = validation.get("exceptions")
    exceptions = list(raw_exceptions) if isinstance(raw_exceptions, list) else []
    exceptions.extend(
        {
            "code": "MY_PROGRESS_SUMMARY_FIELD_INVALID",
            "source": key,
            "severity": "ERROR",
            "message": "Imported summary field is invalid; inspect and re-extract the source.",
        }
        for key in rejected
    )
    return (
        accepted,
        {
            **validation,
            "status": "FAILED",
            "exceptions": exceptions,
            "exceptionCount": len(exceptions),
            "overallConfidenceScore": 0,
            "autoConfirmedFieldCount": 0,
            "downstreamAnalysisAllowed": False,
        },
        rejected,
    )
