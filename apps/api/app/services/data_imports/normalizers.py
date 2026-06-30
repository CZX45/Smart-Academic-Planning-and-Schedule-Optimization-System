from __future__ import annotations

import re

COURSE_CODE_PATTERN = re.compile(r"^\s*([A-Z]{2,8})\s*[-_ ]?\s*([0-9][A-Z0-9]{1,5})\s*$")


def normalize_course_code(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(str(value).strip().upper().replace("-", " ").replace("_", " ").split())
    if not cleaned:
        return None
    match = COURSE_CODE_PATTERN.match(cleaned)
    if match is None:
        compact = cleaned.replace(" ", "")
        match = COURSE_CODE_PATTERN.match(compact)
    if match is None:
        return cleaned
    subject, number = match.groups()
    return f"{subject} {number}"


def split_course_code(value: str | None) -> tuple[str, str] | None:
    normalized = normalize_course_code(value)
    if normalized is None:
        return None
    parts = normalized.split(" ", maxsplit=1)
    if len(parts) != 2:
        return None
    subject, number = parts
    if not subject or not number:
        return None
    return subject, number
