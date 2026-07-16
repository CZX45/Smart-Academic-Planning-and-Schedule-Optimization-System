from __future__ import annotations

import re

_AUTH_RE = re.compile(r"(?i)\b(?:authorization\s*[:=]\s*)?bearer\s+[^\s,;]+")
_SECRET_RE = re.compile(
    r"(?i)\b(?:password|passwd|token|secret|cookie|session|proof|nonce|api[_-]?key)\s*[:=]\s*[^\s,;]+"
)
_DRIVE_PATH_RE = re.compile(r"(?i)\b[A-Z]:\\[^\s\"'<>]+")
_UNC_PATH_RE = re.compile(r"\\\\[^\s\"'<>]+")
_EMAIL_RE = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b", re.I
)
_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)
_TRACEBACK_LINE_RE = re.compile(
    r"(?m)^\s*(?:File \".*?\", line \d+.*|Traceback \(most recent call last\):).*$"
)


def _safe_url(_: re.Match[str]) -> str:
    return "[URL_REDACTED]"


def sanitize_free_text(value: object, *, fallback: str = "[REDACTED]") -> str:
    """Fail-closed redaction for legacy free text; structured errors are preferred."""

    if not isinstance(value, str) or not value.strip():
        return fallback
    text = value[:512]
    text = _TRACEBACK_LINE_RE.sub("[TRACEBACK_REDACTED]", text)
    text = _URL_RE.sub(_safe_url, text)
    text = _AUTH_RE.sub("[AUTH_REDACTED]", text)
    text = _SECRET_RE.sub("[SECRET_REDACTED]", text)
    text = _DRIVE_PATH_RE.sub("[PATH_REDACTED]", text)
    text = _UNC_PATH_RE.sub("[PATH_REDACTED]", text)
    text = _EMAIL_RE.sub("[EMAIL_REDACTED]", text)
    text = _UUID_RE.sub("[ID_REDACTED]", text)
    if "traceback" in text.lower() or "select " in text.lower() or "insert " in text.lower():
        return "[DETAILS_REDACTED]"
    return " ".join(text.split())[:240] or fallback


def sanitize_structured_summary(code: str, component: str, stage: str) -> str:
    """Build a stable summary from allowlisted fields without accepting raw error text."""

    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", code or "unknown")[:80]
    safe_component = re.sub(r"[^A-Za-z0-9_.-]", "_", component or "unknown")[:40]
    safe_stage = re.sub(r"[^A-Za-z0-9_.-]", "_", stage or "unknown")[:40]
    return f"{safe_component}:{safe_stage}:{safe}"
