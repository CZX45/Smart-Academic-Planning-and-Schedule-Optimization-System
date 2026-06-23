from collections.abc import Generator
from datetime import date, time
from decimal import Decimal
from typing import Any, cast
from uuid import NAMESPACE_URL, UUID, uuid5

import pytest
from sqlalchemy import Table, UniqueConstraint, create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.domain.course_rules import (
    CourseRuleExpressionValidationError,
    validate_course_rule_expression_tree,
)
from app.models.academic import (
    AcademicProgram,
    AcademicTerm,
    ApprovalStatus,
    AuditApplicationType,
    AuditCourseApplication,
    AuditMode,
    AuditRunStatus,
    AuditWarningSeverity,
    Campus,
    Course,
    CourseEquivalency,
    CourseOfferingPattern,
    CourseRule,
    CourseRuleExpression,
    CourseRuleExpressionNodeType,
    CourseRuleType,
    CourseSubstitution,
    DayOfWeek,
    DegreeAuditRun,
    DegreeAuditWarning,
    DegreeLevel,
    FrequencyType,
    Institution,
    MeetingType,
    ProgramType,
    ProgramVersion,
    RequirementCourseOption,
    RequirementEvaluation,
    RequirementEvaluationStatus,
    RequirementNode,
    RequirementType,
    Section,
    SectionMeeting,
    SectionModality,
    SectionStatus,
    SourceType,
    StudentAcademicProgram,
    StudentAcademicProgramStatus,
    StudentCourseAttempt,
    StudentCourseAttemptStatus,
    StudentProfile,
    StudentProgramType,
    TermType,
    TransferCredit,
)


def uid(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"sapsos-test:{name}")


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    with testing_session() as db:
        yield db


def institution(name: str = "one") -> Institution:
    return Institution(
        id=uid(f"institution-{name}"),
        code=f"INST{name.upper()}",
        name=f"Institution {name}",
        country="US",
        timezone="America/New_York",
        source_type=SourceType.MOCK,
        is_official=False,
    )


def campus(inst: Institution, name: str = "main") -> Campus:
    return Campus(
        id=uid(f"campus-{inst.code}-{name}"),
        institution_id=inst.id,
        code=name.upper(),
        name=f"{name.title()} Campus",
        source_type=SourceType.MOCK,
        is_official=False,
    )


def term(inst: Institution, campus_record: Campus, code: str = "2024FA") -> AcademicTerm:
    return AcademicTerm(
        id=uid(f"term-{inst.code}-{campus_record.code}-{code}"),
        institution_id=inst.id,
        campus_id=campus_record.id,
        term_code=code,
        name="Fall 2024",
        starts_on=date(2024, 9, 1),
        ends_on=date(2024, 12, 15),
        source_type=SourceType.MOCK,
        is_official=False,
    )


def course(inst: Institution, subject: str, number: str, credits: str = "3.0") -> Course:
    return Course(
        id=uid(f"course-{inst.code}-{subject}-{number}"),
        institution_id=inst.id,
        subject_code=subject,
        course_number=number,
        title=f"{subject} {number}",
        credits_min=Decimal(credits),
        credits_max=Decimal(credits),
        course_level=100,
        source_type=SourceType.MOCK,
        is_official=False,
    )


def program(inst: Institution, code: str = "BSFIN") -> AcademicProgram:
    return AcademicProgram(
        id=uid(f"program-{inst.code}-{code}"),
        institution_id=inst.id,
        code=code,
        name="BS Finance",
        program_type=ProgramType.MAJOR,
        degree_level=DegreeLevel.BACHELORS,
        source_type=SourceType.MOCK,
        is_official=False,
    )


def program_version(
    inst: Institution,
    campus_record: Campus,
    term_record: AcademicTerm,
    program_record: AcademicProgram,
    label: str = "2024",
) -> ProgramVersion:
    return ProgramVersion(
        id=uid(f"program-version-{program_record.code}-{campus_record.code}-{label}"),
        institution_id=inst.id,
        program_id=program_record.id,
        campus_id=campus_record.id,
        effective_term_id=term_record.id,
        catalog_year=label,
        version_label=f"{label} Catalog",
        total_credits_required=Decimal("120.0"),
        source_type=SourceType.MOCK,
        is_official=False,
    )


def seed_catalog(
    session: Session,
) -> tuple[Institution, Campus, AcademicTerm, AcademicProgram, ProgramVersion]:
    inst = institution()
    session.add(inst)
    session.commit()
    campus_record = campus(inst)
    session.add(campus_record)
    session.commit()
    term_record = term(inst, campus_record)
    session.add(term_record)
    session.commit()
    program_record = program(inst)
    session.add(program_record)
    session.commit()
    version = program_version(inst, campus_record, term_record, program_record)
    session.add(version)
    session.commit()
    return inst, campus_record, term_record, program_record, version


