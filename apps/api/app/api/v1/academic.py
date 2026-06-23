from collections import defaultdict
from datetime import datetime
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.academic import (
    AcademicProgram,
    AcademicTerm,
    Campus,
    Course,
    CourseOfferingPattern,
    CourseRule,
    CourseRuleExpression,
    Institution,
    ProgramVersion,
    RequirementCourseOption,
    RequirementNode,
    Section,
    SectionMeeting,
    SectionModality,
    SectionStatus,
    SourceType,
    StudentAcademicProgram,
    StudentCourseAttempt,
    StudentProfile,
)
from app.schemas.academic import (
    AcademicProgramResponse,
    CampusResponse,
    CourseOfferingPatternResponse,
    CourseResponse,
    CourseRuleExpressionNodeResponse,
    CourseRuleExpressionTreeResponse,
    CourseRuleResponse,
    ErrorResponse,
    InstitutionResponse,
    ProgramVersionDetailResponse,
    ProgramVersionSummaryResponse,
    RequirementCourseOptionResponse,
    RequirementNodeResponse,
    RequirementTreeResponse,
    SectionMeetingResponse,
    SectionResponse,
    SourceMetadataResponse,
    StudentAcademicProgramResponse,
    StudentCourseAttemptResponse,
    StudentProfileResponse,
)

router = APIRouter(prefix="/api/v1", tags=["academic"])
not_found_response = {"model": ErrorResponse}
DatabaseSession = Annotated[Session, Depends(get_db)]


class SourceRecord(Protocol):
    source_type: SourceType
    is_official: bool
    source_reference: str | None
    source_retrieved_at: datetime | None
    source_confidence: str | None


def source_response(record: SourceRecord) -> SourceMetadataResponse:
    return SourceMetadataResponse(
        source_type=record.source_type.value,
        is_official=record.is_official,
        source_reference=record.source_reference,
        source_retrieved_at=record.source_retrieved_at,
        source_confidence=record.source_confidence,
    )


def not_found(resource: str, resource_id: UUID) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "code": "not_found",
            "message": f"{resource} {resource_id} was not found.",
        },
    )


def institution_response(institution: Institution) -> InstitutionResponse:
    return InstitutionResponse(
        id=institution.id,
        code=institution.code,
        name=institution.name,
        country=institution.country,
        timezone=institution.timezone,
        source=source_response(institution),
    )


def campus_response(campus: Campus) -> CampusResponse:
    return CampusResponse(
        id=campus.id,
        institution_id=campus.institution_id,
        code=campus.code,
        name=campus.name,
        location=campus.location,
        source=source_response(campus),
    )


def academic_program_response(program: AcademicProgram) -> AcademicProgramResponse:
    return AcademicProgramResponse(
        id=program.id,
        institution_id=program.institution_id,
        code=program.code,
        name=program.name,
        program_type=program.program_type.value,
        degree_level=program.degree_level.value,
        source=source_response(program),
    )


def course_response(course: Course) -> CourseResponse:
    return CourseResponse(
        id=course.id,
        institution_id=course.institution_id,
        subject_code=course.subject_code,
        course_number=course.course_number,
        title=course.title,
        description=course.description,
        credits_min=course.credits_min,
        credits_max=course.credits_max,
        course_level=course.course_level,
        repeatable=course.repeatable,
        source=source_response(course),
    )


def section_response(section: Section) -> SectionResponse:
    return SectionResponse(
        id=section.id,
        institution_id=section.institution_id,
        course_id=section.course_id,
        term_id=section.term_id,
        campus_id=section.campus_id,
        section_code=section.section_code,
        external_reference=section.external_reference,
        title_override=section.title_override,
        credits=section.credits,
        status=section.status.value,
        modality=section.modality.value,
        capacity=section.capacity,
        available_seats=section.available_seats,
        waitlist_capacity=section.waitlist_capacity,
        waitlist_available=section.waitlist_available,
        instructor_display=section.instructor_display,
        last_synced_at=section.last_synced_at,
        source=source_response(section),
    )


