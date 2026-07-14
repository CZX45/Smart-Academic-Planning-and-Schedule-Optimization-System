from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RuleLifecycle(StrEnum):
    DRAFT = "DRAFT"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    REVIEWED = "REVIEWED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"
    REJECTED = "REJECTED"


class RuleValidationState(StrEnum):
    VALID = "VALID"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    INVALID = "INVALID"


class RuleSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: str = Field(min_length=1)
    program_id: str = Field(min_length=1)
    program_name: str = Field(min_length=1)
    degree: str | None = None
    major: str | None = None
    concentration: str | None = None
    catalog_year: str = Field(min_length=1)
    effective_term: str | None = None
    source_type: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_url_or_document_id: str = Field(min_length=1)
    source_location: str = Field(min_length=1)
    source_evidence: str = Field(min_length=1, max_length=2000)
    imported_at: datetime
    checksum: str | None = None


class CourseDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    course_id: str = Field(min_length=1)
    code: str = Field(min_length=1)
    title: str = Field(min_length=1)
    credits_min: Decimal = Field(gt=0)
    credits_max: Decimal = Field(gt=0)
    prerequisite_ids: list[str] = Field(default_factory=list)
    corequisite_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_credits(self) -> CourseDefinition:
        if self.credits_max < self.credits_min:
            raise ValueError("credits_max must be greater than or equal to credits_min")
        return self


class RequirementRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    operator: str = Field(min_length=1)
    course_ids: list[str] = Field(default_factory=list)
    choose_n: int | None = Field(default=None, gt=0)
    minimum_credits: Decimal | None = Field(default=None, gt=0)
    minimum_grade: str | None = None


class UnsupportedStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=2000)
    source_location: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    requires_manual_review: bool = True


class CatalogRuleSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_set_id: UUID
    version: int = Field(gt=0)
    lifecycle: RuleLifecycle = RuleLifecycle.DRAFT
    source: RuleSource
    courses: list[CourseDefinition] = Field(default_factory=list)
    requirements: list[RequirementRule] = Field(default_factory=list)
    unsupported_statements: list[UnsupportedStatement] = Field(default_factory=list)
    supersedes_rule_set_id: UUID | None = None
    reviewed_at: datetime | None = None
    reviewer_confirmed: bool = False
