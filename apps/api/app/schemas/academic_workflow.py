"""Student-scoped, source-bearing inputs for the real academic workflow."""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.academic import SourceMetadataResponse


class WorkflowProgram(BaseModel):
    id: UUID
    name: str
    catalog_year: str
    relationship_type: Literal["PRIMARY_MAJOR", "SECOND_MAJOR", "MINOR", "CERTIFICATE"]
    reviewed_rule_set_id: UUID
    source: SourceMetadataResponse


class WorkflowCourse(BaseModel):
    id: UUID
    code: str
    title: str
    credits: Decimal
    source: SourceMetadataResponse


class WorkflowTerm(BaseModel):
    id: UUID
    code: str
    starts_on: date
    ends_on: date
    source: SourceMetadataResponse


class WorkflowIssue(BaseModel):
    reason_code: str
    message: str
    evidence_reference: str | None = None


class AcademicWorkflowResponse(BaseModel):
    student_profile_id: UUID
    revision: str
    programs: list[WorkflowProgram] = Field(default_factory=list)
    courses: list[WorkflowCourse] = Field(default_factory=list)
    terms: list[WorkflowTerm] = Field(default_factory=list)
    section_ids: list[UUID] = Field(default_factory=list)
    issues: list[WorkflowIssue] = Field(default_factory=list)
