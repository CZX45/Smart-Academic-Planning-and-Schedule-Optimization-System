import json
from decimal import Decimal

import pytest

from app.models.academic import DataImportType
from app.services.data_imports.parsers import decimal_confidence, parse_import_content


@pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity", "1e999999"])
def test_non_finite_confidence_is_not_trusted(value: str) -> None:
    assert decimal_confidence(value) == Decimal("0.00")


@pytest.mark.parametrize(
    "field,value",
    [
        ("programName", "Notes Show Program Notes"),
        ("degree", "Home Announcements Help"),
        ("major", "Major Requirements FIN 3000 Finance A 3 Credits"),
        ("cumulativeGpa", "NaN"),
        ("catalogYear", "2024 navigation"),
    ],
)
def test_old_extension_cannot_import_invalid_summary_as_verified(field: str, value: str) -> None:
    payload = {
        "page_type": "KEAN_MY_PROGRESS_PAGE",
        "programSummary": {"programName": "Synthetic Finance, BS", field: value},
        "validation": {
            "status": "AUTO_VERIFIED",
            "overallConfidenceScore": 1,
            "downstreamAnalysisAllowed": True,
        },
    }
    record = parse_import_content(
        import_type=DataImportType.DEGREE_AUDIT_EXPORT,
        file_name="synthetic.json",
        file_mime_type="application/json",
        content=json.dumps(payload),
    )[0]
    assert record.confidence_score < 1
    assert record.requires_review
    normalized = record.normalized_payload
    assert field not in normalized["programSummary"]
    assert normalized["rejectedSummaryFields"][field] == value
    assert normalized["validation"]["status"] == "FAILED"
    assert normalized["validation"]["downstreamAnalysisAllowed"] is False