def section(
    inst: Institution,
    campus_record: Campus,
    term_record: AcademicTerm,
    course_record: Course,
    code: str = "001",
    *,
    status: SectionStatus = SectionStatus.OPEN,
    modality: SectionModality = SectionModality.IN_PERSON,
) -> Section:
    return Section(
        id=uid(
            f"section-{inst.code}-{term_record.term_code}-{course_record.subject_code}-{course_record.course_number}-{code}"
        ),
        institution_id=inst.id,
        course_id=course_record.id,
        term_id=term_record.id,
        campus_id=campus_record.id,
        section_code=code,
        external_reference=f"MOCK-{code}",
        credits=course_record.credits_min,
        status=status,
        modality=modality,
        capacity=30,
        available_seats=5,
        waitlist_capacity=10,
        waitlist_available=10,
        instructor_display="Mock Instructor",
        source_type=SourceType.MOCK,
        is_official=False,
    )


def offering_pattern(
    inst: Institution,
    campus_record: Campus,
    course_record: Course,
    effective_term: AcademicTerm,
    expiration_term: AcademicTerm,
    *,
    term_type: TermType = TermType.FALL,
) -> CourseOfferingPattern:
    return CourseOfferingPattern(
        id=uid(
            f"offering-pattern-{course_record.subject_code}-{course_record.course_number}-{term_type.value}"
        ),
        institution_id=inst.id,
        course_id=course_record.id,
        campus_id=campus_record.id,
        term_type=term_type,
        frequency_type=FrequencyType.ANNUAL,
        effective_term_id=effective_term.id,
        expiration_term_id=expiration_term.id,
        confidence_level=Decimal("0.75"),
        source_type=SourceType.MOCK,
        is_official=False,
    )


def course_rule(
    inst: Institution,
    course_record: Course,
    effective_term: AcademicTerm,
    *,
    section_record: Section | None = None,
    rule_type: CourseRuleType = CourseRuleType.PREREQUISITE,
    name: str = "Mock prerequisite",
) -> CourseRule:
    return CourseRule(
        id=uid(f"course-rule-{name}-{course_record.subject_code}-{course_record.course_number}"),
        institution_id=inst.id,
        course_id=course_record.id,
        section_id=section_record.id if section_record else None,
        rule_type=rule_type,
        name=name,
        description=f"{name} stored as a mock rule.",
        effective_term_id=effective_term.id,
        source_type=SourceType.MOCK,
        is_official=False,
        requires_manual_confirmation=False,
    )


def expression_node(
    rule_record: CourseRule,
    name: str,
    node_type: CourseRuleExpressionNodeType,
    *,
    parent_id: UUID | None = None,
    display_order: int = 0,
    referenced_course_id: UUID | None = None,
    minimum_grade: str | None = None,
    minimum_completed_credits: Decimal | None = None,
    class_standing: str | None = None,
    referenced_program_id: UUID | None = None,
    referenced_campus_id: UUID | None = None,
    permission_type: str | None = None,
    text_value: str | None = None,
) -> CourseRuleExpression:
    return CourseRuleExpression(
        id=uid(f"course-rule-expression-{name}"),
        institution_id=rule_record.institution_id,
        course_rule_id=rule_record.id,
        parent_id=parent_id,
        node_type=node_type,
        display_order=display_order,
        referenced_course_id=referenced_course_id,
        minimum_grade=minimum_grade,
        minimum_completed_credits=minimum_completed_credits,
        class_standing=class_standing,
        referenced_program_id=referenced_program_id,
        referenced_campus_id=referenced_campus_id,
        permission_type=permission_type,
        text_value=text_value,
        source_type=SourceType.MOCK,
        is_official=False,
    )


def test_institution_code_is_unique(session: Session) -> None:
    session.add_all([institution("one"), institution("two")])
    session.flush()
    duplicate = institution("three")
    duplicate.code = "INSTONE"
    session.add(duplicate)

    with pytest.raises(IntegrityError):
        session.commit()


def test_campus_code_is_unique_within_institution(session: Session) -> None:
    inst = institution()
    first = campus(inst, "main")
    duplicate = campus(inst, "other")
    duplicate.code = first.code
    session.add_all([inst, first, duplicate])

    with pytest.raises(IntegrityError):
        session.commit()


def test_course_code_is_unique_within_institution(session: Session) -> None:
    inst = institution()
    first = course(inst, "FIN", "301")
    duplicate = course(inst, "FIN", "301")
    duplicate.id = uid("course-duplicate")
    session.add_all([inst, first, duplicate])

    with pytest.raises(IntegrityError):
        session.commit()


