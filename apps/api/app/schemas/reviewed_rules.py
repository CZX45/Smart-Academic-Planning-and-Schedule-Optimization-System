from pydantic import BaseModel

from app.services.reviewed_rules.contracts import CatalogRuleSet


class RuleValidationResponse(BaseModel):
    rule_set_id: str
    state: str
    errors: list[str]
    warnings: list[str]
    affects_degree_audit: bool = False
    affects_eligibility: bool = False


class ReviewedRuleSetResponse(CatalogRuleSet):
    pass


class ReviewedRuleSetRecordResponse(BaseModel):
    rule_set: CatalogRuleSet
    validation_state: str
    validation_errors: list[str]
    validation_warnings: list[str]
