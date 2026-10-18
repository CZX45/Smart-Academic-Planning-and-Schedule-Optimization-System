from __future__ import annotations

from dataclasses import dataclass

from app.services.reviewed_rules.contracts import (
    CatalogRuleSet,
    RuleLifecycle,
    RuleValidationState,
)


class RuleLifecycleError(ValueError):
    pass


@dataclass(frozen=True)
class RuleValidationResult:
    state: RuleValidationState
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


SUPPORTED_OPERATORS = {"REQUIRED_COURSE", "ALL_OF", "ANY_OF", "CHOOSE_N", "MINIMUM_CREDITS"}


def validate_rule_set(rule_set: CatalogRuleSet) -> RuleValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    course_ids = [course.course_id for course in rule_set.courses]
    if len(course_ids) != len(set(course_ids)):
        errors.append("duplicate course definitions")
    rule_ids = [rule.rule_id for rule in rule_set.requirements]
    if len(rule_ids) != len(set(rule_ids)):
        errors.append("duplicate rule IDs")
    known_courses = set(course_ids)
    for rule in rule_set.requirements:
        if rule.operator not in SUPPORTED_OPERATORS:
            warnings.append(f"unsupported operator: {rule.operator}")
        unknown = set(rule.course_ids) - known_courses
        if unknown:
            errors.append(f"rule {rule.rule_id} references unknown courses: {sorted(unknown)}")
        if rule.operator == "CHOOSE_N" and (
            rule.choose_n is None or rule.choose_n > len(rule.course_ids)
        ):
            errors.append(f"rule {rule.rule_id} has invalid choose_n")
        if rule.operator == "MINIMUM_CREDITS" and rule.minimum_credits is None:
            errors.append(f"rule {rule.rule_id} is missing minimum_credits")
    if rule_set.unsupported_statements:
        warnings.append("unsupported source statements require manual review")
    if not rule_set.source.source_evidence.strip():
        errors.append("missing source evidence")
    if errors:
        return RuleValidationResult(RuleValidationState.INVALID, tuple(errors), tuple(warnings))
    if warnings or rule_set.lifecycle in {RuleLifecycle.DRAFT, RuleLifecycle.REQUIRES_REVIEW}:
        return RuleValidationResult(RuleValidationState.REQUIRES_REVIEW, (), tuple(warnings))
    return RuleValidationResult(RuleValidationState.VALID)


class ReviewedRuleService:
    """Enforce explicit lifecycle transitions without activating rules implicitly."""

    def review(self, rule_set: CatalogRuleSet, reviewer_confirmed: bool) -> CatalogRuleSet:
        result = validate_rule_set(rule_set)
        if result.state is RuleValidationState.INVALID:
            raise RuleLifecycleError("invalid rule set cannot be reviewed")
        if not reviewer_confirmed:
            raise RuleLifecycleError("explicit reviewer confirmation is required")
        return rule_set.model_copy(
            update={"lifecycle": RuleLifecycle.REVIEWED, "reviewer_confirmed": True}
        )

    def activate(self, rule_set: CatalogRuleSet) -> CatalogRuleSet:
        if rule_set.lifecycle is not RuleLifecycle.REVIEWED or not rule_set.reviewer_confirmed:
            raise RuleLifecycleError("only explicitly reviewed rules can be activated")
        return rule_set.model_copy(update={"lifecycle": RuleLifecycle.ACTIVE})

    def retire(self, rule_set: CatalogRuleSet) -> CatalogRuleSet:
        if rule_set.lifecycle not in {RuleLifecycle.ACTIVE, RuleLifecycle.SUPERSEDED}:
            raise RuleLifecycleError("only active or superseded rules can be retired")
        return rule_set.model_copy(update={"lifecycle": RuleLifecycle.RETIRED})


def select_exact_rule_set(
    rule_sets: list[CatalogRuleSet],
    *,
    institution_id: str,
    program_id: str,
    catalog_year: str,
) -> CatalogRuleSet | None:
    """Select only an exact active match; never fall back to a newer year."""

    matches = [
        rule_set
        for rule_set in rule_sets
        if rule_set.lifecycle is RuleLifecycle.ACTIVE
        and rule_set.source.institution_id == institution_id
        and rule_set.source.program_id == program_id
        and rule_set.source.catalog_year == catalog_year
    ]
    if len(matches) > 1:
        raise RuleLifecycleError("conflicting active rule sets for exact catalog identity")
    return matches[0] if matches else None


__all__ = [
    "RuleLifecycleError",
    "RuleValidationResult",
    "ReviewedRuleService",
    "select_exact_rule_set",
    "validate_rule_set",
]