def test_course_credit_range_is_valid(session: Session) -> None:
    inst = institution()
    invalid = course(inst, "FIN", "301")
    invalid.credits_min = Decimal("4.0")
    invalid.credits_max = Decimal("3.0")
    session.add_all([inst, invalid])

    with pytest.raises(IntegrityError):
        session.commit()


def test_course_offering_pattern_rejects_duplicate_range_and_mock_official(
    session: Session,
) -> None:
    inst, campus_record, fall_term, _, _ = seed_catalog(session)
    spring_term = term(inst, campus_record, "2025SP")
    fin_300 = course(inst, "FIN", "300")
    session.add_all([spring_term, fin_300])
    session.commit()

    first = offering_pattern(inst, campus_record, fin_300, fall_term, spring_term)
    duplicate = offering_pattern(inst, campus_record, fin_300, fall_term, spring_term)
    duplicate.id = uid("offering-pattern-duplicate")
    session.add_all([first, duplicate])

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    official_mock = offering_pattern(
        inst,
        campus_record,
        fin_300,
        fall_term,
        spring_term,
        term_type=TermType.SPRING,
    )
    official_mock.id = uid("offering-pattern-official-mock")
    official_mock.is_official = True
    session.add(official_mock)

    with pytest.raises(IntegrityError):
        session.commit()


def test_program_version_combination_is_unique(session: Session) -> None:
    inst, campus_record, term_record, program_record, version = seed_catalog(session)
    version_id = version.id
    duplicate = program_version(inst, campus_record, term_record, program_record)
    duplicate.id = uid("program-version-duplicate")
    session.add(duplicate)

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    assert session.get(ProgramVersion, version_id) is not None


def test_section_constraints_and_modalities(session: Session) -> None:
    inst, campus_record, term_record, _, _ = seed_catalog(session)
    fin_300 = course(inst, "FIN", "300")
    session.add(fin_300)
    session.commit()

    in_person = section(inst, campus_record, term_record, fin_300, "001")
    online = section(
        inst,
        campus_record,
        term_record,
        fin_300,
        "WEB",
        modality=SectionModality.ONLINE_ASYNCHRONOUS,
        status=SectionStatus.PLANNED,
    )
    cancelled = section(
        inst,
        campus_record,
        term_record,
        fin_300,
        "099",
        status=SectionStatus.CANCELLED,
    )
    session.add_all([in_person, online, cancelled])
    session.commit()

    assert {record.modality for record in session.scalars(select(Section)).all()} == {
        SectionModality.IN_PERSON,
        SectionModality.ONLINE_ASYNCHRONOUS,
    }
    assert session.get(Section, cancelled.id) is not None

    duplicate = section(inst, campus_record, term_record, fin_300, "001")
    duplicate.id = uid("section-duplicate")
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    invalid_capacity = section(inst, campus_record, term_record, fin_300, "002")
    invalid_capacity.capacity = -1
    session.add(invalid_capacity)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    invalid_seats = section(inst, campus_record, term_record, fin_300, "003")
    invalid_seats.capacity = 5
    invalid_seats.available_seats = 6
    session.add(invalid_seats)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    other_inst = institution("other")
    other_campus = campus(other_inst, "main")
    cross_campus = section(inst, other_campus, term_record, fin_300, "004")
    session.add(other_inst)
    session.commit()
    session.add(other_campus)
    session.commit()
    session.add(cross_campus)
    with pytest.raises(IntegrityError):
        session.commit()


