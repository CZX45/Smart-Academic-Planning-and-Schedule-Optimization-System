from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GradeDecision:
    is_satisfied: bool
    warning_code: str | None = None
    message: str | None = None


class GradePolicy:
    def __init__(self, grade_order: tuple[str, ...] | None = None) -> None:
        self._grade_order = grade_order or (
            "A",
            "A-",
            "B+",
            "B",
            "B-",
            "C+",
            "C",
            "C-",
            "D+",
            "D",
            "D-",
            "F",
        )
        self._rank = {grade: index for index, grade in enumerate(self._grade_order)}

    def satisfies_minimum(self, grade: str | None, minimum_grade: str | None) -> GradeDecision:
        normalized_grade = grade.strip().upper() if grade else None
        normalized_minimum = minimum_grade.strip().upper() if minimum_grade else None

        if normalized_grade is None:
            if normalized_minimum is None:
                return GradeDecision(is_satisfied=True)
            return GradeDecision(
                is_satisfied=False,
                warning_code="UNKNOWN_GRADE",
                message="A minimum grade is configured but the student record has no grade.",
            )

        if normalized_grade in {"W", "AU", "NC"}:
            return GradeDecision(is_satisfied=False)

        if normalized_grade == "I":
            return GradeDecision(
                is_satisfied=False,
                warning_code="INCOMPLETE_GRADE",
                message="Incomplete grades are not treated as completed in Phase 3A.",
            )

        if normalized_grade in {"P", "S", "CR"}:
            if normalized_minimum is None:
                return GradeDecision(is_satisfied=True)
            return GradeDecision(
                is_satisfied=False,
                warning_code="PASS_FAIL_MINIMUM_GRADE_REVIEW",
                message="Pass/fail grades require advisor confirmation for minimum-grade rules.",
            )

        if normalized_grade not in self._rank:
            return GradeDecision(
                is_satisfied=False,
                warning_code="UNKNOWN_GRADE",
                message=f"Grade {normalized_grade} is not known to the mock grade policy.",
            )

        if normalized_minimum is None:
            return GradeDecision(is_satisfied=normalized_grade != "F")

        if normalized_minimum not in self._rank:
            return GradeDecision(
                is_satisfied=False,
                warning_code="UNKNOWN_MINIMUM_GRADE",
                message=f"Minimum grade {normalized_minimum} is not known to the mock policy.",
            )

        return GradeDecision(
            is_satisfied=self._rank[normalized_grade] <= self._rank[normalized_minimum]
        )

    def best_grade_key(self, grade: str | None) -> int:
        normalized = grade.strip().upper() if grade else ""
        return self._rank.get(normalized, len(self._rank) + 1)
