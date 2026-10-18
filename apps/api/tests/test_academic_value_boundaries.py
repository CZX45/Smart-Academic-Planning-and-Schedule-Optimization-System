from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.services.course_state.engine import CourseStateApplicationService
from app.services.data_imports.normalizers import normalize_course_code
from app.services.degree_audit.grade_policy import GradePolicy


@pytest.mark.parametrize("value", ["FIN*3000", "fin * 3000", "FIN-3000", "FIN3000", "FIN_3000"])
def test_course_identity_accepts_source_delimiters(value: str) -> None:
    assert normalize_course_code(value) == "FIN 3000"


def test_compound_course_reference_is_not_invented_as_one_identity() -> None:
    assert normalize_course_code("FIN*3000/4000") != "FIN 3000"


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, Decimal("0")),
        ("0", Decimal("0")),
        (None, None),
        ("NaN", None),
        ("Infinity", None),
        (True, None),
        ("-1", None),
    ],
)
def test_course_state_credit_boundary_preserves_zero_and_rejects_unknown(
    value: object,
    expected: Decimal | None,
) -> None:
    with Session() as session:
        assert CourseStateApplicationService(session)._credits(value) == expected


def test_blank_grade_and_minimum_are_equivalent_to_missing_values() -> None:
    policy = GradePolicy()
    assert policy.satisfies_minimum("  ", None).is_satisfied
    assert policy.satisfies_minimum("A", "  ").is_satisfied
    missing_with_minimum = policy.satisfies_minimum(" ", "C")
    assert not missing_with_minimum.is_satisfied
    assert missing_with_minimum.warning_code == "UNKNOWN_GRADE"
