from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class SourceMetadataResponse(BaseModel):
    source_type: str
    is_official: bool
    source_reference: str | None = None
    source_retrieved_at: datetime | None = None
    source_confidence: str | None = None


class InstitutionResponse(BaseModel):
    id: UUID
    code: str
    name: str
    country: str
    timezone: str
    source: SourceMetadataResponse


class CampusResponse(BaseModel):
    id: UUID
    institution_id: UUID
    code: str
    name: str
    location: str | None = None
    source: SourceMetadataResponse


class AcademicProgramResponse(BaseModel):
    id: UUID
    institution_id: UUID
    code: str
    name: str
    program_type: str
    degree_level: str
    source: SourceMetadataResponse


class ProgramVersionSummaryResponse(BaseModel):
    program_version_id: UUID
    program_id: UUID
    program_code: str
    program_name: str
    program_type: str
    degree_level: str
    campus_id: UUID
    campus_code: str
    campus_name: str
    catalog_year: str
    version_label: str
    total_credits_required: Decimal
    source: SourceMetadataResponse


class ProgramVersionDetailResponse(BaseModel):
    id: UUID
    institution_id: UUID
    catalog_year: str
    version_label: str
    total_credits_required: Decimal
    effective_term_id: UUID
    program: AcademicProgramResponse
    campus: CampusResponse
    source: SourceMetadataResponse


class CourseResponse(BaseModel):
    id: UUID
    institution_id: UUID
    subject_code: str
    course_number: str
    title: str
    description: str | None = None
    credits_min: Decimal
    credits_max: Decimal
    course_level: int
    repeatable: bool
    source: SourceMetadataResponse


class RequirementCourseOptionResponse(BaseModel):
    id: UUID
    course_id: UUID
    subject_code: str
    course_number: str
    title: str
    display_order: int
    minimum_grade: str | None = None
    credits_override: Decimal | None = None
    source: SourceMetadataResponse


class RequirementNodeResponse(BaseModel):
    id: UUID
    parent_id: UUID | None = None
    code: str
    name: str
    requirement_type: str
    display_order: int
    minimum_credits: Decimal | None = None
    minimum_courses: int | None = None
    choose_n: int | None = None
    minimum_grade: str | None = None
    minimum_course_level: int | None = None
    minimum_residency_credits: Decimal | None = None
    allows_overlap: bool
    is_required: bool
    course_options: list[RequirementCourseOptionResponse]
    source: SourceMetadataResponse


class RequirementTreeResponse(BaseModel):
    program_version_id: UUID
    nodes: list[RequirementNodeResponse]


class StudentAcademicProgramResponse(BaseModel):
    id: UUID
    program_version_id: UUID
    program_code: str
    program_name: str
    program_type: str
    status: str
    declared_on: date | None = None
    source: SourceMetadataResponse


class StudentProfileResponse(BaseModel):
    id: UUID
    home_institution_id: UUID
    home_campus_id: UUID
    expected_graduation_term_id: UUID | None = None
    external_ref: str | None = None
    display_name: str
    class_standing: str | None = None
    programs: list[StudentAcademicProgramResponse]
    source: SourceMetadataResponse


class StudentCourseAttemptResponse(BaseModel):
    id: UUID
    student_profile_id: UUID
    course_id: UUID
    course_code: str
    course_title: str
    term_id: UUID
    term_code: str
    attempt_number: int
    status: str
    grade: str | None = None
    credits_attempted: Decimal
    credits_earned: Decimal
    is_repeat: bool
    source: SourceMetadataResponse


class CourseOfferingPatternResponse(BaseModel):
    id: UUID
    institution_id: UUID
    course_id: UUID
    campus_id: UUID
    term_type: str
    frequency_type: str
    effective_term_id: UUID
    expiration_term_id: UUID | None = None
    confidence_level: Decimal
    notes: str | None = None
    source: SourceMetadataResponse


class SectionResponse(BaseModel):
    id: UUID
    institution_id: UUID
    course_id: UUID
    term_id: UUID
    campus_id: UUID
    section_code: str
    external_reference: str | None = None
    title_override: str | None = None
    credits: Decimal | None = None
    status: str
    modality: str
    capacity: int | None = None
    available_seats: int | None = None
    waitlist_capacity: int | None = None
    waitlist_available: int | None = None
    instructor_display: str | None = None
    last_synced_at: datetime | None = None
    source: SourceMetadataResponse


class SectionMeetingResponse(BaseModel):
    id: UUID
    section_id: UUID
    meeting_type: str
    day_of_week: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    building: str | None = None
    room: str | None = None
    timezone: str
    is_arranged: bool
    is_online: bool
    display_order: int
    source: SourceMetadataResponse


class CourseRuleResponse(BaseModel):
    id: UUID
    institution_id: UUID
    course_id: UUID
    section_id: UUID | None = None
    rule_type: str
    name: str
    description: str | None = None
    effective_term_id: UUID
    expiration_term_id: UUID | None = None
    requires_manual_confirmation: bool
    source: SourceMetadataResponse


class CourseRuleExpressionNodeResponse(BaseModel):
    id: UUID
    parent_id: UUID | None = None
    node_type: str
    display_order: int
    referenced_course_id: UUID | None = None
    minimum_grade: str | None = None
    minimum_completed_credits: Decimal | None = None
    class_standing: str | None = None
    referenced_program_id: UUID | None = None
    referenced_campus_id: UUID | None = None
    permission_type: str | None = None
    text_value: str | None = None
    children: list["CourseRuleExpressionNodeResponse"] = Field(default_factory=list)
    source: SourceMetadataResponse


class CourseRuleExpressionTreeResponse(BaseModel):
    course_rule_id: UUID
    root: CourseRuleExpressionNodeResponse | None = None


class ErrorDetailResponse(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    detail: ErrorDetailResponse
