from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.services.reviewed_rules.contracts import CatalogRuleSet, RuleLifecycle, RuleSource
from app.services.reviewed_rules.engine import (
    ReviewedRuleService,
    RuleLifecycleError,
    select_exact_rule_set,
    validate_rule_set,
)


def rule_set(**overrides: object) -> CatalogRuleSet:
    source = RuleSource(
        institution_id="synthetic-institution",
        program_id="synthetic-program",
        program_name="Synthetic Program",
        catalog_year="2026",
        source_type="MOCK",
        source_title="Synthetic fixture",
        source_url_or_document_id="fixture:synthetic-program-2026",
        source_location="fixture:requirements",
        source_evidence="Synthetic test evidence; not university policy.",
        imported_at=datetime.now(UTC),
    )
    return CatalogRuleSet(rule_set_id=uuid4(), version=1, source=source, **overrides)


def test_draft_requires_review_and_cannot_activate() -> None:
    draft = rule_set()
    assert validate_rule_set(draft).state.value == "REQUIRES_REVIEW"
    with pytest.raises(RuleLifecycleError):
        ReviewedRuleService().activate(draft)


def test_review_and_activation_are_explicit() -> None:
    service = ReviewedRuleService()
    reviewed = service.review(rule_set(), reviewer_confirmed=True)
    assert reviewed.lifecycle is RuleLifecycle.REVIEWED
    assert service.activate(reviewed).lifecycle is RuleLifecycle.ACTIVE


def test_unknown_course_and_choose_n_are_invalid() -> None:
    bad = rule_set(
        requirements=[
            {
                "rule_id": "r1",
                "name": "bad",
                "operator": "CHOOSE_N",
                "course_ids": ["missing"],
                "choose_n": 2,
            }
        ]
    )
    result = validate_rule_set(bad)
    assert result.state.value == "INVALID"
    assert any("unknown courses" in error for error in result.errors)


def test_unsupported_statement_remains_review_warning() -> None:
    draft = rule_set(
        unsupported_statements=[
            {
                "statement_id": "u1",
                "text": "or equivalent",
                "source_location": "p. 3",
                "reason": "equivalency not modeled",
            }
        ]
    )
    result = validate_rule_set(draft)
    assert result.state.value == "REQUIRES_REVIEW"
    assert result.warnings


def test_selection_requires_exact_active_catalog_year() -> None:
    service = ReviewedRuleService()
    active = service.activate(service.review(rule_set(), reviewer_confirmed=True))
    assert (
        select_exact_rule_set(
            [active],
            institution_id="synthetic-institution",
            program_id="synthetic-program",
            catalog_year="2025",
        )
        is None
    )
    assert (
        select_exact_rule_set(
            [active],
            institution_id="synthetic-institution",
            program_id="synthetic-program",
            catalog_year="2026",
        )
        is active
    )