def section_meeting_response(meeting: SectionMeeting) -> SectionMeetingResponse:
    return SectionMeetingResponse(
        id=meeting.id,
        section_id=meeting.section_id,
        meeting_type=meeting.meeting_type.value,
        day_of_week=meeting.day_of_week.value if meeting.day_of_week else None,
        start_time=meeting.start_time.isoformat(timespec="minutes") if meeting.start_time else None,
        end_time=meeting.end_time.isoformat(timespec="minutes") if meeting.end_time else None,
        start_date=meeting.start_date,
        end_date=meeting.end_date,
        building=meeting.building,
        room=meeting.room,
        timezone=meeting.timezone,
        is_arranged=meeting.is_arranged,
        is_online=meeting.is_online,
        display_order=meeting.display_order,
        source=source_response(meeting),
    )


def course_rule_response(rule: CourseRule) -> CourseRuleResponse:
    return CourseRuleResponse(
        id=rule.id,
        institution_id=rule.institution_id,
        course_id=rule.course_id,
        section_id=rule.section_id,
        rule_type=rule.rule_type.value,
        name=rule.name,
        description=rule.description,
        effective_term_id=rule.effective_term_id,
        expiration_term_id=rule.expiration_term_id,
        requires_manual_confirmation=rule.requires_manual_confirmation,
        source=source_response(rule),
    )


def offering_pattern_response(pattern: CourseOfferingPattern) -> CourseOfferingPatternResponse:
    return CourseOfferingPatternResponse(
        id=pattern.id,
        institution_id=pattern.institution_id,
        course_id=pattern.course_id,
        campus_id=pattern.campus_id,
        term_type=pattern.term_type.value,
        frequency_type=pattern.frequency_type.value,
        effective_term_id=pattern.effective_term_id,
        expiration_term_id=pattern.expiration_term_id,
        confidence_level=pattern.confidence_level,
        notes=pattern.notes,
        source=source_response(pattern),
    )


def expression_node_response(
    node: CourseRuleExpression,
    children_by_parent: dict[UUID, list[CourseRuleExpression]],
) -> CourseRuleExpressionNodeResponse:
    children = sorted(
        children_by_parent[node.id],
        key=lambda child: (child.display_order, child.node_type.value, str(child.id)),
    )
    return CourseRuleExpressionNodeResponse(
        id=node.id,
        parent_id=node.parent_id,
        node_type=node.node_type.value,
        display_order=node.display_order,
        referenced_course_id=node.referenced_course_id,
        minimum_grade=node.minimum_grade,
        minimum_completed_credits=node.minimum_completed_credits,
        class_standing=node.class_standing,
        referenced_program_id=node.referenced_program_id,
        referenced_campus_id=node.referenced_campus_id,
        permission_type=node.permission_type,
        text_value=node.text_value,
        children=[expression_node_response(child, children_by_parent) for child in children],
        source=source_response(node),
    )


def program_summary_response(
    version: ProgramVersion,
    program: AcademicProgram,
    campus: Campus,
) -> ProgramVersionSummaryResponse:
    return ProgramVersionSummaryResponse(
        program_version_id=version.id,
        program_id=program.id,
        program_code=program.code,
        program_name=program.name,
        program_type=program.program_type.value,
        degree_level=program.degree_level.value,
        campus_id=campus.id,
        campus_code=campus.code,
        campus_name=campus.name,
        catalog_year=version.catalog_year,
        version_label=version.version_label,
        total_credits_required=version.total_credits_required,
        source=source_response(version),
    )


def program_detail_response(
    version: ProgramVersion,
    program: AcademicProgram,
    campus: Campus,
) -> ProgramVersionDetailResponse:
    return ProgramVersionDetailResponse(
        id=version.id,
        institution_id=version.institution_id,
        catalog_year=version.catalog_year,
        version_label=version.version_label,
        total_credits_required=version.total_credits_required,
        effective_term_id=version.effective_term_id,
        program=academic_program_response(program),
        campus=campus_response(campus),
        source=source_response(version),
    )


def program_version_query() -> Select[tuple[ProgramVersion, AcademicProgram, Campus]]:
    return (
        select(ProgramVersion, AcademicProgram, Campus)
        .join(AcademicProgram, ProgramVersion.program_id == AcademicProgram.id)
        .join(Campus, ProgramVersion.campus_id == Campus.id)
    )


@router.get("/institutions", response_model=list[InstitutionResponse])
def list_institutions(db: DatabaseSession) -> list[InstitutionResponse]:
    institutions = db.scalars(select(Institution).order_by(Institution.code)).all()
    return [institution_response(institution) for institution in institutions]


