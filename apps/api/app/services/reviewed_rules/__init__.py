"""Source-backed Program/Catalog rule review primitives.

This package is intentionally independent from Degree Audit and Eligibility.
Only an explicitly reviewed and activated rule set may cross that boundary in
the follow-up integration milestone.
"""

from app.services.reviewed_rules.contracts import (
    CatalogRuleSet,
    RuleLifecycle,
    RuleValidationState,
    UnsupportedStatement,
)
from app.services.reviewed_rules.engine import (
    ReviewedRuleService,
    RuleLifecycleError,
    validate_rule_set,
)

__all__ = [
    "CatalogRuleSet",
    "RuleLifecycle",
    "RuleLifecycleError",
    "RuleValidationState",
    "ReviewedRuleService",
    "UnsupportedStatement",
    "validate_rule_set",
]