def test_section_meeting_time_date_and_multiple_meetings(session: Session) -> None:
    inst, campus_record, term_record, _, _ = seed_catalog(session)
    fin_300 = course(inst, "FIN", "300")
    fin_section = section(inst, campus_record, term_record, fin_300)
    session.add(fin_300)
    session.commit()
    session.add(fin_section)
    session.commit()

    lecture = SectionMeeting(
        id=uid("meeting-lecture"),
        section_id=fin_section.id,
        meeting_type=MeetingType.LECTURE,
        day_of_week=DayOfWeek.MONDAY,
        start_time=time(9, 0),
        end_time=time(10, 15),
        start_date=term_record.starts_on,
        end_date=term_record.ends_on,
        building="Mock Building",
        room="101",
        timezone="America/New_York",
        display_order=10,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    lab = SectionMeeting(
        id=uid("meeting-lab"),
        section_id=fin_section.id,
        meeting_type=MeetingType.LAB,
        day_of_week=DayOfWeek.WEDNESDAY,
        start_time=time(14, 0),
        end_time=time(15, 50),
        start_date=term_record.starts_on,
        end_date=term_record.ends_on,
        building="Mock Lab Building",
        room="201",
        timezone="America/New_York",
        display_order=20,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    async_meeting = SectionMeeting(
        id=uid("meeting-online-async"),
        section_id=fin_section.id,
        meeting_type=MeetingType.OTHER,
        timezone="America/New_York",
        is_online=True,
        display_order=30,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    session.add_all([lecture, lab, async_meeting])
    session.commit()

    meetings = session.scalars(
        select(SectionMeeting).where(SectionMeeting.section_id == fin_section.id)
    ).all()
    assert [meeting.meeting_type for meeting in meetings] == [
        MeetingType.LECTURE,
        MeetingType.LAB,
        MeetingType.OTHER,
    ]

    invalid_time = SectionMeeting(
        id=uid("meeting-invalid-time"),
        section_id=fin_section.id,
        meeting_type=MeetingType.LECTURE,
        day_of_week=DayOfWeek.TUESDAY,
        start_time=time(11, 0),
        end_time=time(10, 0),
        timezone="America/New_York",
        source_type=SourceType.MOCK,
        is_official=False,
    )
    session.add(invalid_time)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    invalid_date = SectionMeeting(
        id=uid("meeting-invalid-date"),
        section_id=fin_section.id,
        meeting_type=MeetingType.EXAM,
        day_of_week=DayOfWeek.FRIDAY,
        start_time=time(8, 0),
        end_time=time(9, 0),
        start_date=term_record.ends_on,
        end_date=term_record.starts_on,
        timezone="America/New_York",
        source_type=SourceType.MOCK,
        is_official=False,
    )
    session.add(invalid_date)
    with pytest.raises(IntegrityError):
        session.commit()


def test_requirement_parent_must_belong_to_same_program_version(session: Session) -> None:
    inst, campus_record, term_record, program_record, first_version = seed_catalog(session)
    second_program = program(inst, "BSACC")
    second_version = program_version(inst, campus_record, term_record, second_program, "2025")
    session.add(second_program)
    session.commit()
    session.add(second_version)
    session.commit()
    parent = RequirementNode(
        id=uid("requirement-parent"),
        institution_id=inst.id,
        program_version_id=first_version.id,
        code="ROOT",
        name="Root",
        requirement_type=RequirementType.GROUP,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    session.add(parent)
    session.commit()
    child = RequirementNode(
        id=uid("requirement-child"),
        institution_id=inst.id,
        program_version_id=second_version.id,
        parent_id=parent.id,
        code="BAD",
        name="Bad Child",
        requirement_type=RequirementType.REQUIRED_COURSE,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    session.add(child)

    with pytest.raises(IntegrityError):
        session.commit()


def test_requirement_parent_target_has_table_unique_constraint() -> None:
    table = cast(Table, RequirementNode.__table__)
    unique_constraints = [
        constraint for constraint in table.constraints if isinstance(constraint, UniqueConstraint)
    ]

    assert any(
        {column.name for column in constraint.columns}
        == {"id", "program_version_id", "institution_id"}
        for constraint in unique_constraints
    )


def test_requirement_cannot_be_its_own_parent(session: Session) -> None:
    inst, _, _, _, version = seed_catalog(session)
    node_id = uid("requirement-self-parent")
    node = RequirementNode(
        id=node_id,
        institution_id=inst.id,
        program_version_id=version.id,
        parent_id=node_id,
        code="SELF",
        name="Self Parent",
        requirement_type=RequirementType.GROUP,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    session.add(node)

    with pytest.raises(IntegrityError):
        session.commit()


def test_requirement_course_option_cannot_repeat_or_cross_institution(session: Session) -> None:
    inst, _, _, _, version = seed_catalog(session)
    fin_301 = course(inst, "FIN", "301")
    node = RequirementNode(
        id=uid("requirement-required-course"),
        institution_id=inst.id,
        program_version_id=version.id,
        code="FIN-REQ",
        name="Finance Required",
        requirement_type=RequirementType.REQUIRED_COURSE,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    first_option = RequirementCourseOption(
        id=uid("course-option-first"),
        institution_id=inst.id,
        program_version_id=version.id,
        requirement_node_id=node.id,
        course_id=fin_301.id,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    duplicate_option = RequirementCourseOption(
        id=uid("course-option-duplicate"),
        institution_id=inst.id,
        program_version_id=version.id,
        requirement_node_id=node.id,
        course_id=fin_301.id,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    session.add_all([fin_301, node])
    session.commit()
    session.add_all([first_option, duplicate_option])

    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    other_inst = institution("other")
    other_course = course(other_inst, "FIN", "301")
    cross_option = RequirementCourseOption(
        id=uid("course-option-cross"),
        institution_id=inst.id,
        program_version_id=version.id,
        requirement_node_id=node.id,
        course_id=other_course.id,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    session.add(other_inst)
    session.commit()
    session.add(other_course)
    session.commit()
    session.add(cross_option)

    with pytest.raises(IntegrityError):
        session.commit()


def test_course_rule_course_and_section_scopes(session: Session) -> None:
    inst, campus_record, term_record, _, _ = seed_catalog(session)
    fin_300 = course(inst, "FIN", "300")
    fin_400 = course(inst, "FIN", "400")
    fin_section = section(inst, campus_record, term_record, fin_300)
    session.add_all([fin_300, fin_400])
    session.commit()
    session.add(fin_section)
    session.commit()

    course_level_rule = course_rule(inst, fin_300, term_record)
    section_level_rule = course_rule(
        inst,
        fin_300,
        term_record,
        section_record=fin_section,
        rule_type=CourseRuleType.PERMISSION,
        name="Mock section permission",
    )
    session.add_all([course_level_rule, section_level_rule])
    session.commit()

    assert course_level_rule.rule_type is CourseRuleType.PREREQUISITE
    assert section_level_rule.section_id == fin_section.id

    no_scope = CourseRule(
        id=uid("course-rule-no-scope"),
        institution_id=inst.id,
        course_id=None,
        section_id=None,
        rule_type=CourseRuleType.PERMISSION,
        name="No scope",
        effective_term_id=term_record.id,
        source_type=SourceType.MOCK,
        is_official=False,
        requires_manual_confirmation=True,
    )
    session.add(no_scope)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    cross_course = course_rule(
        inst,
        fin_400,
        term_record,
        section_record=fin_section,
        rule_type=CourseRuleType.PERMISSION,
        name="Wrong section course",
    )
    session.add(cross_course)
    with pytest.raises(IntegrityError):
        session.commit()


def test_course_rule_expression_database_constraints(session: Session) -> None:
    inst, campus_record, term_record, program_record, _ = seed_catalog(session)
    fin_200 = course(inst, "FIN", "200")
    fin_300 = course(inst, "FIN", "300")
    rule = course_rule(inst, fin_300, term_record)
    session.add_all([fin_200, fin_300])
    session.commit()
    session.add(rule)
    session.commit()

    root = expression_node(rule, "root", CourseRuleExpressionNodeType.AND)
    session.add(root)
    session.commit()

    duplicate_root = expression_node(rule, "duplicate-root", CourseRuleExpressionNodeType.OR)
    session.add(duplicate_root)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    bad_completed_leaf = expression_node(
        rule,
        "completed-without-course",
        CourseRuleExpressionNodeType.COMPLETED_COURSE,
        parent_id=root.id,
    )
    session.add(bad_completed_leaf)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    bad_grade_leaf = expression_node(
        rule,
        "minimum-grade-without-grade",
        CourseRuleExpressionNodeType.MINIMUM_GRADE,
        parent_id=root.id,
        referenced_course_id=fin_200.id,
    )
    session.add(bad_grade_leaf)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    bad_credits_leaf = expression_node(
        rule,
        "negative-credits",
        CourseRuleExpressionNodeType.MINIMUM_COMPLETED_CREDITS,
        parent_id=root.id,
        minimum_completed_credits=Decimal("-1.0"),
    )
    session.add(bad_credits_leaf)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    bad_self_parent = expression_node(
        rule,
        "self-parent",
        CourseRuleExpressionNodeType.CLASS_STANDING,
        class_standing="JUNIOR",
    )
    bad_self_parent.parent_id = bad_self_parent.id
    session.add(bad_self_parent)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    other_rule = course_rule(
        inst,
        fin_300,
        term_record,
        rule_type=CourseRuleType.PERMISSION,
        name="Other rule",
    )
    session.add(other_rule)
    session.commit()
    wrong_rule_parent = expression_node(
        other_rule,
        "wrong-rule-parent",
        CourseRuleExpressionNodeType.PERMISSION_REQUIRED,
        parent_id=root.id,
        permission_type="DEPARTMENT_APPROVAL",
    )
    session.add(wrong_rule_parent)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    other_inst = institution("other")
    other_program = program(other_inst, "OTHER")
    cross_program = expression_node(
        rule,
        "cross-program",
        CourseRuleExpressionNodeType.MAJOR_RESTRICTION,
        parent_id=root.id,
        referenced_program_id=other_program.id,
    )
    session.add(other_inst)
    session.commit()
    session.add(other_program)
    session.commit()
    session.add(cross_program)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    assert program_record.id is not None


def test_course_rule_expression_tree_validator() -> None:
    rule_id = uid("validator-rule")
    root_id = uid("validator-root")
    first_child_id = uid("validator-child-one")
    second_child_id = uid("validator-child-two")
    root = CourseRuleExpression(
        id=root_id,
        institution_id=uid("validator-inst"),
        course_rule_id=rule_id,
        node_type=CourseRuleExpressionNodeType.AND,
        display_order=0,
    )
    first_child = CourseRuleExpression(
        id=first_child_id,
        institution_id=root.institution_id,
        course_rule_id=rule_id,
        parent_id=root_id,
        node_type=CourseRuleExpressionNodeType.COMPLETED_COURSE,
        display_order=10,
        referenced_course_id=uid("validator-course-one"),
    )
    second_child = CourseRuleExpression(
        id=second_child_id,
        institution_id=root.institution_id,
        course_rule_id=rule_id,
        parent_id=root_id,
        node_type=CourseRuleExpressionNodeType.MINIMUM_GRADE,
        display_order=20,
        referenced_course_id=uid("validator-course-two"),
        minimum_grade="C",
    )

    validate_course_rule_expression_tree([root, second_child, first_child])

    not_root = CourseRuleExpression(
        id=uid("validator-not-root"),
        institution_id=root.institution_id,
        course_rule_id=rule_id,
        node_type=CourseRuleExpressionNodeType.NOT,
        display_order=0,
    )
    not_child_one = CourseRuleExpression(
        id=uid("validator-not-child-one"),
        institution_id=root.institution_id,
        course_rule_id=rule_id,
        parent_id=not_root.id,
        node_type=CourseRuleExpressionNodeType.CAMPUS_RESTRICTION,
        display_order=10,
        referenced_campus_id=uid("validator-campus-one"),
    )
    not_child_two = CourseRuleExpression(
        id=uid("validator-not-child-two"),
        institution_id=root.institution_id,
        course_rule_id=rule_id,
        parent_id=not_root.id,
        node_type=CourseRuleExpressionNodeType.CAMPUS_RESTRICTION,
        display_order=20,
        referenced_campus_id=uid("validator-campus-two"),
    )

    with pytest.raises(CourseRuleExpressionValidationError):
        validate_course_rule_expression_tree([not_root, not_child_one, not_child_two])

    leaf_with_child = CourseRuleExpression(
        id=uid("validator-leaf-root"),
        institution_id=root.institution_id,
        course_rule_id=rule_id,
        node_type=CourseRuleExpressionNodeType.CLASS_STANDING,
        class_standing="JUNIOR",
    )
    invalid_child = CourseRuleExpression(
        id=uid("validator-leaf-child"),
        institution_id=root.institution_id,
        course_rule_id=rule_id,
        parent_id=leaf_with_child.id,
        node_type=CourseRuleExpressionNodeType.PERMISSION_REQUIRED,
        permission_type="DEPARTMENT_APPROVAL",
    )
    with pytest.raises(CourseRuleExpressionValidationError):
        validate_course_rule_expression_tree([leaf_with_child, invalid_child])


def test_course_equivalency_cannot_equate_course_to_itself(session: Session) -> None:
    inst = institution()
    fin_301 = course(inst, "FIN", "301")
    equivalency = CourseEquivalency(
        id=uid("self-equivalency"),
        institution_id=inst.id,
        source_course_id=fin_301.id,
        equivalent_course_id=fin_301.id,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    session.add_all([inst, fin_301, equivalency])

    with pytest.raises(IntegrityError):
        session.commit()


def test_student_can_have_only_one_active_primary_major(session: Session) -> None:
    inst, campus_record, term_record, program_record, version = seed_catalog(session)
    second_program = program(inst, "BSACC")
    second_version = program_version(inst, campus_record, term_record, second_program, "2025")
    student = StudentProfile(
        id=uid("student"),
        home_institution_id=inst.id,
        home_campus_id=campus_record.id,
        expected_graduation_term_id=term_record.id,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    first_major = StudentAcademicProgram(
        id=uid("student-program-one"),
        student_profile_id=student.id,
        program_version_id=version.id,
        program_type=StudentProgramType.PRIMARY_MAJOR,
        status=StudentAcademicProgramStatus.ACTIVE,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    second_major = StudentAcademicProgram(
        id=uid("student-program-two"),
        student_profile_id=student.id,
        program_version_id=second_version.id,
        program_type=StudentProgramType.PRIMARY_MAJOR,
        status=StudentAcademicProgramStatus.ACTIVE,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    session.add(second_program)
    session.commit()
    session.add(second_version)
    session.commit()
    session.add(student)
    session.commit()
    session.add_all([first_major, second_major])

    with pytest.raises(IntegrityError):
        session.commit()


def test_student_course_attempt_supports_retake_and_positive_attempt_number(
    session: Session,
) -> None:
    inst, campus_record, term_record, _, _ = seed_catalog(session)
    fin_301 = course(inst, "FIN", "301")
    student = StudentProfile(
        id=uid("student-retake"),
        home_institution_id=inst.id,
        home_campus_id=campus_record.id,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    session.add(fin_301)
    session.commit()
    session.add(student)
    session.commit()

    session.add_all(
        [
            StudentCourseAttempt(
                id=uid("attempt-one"),
                student_profile_id=student.id,
                course_id=fin_301.id,
                term_id=term_record.id,
                attempt_number=1,
                status=StudentCourseAttemptStatus.COMPLETED,
                grade="D",
                credits_attempted=Decimal("3.0"),
                credits_earned=Decimal("3.0"),
                source_type=SourceType.MOCK,
                is_repeat=False,
                is_official=False,
            ),
            StudentCourseAttempt(
                id=uid("attempt-two"),
                student_profile_id=student.id,
                course_id=fin_301.id,
                term_id=term_record.id,
                attempt_number=2,
                status=StudentCourseAttemptStatus.COMPLETED,
                grade="B",
                credits_attempted=Decimal("3.0"),
                credits_earned=Decimal("3.0"),
                source_type=SourceType.MOCK,
                is_repeat=True,
                is_official=False,
            ),
        ]
    )
    session.commit()

    attempts = session.scalars(select(StudentCourseAttempt)).all()
    assert [attempt.attempt_number for attempt in attempts] == [1, 2]

    invalid = StudentCourseAttempt(
        id=uid("attempt-zero"),
        student_profile_id=student.id,
        course_id=fin_301.id,
        term_id=term_record.id,
        attempt_number=0,
        status=StudentCourseAttemptStatus.COMPLETED,
        credits_attempted=Decimal("3.0"),
        credits_earned=Decimal("3.0"),
        source_type=SourceType.MOCK,
        is_official=False,
    )
    session.add(invalid)

    with pytest.raises(IntegrityError):
        session.commit()


def test_transfer_credit_statuses_are_distinct(session: Session) -> None:
    inst, campus_record, _, _, _ = seed_catalog(session)
    fin_301 = course(inst, "FIN", "301")
    student = StudentProfile(
        id=uid("student-transfer"),
        home_institution_id=inst.id,
        home_campus_id=campus_record.id,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    session.add(fin_301)
    session.commit()
    session.add(student)
    session.commit()

    for status in ApprovalStatus:
        session.add(
            TransferCredit(
                id=uid(f"transfer-{status.value}"),
                student_profile_id=student.id,
                equivalent_course_id=fin_301.id,
                source_institution_name=f"Source {status.value}",
                source_course_code=f"SRC {status.value}",
                credits_earned=Decimal("3.0"),
                status=status,
                source_type=SourceType.MOCK,
                is_official=False,
            )
        )
    session.commit()

    statuses = set(session.scalars(select(TransferCredit.status)).all())
    assert statuses == set(ApprovalStatus)


def test_course_substitution_cannot_use_same_course(session: Session) -> None:
    inst, campus_record, _, _, version = seed_catalog(session)
    student = StudentProfile(
        id=uid("student-substitution"),
        home_institution_id=inst.id,
        home_campus_id=campus_record.id,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    fin_301 = course(inst, "FIN", "301")
    substitution = CourseSubstitution(
        id=uid("substitution-same"),
        student_profile_id=student.id,
        program_version_id=version.id,
        original_course_id=fin_301.id,
        substitute_course_id=fin_301.id,
        status=ApprovalStatus.APPROVED,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    session.add(student)
    session.commit()
    session.add(fin_301)
    session.commit()
    session.add(substitution)

    with pytest.raises(IntegrityError):
        session.commit()


def test_degree_audit_snapshot_models_enforce_sources_and_unique_evaluations(
    session: Session,
) -> None:
    inst, campus_record, term_record, program_record, version = seed_catalog(session)
    student = StudentProfile(
        id=uid("student-audit"),
        home_institution_id=inst.id,
        home_campus_id=campus_record.id,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    student_program = StudentAcademicProgram(
        id=uid("student-audit-program"),
        student_profile_id=student.id,
        program_version_id=version.id,
        program_type=StudentProgramType.PRIMARY_MAJOR,
        status=StudentAcademicProgramStatus.ACTIVE,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    fin_301 = course(inst, "FIN", "301")
    attempt = StudentCourseAttempt(
        id=uid("audit-attempt"),
        student_profile_id=student.id,
        course_id=fin_301.id,
        term_id=term_record.id,
        attempt_number=1,
        status=StudentCourseAttemptStatus.COMPLETED,
        grade="B",
        credits_attempted=Decimal("3.0"),
        credits_earned=Decimal("3.0"),
        source_type=SourceType.MOCK,
        is_official=False,
    )
    requirement = RequirementNode(
        id=uid("audit-requirement"),
        institution_id=inst.id,
        program_version_id=version.id,
        code="AUDIT-REQ",
        name="Audit Requirement",
        requirement_type=RequirementType.REQUIRED_COURSE,
        source_type=SourceType.MOCK,
        is_official=False,
    )
    session.add_all([student, fin_301, requirement])
    session.commit()
    session.add(student_program)
    session.commit()
    session.add(attempt)
    session.commit()

    run = DegreeAuditRun(
        id=uid("audit-run"),
        student_profile_id=student.id,
        program_version_id=version.id,
        status=AuditRunStatus.COMPLETED,
        engine_version="phase-3a-test",
        calculation_mode=AuditMode.CURRENT,
        total_required_credits=Decimal("120.0"),
        completed_credits=Decimal("3.0"),
        in_progress_credits=Decimal("0.0"),
        planned_credits=Decimal("0.0"),
        remaining_credits=Decimal("117.0"),
        completion_percentage=Decimal("2.50"),
        source_snapshot_hash="test-hash",
    )
    evaluation = RequirementEvaluation(
        id=uid("audit-evaluation"),
        degree_audit_run_id=run.id,
        requirement_node_id=requirement.id,
        status=RequirementEvaluationStatus.SATISFIED,
        required_credits=Decimal("3.0"),
        satisfied_credits=Decimal("3.0"),
        remaining_credits=Decimal("0.0"),
        required_courses=1,
        satisfied_courses=1,
        remaining_courses=0,
        minimum_grade="C",
        explanation="Completed by Mock FIN 301.",
        display_order=10,
    )
    application = AuditCourseApplication(
        id=uid("audit-application"),
        degree_audit_run_id=run.id,
        requirement_evaluation_id=evaluation.id,
        course_id=fin_301.id,
        student_course_attempt_id=attempt.id,
        application_type=AuditApplicationType.COURSE_ATTEMPT,
        credit_amount=Decimal("3.0"),
        grade="B",
        is_completed=True,
        is_in_progress=False,
        is_planned=False,
        is_shared=False,
        explanation="Applied completed Mock FIN 301 attempt.",
    )
    warning = DegreeAuditWarning(
        id=uid("audit-warning"),
        degree_audit_run_id=run.id,
        requirement_evaluation_id=evaluation.id,
        warning_code="MOCK_WARNING",
        severity=AuditWarningSeverity.WARNING,
        message="Mock advisor warning.",
        requires_advisor_confirmation=True,
    )
    session.add(run)
    session.commit()
    session.add(evaluation)
    session.commit()
    session.add_all([application, warning])
    session.commit()

    duplicate_evaluation = RequirementEvaluation(
        id=uid("audit-evaluation-duplicate"),
        degree_audit_run_id=run.id,
        requirement_node_id=requirement.id,
        status=RequirementEvaluationStatus.SATISFIED,
        required_credits=Decimal("3.0"),
        satisfied_credits=Decimal("3.0"),
        remaining_credits=Decimal("0.0"),
        required_courses=1,
        satisfied_courses=1,
        remaining_courses=0,
        explanation="Duplicate.",
        display_order=20,
    )
    session.add(duplicate_evaluation)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    no_source_application = AuditCourseApplication(
        id=uid("audit-application-no-source"),
        degree_audit_run_id=run.id,
        requirement_evaluation_id=evaluation.id,
        course_id=fin_301.id,
        application_type=AuditApplicationType.COURSE_ATTEMPT,
        credit_amount=Decimal("3.0"),
        is_completed=True,
        is_in_progress=False,
        is_planned=False,
        is_shared=False,
        explanation="Missing source.",
    )
    session.add(no_source_application)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()
    bad_remaining = DegreeAuditRun(
        id=uid("audit-run-negative-remaining"),
        student_profile_id=student.id,
        program_version_id=version.id,
        status=AuditRunStatus.COMPLETED,
        engine_version="phase-3a-test",
        calculation_mode=AuditMode.CURRENT,
        total_required_credits=Decimal("120.0"),
        completed_credits=Decimal("130.0"),
        in_progress_credits=Decimal("0.0"),
        planned_credits=Decimal("0.0"),
        remaining_credits=Decimal("-10.0"),
        completion_percentage=Decimal("100.00"),
        source_snapshot_hash="bad-hash",
    )
    session.add(bad_remaining)
    with pytest.raises(IntegrityError):
        session.commit()