@router.get("/programs", response_model=list[ProgramVersionSummaryResponse])
def list_programs(db: DatabaseSession) -> list[ProgramVersionSummaryResponse]:
    rows = db.execute(
        program_version_query().order_by(AcademicProgram.code, ProgramVersion.catalog_year)
    ).all()
    return [program_summary_response(version, program, campus) for version, program, campus in rows]


@router.get(
    "/programs/{program_version_id}",
    response_model=ProgramVersionDetailResponse,
    responses={404: not_found_response},
)
def get_program(
    program_version_id: UUID,
    db: DatabaseSession,
) -> ProgramVersionDetailResponse:
    row = db.execute(
        program_version_query().where(ProgramVersion.id == program_version_id)
    ).one_or_none()
    if row is None:
        raise not_found("ProgramVersion", program_version_id)
    version, program, campus = row
    return program_detail_response(version, program, campus)


@router.get(
    "/programs/{program_version_id}/requirements",
    response_model=RequirementTreeResponse,
    responses={404: not_found_response},
)
def get_program_requirements(
    program_version_id: UUID,
    db: DatabaseSession,
) -> RequirementTreeResponse:
    version = db.get(ProgramVersion, program_version_id)
    if version is None:
        raise not_found("ProgramVersion", program_version_id)

    nodes = db.scalars(
        select(RequirementNode)
        .where(RequirementNode.program_version_id == program_version_id)
        .order_by(RequirementNode.display_order, RequirementNode.code)
    ).all()
    option_rows = db.execute(
        select(RequirementCourseOption, Course)
        .join(Course, RequirementCourseOption.course_id == Course.id)
        .where(RequirementCourseOption.program_version_id == program_version_id)
        .order_by(RequirementCourseOption.display_order)
    ).all()
    options_by_node: dict[UUID, list[RequirementCourseOptionResponse]] = defaultdict(list)
    for option, course in option_rows:
        options_by_node[option.requirement_node_id].append(
            RequirementCourseOptionResponse(
                id=option.id,
                course_id=course.id,
                subject_code=course.subject_code,
                course_number=course.course_number,
                title=course.title,
                display_order=option.display_order,
                minimum_grade=option.minimum_grade,
                credits_override=option.credits_override,
                source=source_response(option),
            )
        )

    return RequirementTreeResponse(
        program_version_id=program_version_id,
        nodes=[
            RequirementNodeResponse(
                id=node.id,
                parent_id=node.parent_id,
                code=node.code,
                name=node.name,
                requirement_type=node.requirement_type.value,
                display_order=node.display_order,
                minimum_credits=node.minimum_credits,
                minimum_courses=node.minimum_courses,
                choose_n=node.choose_n,
                minimum_grade=node.minimum_grade,
                minimum_course_level=node.minimum_course_level,
                minimum_residency_credits=node.minimum_residency_credits,
                allows_overlap=node.allows_overlap,
                is_required=node.is_required,
                course_options=options_by_node[node.id],
                source=source_response(node),
            )
            for node in nodes
        ],
    )


@router.get("/courses", response_model=list[CourseResponse])
def list_courses(db: DatabaseSession) -> list[CourseResponse]:
    courses = db.scalars(select(Course).order_by(Course.subject_code, Course.course_number)).all()
    return [course_response(course) for course in courses]


@router.get(
    "/courses/{course_id}",
    response_model=CourseResponse,
    responses={404: not_found_response},
)
def get_course(course_id: UUID, db: DatabaseSession) -> CourseResponse:
    course = db.get(Course, course_id)
    if course is None:
        raise not_found("Course", course_id)
    return course_response(course)


def section_rows(
    db: Session,
    *,
    term_id: UUID | None = None,
    course_id: UUID | None = None,
    campus_id: UUID | None = None,
    status: SectionStatus | None = None,
    modality: SectionModality | None = None,
) -> list[Section]:
    stmt = select(Section)
    if term_id is not None:
        stmt = stmt.where(Section.term_id == term_id)
    if course_id is not None:
        stmt = stmt.where(Section.course_id == course_id)
    if campus_id is not None:
        stmt = stmt.where(Section.campus_id == campus_id)
    if status is not None:
        stmt = stmt.where(Section.status == status)
    if modality is not None:
        stmt = stmt.where(Section.modality == modality)
    return list(db.scalars(stmt.order_by(Section.section_code, Section.id)).all())


@router.get(
    "/terms/{term_id}/sections",
    response_model=list[SectionResponse],
    responses={404: not_found_response},
)
def list_term_sections(
    term_id: UUID,
    db: DatabaseSession,
    course_id: UUID | None = None,
    campus_id: UUID | None = None,
    status: Annotated[SectionStatus | None, Query()] = None,
    modality: Annotated[SectionModality | None, Query()] = None,
) -> list[SectionResponse]:
    if db.get(AcademicTerm, term_id) is None:
        raise not_found("AcademicTerm", term_id)
    return [
        section_response(section)
        for section in section_rows(
            db,
            term_id=term_id,
            course_id=course_id,
            campus_id=campus_id,
            status=status,
            modality=modality,
        )
    ]


@router.get(
    "/courses/{course_id}/sections",
    response_model=list[SectionResponse],
    responses={404: not_found_response},
)
def list_course_sections(
    course_id: UUID,
    db: DatabaseSession,
    term_id: UUID | None = None,
    campus_id: UUID | None = None,
    status: Annotated[SectionStatus | None, Query()] = None,
    modality: Annotated[SectionModality | None, Query()] = None,
) -> list[SectionResponse]:
    if db.get(Course, course_id) is None:
        raise not_found("Course", course_id)
    return [
        section_response(section)
        for section in section_rows(
            db,
            term_id=term_id,
            course_id=course_id,
            campus_id=campus_id,
            status=status,
            modality=modality,
        )
    ]


@router.get(
    "/sections/{section_id}",
    response_model=SectionResponse,
    responses={404: not_found_response},
)
def get_section(section_id: UUID, db: DatabaseSession) -> SectionResponse:
    section = db.get(Section, section_id)
    if section is None:
        raise not_found("Section", section_id)
    return section_response(section)


@router.get(
    "/sections/{section_id}/meetings",
    response_model=list[SectionMeetingResponse],
    responses={404: not_found_response},
)
def get_section_meetings(
    section_id: UUID,
    db: DatabaseSession,
) -> list[SectionMeetingResponse]:
    if db.get(Section, section_id) is None:
        raise not_found("Section", section_id)
    meetings = db.scalars(
        select(SectionMeeting)
        .where(SectionMeeting.section_id == section_id)
        .order_by(SectionMeeting.display_order, SectionMeeting.meeting_type, SectionMeeting.id)
    ).all()
    return [section_meeting_response(meeting) for meeting in meetings]


@router.get(
    "/courses/{course_id}/rules",
    response_model=list[CourseRuleResponse],
    responses={404: not_found_response},
)
def get_course_rules(course_id: UUID, db: DatabaseSession) -> list[CourseRuleResponse]:
    if db.get(Course, course_id) is None:
        raise not_found("Course", course_id)
    rules = db.scalars(
        select(CourseRule)
        .where(CourseRule.course_id == course_id, CourseRule.section_id.is_(None))
        .order_by(CourseRule.rule_type, CourseRule.name, CourseRule.id)
    ).all()
    return [course_rule_response(rule) for rule in rules]


@router.get(
    "/sections/{section_id}/rules",
    response_model=list[CourseRuleResponse],
    responses={404: not_found_response},
)
def get_section_rules(section_id: UUID, db: DatabaseSession) -> list[CourseRuleResponse]:
    if db.get(Section, section_id) is None:
        raise not_found("Section", section_id)
    rules = db.scalars(
        select(CourseRule)
        .where(CourseRule.section_id == section_id)
        .order_by(CourseRule.rule_type, CourseRule.name, CourseRule.id)
    ).all()
    return [course_rule_response(rule) for rule in rules]


@router.get(
    "/rules/{rule_id}",
    response_model=CourseRuleResponse,
    responses={404: not_found_response},
)
def get_rule(rule_id: UUID, db: DatabaseSession) -> CourseRuleResponse:
    rule = db.get(CourseRule, rule_id)
    if rule is None:
        raise not_found("CourseRule", rule_id)
    return course_rule_response(rule)


@router.get(
    "/rules/{rule_id}/expression",
    response_model=CourseRuleExpressionTreeResponse,
    responses={404: not_found_response},
)
def get_rule_expression(
    rule_id: UUID,
    db: DatabaseSession,
) -> CourseRuleExpressionTreeResponse:
    if db.get(CourseRule, rule_id) is None:
        raise not_found("CourseRule", rule_id)
    nodes = db.scalars(
        select(CourseRuleExpression)
        .where(CourseRuleExpression.course_rule_id == rule_id)
        .order_by(CourseRuleExpression.display_order, CourseRuleExpression.node_type)
    ).all()
    children_by_parent: dict[UUID, list[CourseRuleExpression]] = defaultdict(list)
    root: CourseRuleExpression | None = None
    for node in nodes:
        if node.parent_id is None:
            root = node
        else:
            children_by_parent[node.parent_id].append(node)
    return CourseRuleExpressionTreeResponse(
        course_rule_id=rule_id,
        root=expression_node_response(root, children_by_parent) if root else None,
    )


@router.get(
    "/courses/{course_id}/offering-patterns",
    response_model=list[CourseOfferingPatternResponse],
    responses={404: not_found_response},
)
def get_course_offering_patterns(
    course_id: UUID,
    db: DatabaseSession,
) -> list[CourseOfferingPatternResponse]:
    if db.get(Course, course_id) is None:
        raise not_found("Course", course_id)
    patterns = db.scalars(
        select(CourseOfferingPattern)
        .where(CourseOfferingPattern.course_id == course_id)
        .order_by(
            CourseOfferingPattern.term_type,
            CourseOfferingPattern.effective_term_id,
            CourseOfferingPattern.id,
        )
    ).all()
    return [offering_pattern_response(pattern) for pattern in patterns]


def student_programs_response(
    student_id: UUID,
    db: Session,
) -> list[StudentAcademicProgramResponse]:
    rows = db.execute(
        select(StudentAcademicProgram, ProgramVersion, AcademicProgram)
        .join(ProgramVersion, StudentAcademicProgram.program_version_id == ProgramVersion.id)
        .join(AcademicProgram, ProgramVersion.program_id == AcademicProgram.id)
        .where(StudentAcademicProgram.student_profile_id == student_id)
        .order_by(StudentAcademicProgram.program_type)
    ).all()
    return [
        StudentAcademicProgramResponse(
            id=student_program.id,
            program_version_id=program_version.id,
            program_code=program.code,
            program_name=program.name,
            program_type=student_program.program_type.value,
            status=student_program.status.value,
            declared_on=student_program.declared_on,
            source=source_response(student_program),
        )
        for student_program, program_version, program in rows
    ]


@router.get(
    "/students/{student_id}",
    response_model=StudentProfileResponse,
    responses={404: not_found_response},
)
def get_student(student_id: UUID, db: DatabaseSession) -> StudentProfileResponse:
    student = db.get(StudentProfile, student_id)
    if student is None:
        raise not_found("StudentProfile", student_id)
    return StudentProfileResponse(
        id=student.id,
        home_institution_id=student.home_institution_id,
        home_campus_id=student.home_campus_id,
        expected_graduation_term_id=student.expected_graduation_term_id,
        external_ref=student.external_ref,
        display_name=student.display_name,
        class_standing=student.class_standing,
        programs=student_programs_response(student.id, db),
        source=source_response(student),
    )


@router.get(
    "/students/{student_id}/course-attempts",
    response_model=list[StudentCourseAttemptResponse],
    responses={404: not_found_response},
)
def get_student_course_attempts(
    student_id: UUID,
    db: DatabaseSession,
) -> list[StudentCourseAttemptResponse]:
    if db.get(StudentProfile, student_id) is None:
        raise not_found("StudentProfile", student_id)
    rows = db.execute(
        select(StudentCourseAttempt, Course, AcademicTerm)
        .join(Course, StudentCourseAttempt.course_id == Course.id)
        .join(AcademicTerm, StudentCourseAttempt.term_id == AcademicTerm.id)
        .where(StudentCourseAttempt.student_profile_id == student_id)
        .order_by(AcademicTerm.term_code, StudentCourseAttempt.attempt_number)
    ).all()
    return [
        StudentCourseAttemptResponse(
            id=attempt.id,
            student_profile_id=attempt.student_profile_id,
            course_id=course.id,
            course_code=f"{course.subject_code} {course.course_number}",
            course_title=course.title,
            term_id=term.id,
            term_code=term.term_code,
            attempt_number=attempt.attempt_number,
            status=attempt.status.value,
            grade=attempt.grade,
            credits_attempted=attempt.credits_attempted,
            credits_earned=attempt.credits_earned,
            is_repeat=attempt.is_repeat,
            source=source_response(attempt),
        )
        for attempt, course, term in rows
    ]
