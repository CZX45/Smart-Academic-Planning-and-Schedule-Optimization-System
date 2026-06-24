from __future__ import annotations

from collections.abc import Iterable
from datetime import date, time
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.orm import Session

from app.db.base import Base, DevSeedRecord
from app.db.session import SessionLocal
from app.models.academic import (
    AcademicProgram,
    AcademicTerm,
    ApprovalStatus,
    Campus,
    Course,
    CourseEquivalency,
    CourseOfferingPattern,
    CourseRule,
    CourseRuleExpression,
    CourseRuleExpressionNodeType,
    CourseRuleType,
    CourseSubstitution,
    CourseWaiver,
    DayOfWeek,
    DegreeLevel,
    FrequencyType,
    Institution,
    MeetingType,
    ProgramCombinationRule,
    ProgramType,
    ProgramVersion,
    RequirementCourseOption,
    RequirementNode,
    RequirementType,
    ScenarioRelationshipType,
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


def seed_uuid(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"sapsos-dev-seed:{name}")


MOCK_SOURCE = {
    "source_type": SourceType.MOCK,
    "is_official": False,
    "source_reference": "Phase 2A deterministic mock seed",
    "source_confidence": "mock",
}


def merge_all(session: Session, records: Iterable[Base]) -> None:
    for record in records:
        session.merge(record)


def mock_source() -> dict[str, object]:
    return dict(MOCK_SOURCE)


def course(
    subject_code: str,
    course_number: str,
    title: str,
    *,
    level: int,
    credits: str = "3.0",
) -> Course:
    return Course(
        id=seed_uuid(f"course:{subject_code}-{course_number}"),
        institution_id=seed_uuid("institution:mock-university"),
        subject_code=subject_code,
        course_number=course_number,
        title=title,
        credits_min=Decimal(credits),
        credits_max=Decimal(credits),
        course_level=level,
        repeatable=False,
        **mock_source(),
    )


def requirement_node(
    code: str,
    name: str,
    requirement_type: RequirementType,
    *,
    parent_code: str | None = None,
    display_order: int = 0,
    minimum_credits: Decimal | None = None,
    minimum_courses: int | None = None,
    choose_n: int | None = None,
    minimum_grade: str | None = None,
    minimum_course_level: int | None = None,
    minimum_residency_credits: Decimal | None = None,
    allows_overlap: bool = False,
    is_required: bool = True,
    program_version_key: str = "bs-finance-2024",
) -> RequirementNode:
    node_seed = (
        f"requirement-node:{code}"
        if program_version_key == "bs-finance-2024"
        else f"requirement-node:{program_version_key}:{code}"
    )
    parent_seed = (
        f"requirement-node:{parent_code}"
        if program_version_key == "bs-finance-2024"
        else f"requirement-node:{program_version_key}:{parent_code}"
    )
    return RequirementNode(
        id=seed_uuid(node_seed),
        institution_id=seed_uuid("institution:mock-university"),
        program_version_id=seed_uuid(f"program-version:{program_version_key}"),
        parent_id=seed_uuid(parent_seed) if parent_code else None,
        code=code,
        name=name,
        requirement_type=requirement_type,
        display_order=display_order,
        minimum_credits=minimum_credits,
        minimum_courses=minimum_courses,
        choose_n=choose_n,
        minimum_grade=minimum_grade,
        minimum_course_level=minimum_course_level,
        minimum_residency_credits=minimum_residency_credits,
        allows_overlap=allows_overlap,
        is_required=is_required,
        **mock_source(),
    )


def requirement_option(
    node_code: str,
    subject_code: str,
    course_number: str,
    *,
    display_order: int,
    minimum_grade: str | None = None,
    program_version_key: str = "bs-finance-2024",
) -> RequirementCourseOption:
    option_seed = (
        f"requirement-option:{node_code}:{subject_code}-{course_number}"
        if program_version_key == "bs-finance-2024"
        else f"requirement-option:{program_version_key}:{node_code}:{subject_code}-{course_number}"
    )
    node_seed = (
        f"requirement-node:{node_code}"
        if program_version_key == "bs-finance-2024"
        else f"requirement-node:{program_version_key}:{node_code}"
    )
    return RequirementCourseOption(
        id=seed_uuid(option_seed),
        institution_id=seed_uuid("institution:mock-university"),
        program_version_id=seed_uuid(f"program-version:{program_version_key}"),
        requirement_node_id=seed_uuid(node_seed),
        course_id=seed_uuid(f"course:{subject_code}-{course_number}"),
        display_order=display_order,
        minimum_grade=minimum_grade,
        **mock_source(),
    )


def section(
    seed_name: str,
    course_key: str,
    term_key: str,
    section_code: str,
    *,
    status: SectionStatus,
    modality: SectionModality,
    capacity: int | None = 30,
    available_seats: int | None = 8,
    waitlist_capacity: int | None = 10,
    waitlist_available: int | None = 10,
    title_override: str | None = None,
    instructor_display: str | None = "Mock Instructor",
) -> Section:
    return Section(
        id=seed_uuid(f"section:{seed_name}"),
        institution_id=seed_uuid("institution:mock-university"),
        course_id=seed_uuid(f"course:{course_key}"),
        term_id=seed_uuid(f"term:{term_key}"),
        campus_id=seed_uuid("campus:mock-main"),
        section_code=section_code,
        external_reference=f"MOCK-{seed_name.upper()}",
        title_override=title_override,
        credits=Decimal("3.0"),
        status=status,
        modality=modality,
        capacity=capacity,
        available_seats=available_seats,
        waitlist_capacity=waitlist_capacity,
        waitlist_available=waitlist_available,
        instructor_display=instructor_display,
        **mock_source(),
    )


def section_meeting(
    seed_name: str,
    section_seed_name: str,
    meeting_type: MeetingType,
    *,
    day_of_week: DayOfWeek | None = None,
    start_time: time | None = None,
    end_time: time | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    building: str | None = None,
    room: str | None = None,
    is_arranged: bool = False,
    is_online: bool = False,
    display_order: int = 0,
) -> SectionMeeting:
    return SectionMeeting(
        id=seed_uuid(f"section-meeting:{seed_name}"),
        section_id=seed_uuid(f"section:{section_seed_name}"),
        meeting_type=meeting_type,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        start_date=start_date,
        end_date=end_date,
        building=building,
        room=room,
        timezone="America/New_York",
        is_arranged=is_arranged,
        is_online=is_online,
        display_order=display_order,
        **mock_source(),
    )


def offering_pattern(
    course_key: str,
    term_type: TermType,
    frequency_type: FrequencyType,
    *,
    effective_term_key: str,
    expiration_term_key: str | None,
    confidence_level: str,
    notes: str,
) -> CourseOfferingPattern:
    return CourseOfferingPattern(
        id=seed_uuid(f"course-offering-pattern:{course_key}:{term_type.value}"),
        institution_id=seed_uuid("institution:mock-university"),
        course_id=seed_uuid(f"course:{course_key}"),
        campus_id=seed_uuid("campus:mock-main"),
        term_type=term_type,
        frequency_type=frequency_type,
        effective_term_id=seed_uuid(f"term:{effective_term_key}"),
        expiration_term_id=seed_uuid(f"term:{expiration_term_key}")
        if expiration_term_key
        else None,
        confidence_level=Decimal(confidence_level),
        notes=notes,
        **mock_source(),
    )


def course_rule(
    seed_name: str,
    course_key: str,
    rule_type: CourseRuleType,
    name: str,
    *,
    section_seed_name: str | None = None,
    description: str | None = None,
    requires_manual_confirmation: bool = False,
) -> CourseRule:
    return CourseRule(
        id=seed_uuid(f"course-rule:{seed_name}"),
        institution_id=seed_uuid("institution:mock-university"),
        course_id=seed_uuid(f"course:{course_key}"),
        section_id=seed_uuid(f"section:{section_seed_name}") if section_seed_name else None,
        rule_type=rule_type,
        name=name,
        description=description,
        effective_term_id=seed_uuid("term:2024-fall"),
        requires_manual_confirmation=requires_manual_confirmation,
        **mock_source(),
    )


def expression_node(
    seed_name: str,
    rule_seed_name: str,
    node_type: CourseRuleExpressionNodeType,
    *,
    parent_seed_name: str | None = None,
    display_order: int = 0,
    referenced_course_key: str | None = None,
    minimum_grade: str | None = None,
    minimum_completed_credits: Decimal | None = None,
    class_standing: str | None = None,
    referenced_program_key: str | None = None,
    referenced_campus_key: str | None = None,
    permission_type: str | None = None,
    text_value: str | None = None,
) -> CourseRuleExpression:
    return CourseRuleExpression(
        id=seed_uuid(f"course-rule-expression:{seed_name}"),
        institution_id=seed_uuid("institution:mock-university"),
        course_rule_id=seed_uuid(f"course-rule:{rule_seed_name}"),
        parent_id=(
            seed_uuid(f"course-rule-expression:{parent_seed_name}") if parent_seed_name else None
        ),
        node_type=node_type,
        display_order=display_order,
        referenced_course_id=seed_uuid(f"course:{referenced_course_key}")
        if referenced_course_key
        else None,
        minimum_grade=minimum_grade,
        minimum_completed_credits=minimum_completed_credits,
        class_standing=class_standing,
        referenced_program_id=seed_uuid(f"program:{referenced_program_key}")
        if referenced_program_key
        else None,
        referenced_campus_id=seed_uuid(f"campus:{referenced_campus_key}")
        if referenced_campus_key
        else None,
        permission_type=permission_type,
        text_value=text_value,
        **mock_source(),
    )


def seed_mock_data(session: Session) -> None:
    institution = Institution(
        id=seed_uuid("institution:mock-university"),
        code="MOCKU",
        name="Mock University",
        country="US",
        timezone="America/New_York",
        **mock_source(),
    )
    merge_all(session, [institution])
    session.flush()

    main_campus = Campus(
        id=seed_uuid("campus:mock-main"),
        institution_id=institution.id,
        code="MAIN",
        name="Mock Main Campus",
        location="Mock City, USA",
        **mock_source(),
    )
    merge_all(session, [main_campus])
    session.flush()

    fall_2024 = AcademicTerm(
        id=seed_uuid("term:2024-fall"),
        institution_id=institution.id,
        campus_id=main_campus.id,
        term_code="2024FA",
        name="Fall 2024",
        starts_on=date(2024, 9, 1),
        ends_on=date(2024, 12, 15),
        **mock_source(),
    )
    spring_2025 = AcademicTerm(
        id=seed_uuid("term:2025-spring"),
        institution_id=institution.id,
        campus_id=main_campus.id,
        term_code="2025SP",
        name="Spring 2025",
        starts_on=date(2025, 1, 16),
        ends_on=date(2025, 5, 15),
        **mock_source(),
    )
    merge_all(session, [fall_2024, spring_2025])
    session.flush()

    finance_program = AcademicProgram(
        id=seed_uuid("program:bs-finance"),
        institution_id=institution.id,
        code="BSFIN",
        name="Mock BS Finance",
        program_type=ProgramType.MAJOR,
        degree_level=DegreeLevel.BACHELORS,
        **mock_source(),
    )
    accounting_minor_program = AcademicProgram(
        id=seed_uuid("program:accounting-minor"),
        institution_id=institution.id,
        code="MINACCT",
        name="Mock Accounting Minor",
        program_type=ProgramType.MINOR,
        degree_level=DegreeLevel.BACHELORS,
        **mock_source(),
    )
    economics_minor_program = AcademicProgram(
        id=seed_uuid("program:economics-minor"),
        institution_id=institution.id,
        code="MINECON",
        name="Mock Economics Minor",
        program_type=ProgramType.MINOR,
        degree_level=DegreeLevel.BACHELORS,
        **mock_source(),
    )
    second_major_program = AcademicProgram(
        id=seed_uuid("program:second-major"),
        institution_id=institution.id,
        code="BSZACT",
        name="Mock BS Actuarial Analytics",
        program_type=ProgramType.MAJOR,
        degree_level=DegreeLevel.BACHELORS,
        **mock_source(),
    )
    certificate_program = AcademicProgram(
        id=seed_uuid("program:certificate-data"),
        institution_id=institution.id,
        code="CERTDATA",
        name="Mock Data Literacy Certificate",
        program_type=ProgramType.CERTIFICATE,
        degree_level=DegreeLevel.CERTIFICATE,
        **mock_source(),
    )
    management_program = AcademicProgram(
        id=seed_uuid("program:bs-management"),
        institution_id=institution.id,
        code="BSMGMT",
        name="Mock BS Management",
        program_type=ProgramType.MAJOR,
        degree_level=DegreeLevel.BACHELORS,
        **mock_source(),
    )
    concentration_program = AcademicProgram(
        id=seed_uuid("program:finance-analytics-concentration"),
        institution_id=institution.id,
        code="CONCFINA",
        name="Mock Finance Analytics Concentration",
        program_type=ProgramType.CONCENTRATION,
        degree_level=DegreeLevel.BACHELORS,
        **mock_source(),
    )
    merge_all(
        session,
        [
            finance_program,
            accounting_minor_program,
            economics_minor_program,
            second_major_program,
            certificate_program,
            management_program,
            concentration_program,
        ],
    )
    session.flush()

    finance_version = ProgramVersion(
        id=seed_uuid("program-version:bs-finance-2024"),
        institution_id=institution.id,
        program_id=finance_program.id,
        campus_id=main_campus.id,
        effective_term_id=fall_2024.id,
        catalog_year="2024",
        version_label="Mock BS Finance 2024 Catalog",
        total_credits_required=Decimal("120.0"),
        **mock_source(),
    )
    accounting_minor_version = ProgramVersion(
        id=seed_uuid("program-version:accounting-minor-2024"),
        institution_id=institution.id,
        program_id=accounting_minor_program.id,
        campus_id=main_campus.id,
        effective_term_id=fall_2024.id,
        catalog_year="2024",
        version_label="Mock Accounting Minor 2024 Catalog",
        total_credits_required=Decimal("18.0"),
        **mock_source(),
    )
    economics_minor_version = ProgramVersion(
        id=seed_uuid("program-version:economics-minor-2024"),
        institution_id=institution.id,
        program_id=economics_minor_program.id,
        campus_id=main_campus.id,
        effective_term_id=fall_2024.id,
        catalog_year="2024",
        version_label="Mock Economics Minor 2024 Catalog",
        total_credits_required=Decimal("18.0"),
        **mock_source(),
    )
    second_major_version = ProgramVersion(
        id=seed_uuid("program-version:second-major-2024"),
        institution_id=institution.id,
        program_id=second_major_program.id,
        campus_id=main_campus.id,
        effective_term_id=fall_2024.id,
        catalog_year="2024",
        version_label="Mock Actuarial Analytics 2024 Catalog",
        total_credits_required=Decimal("120.0"),
        **mock_source(),
    )
    certificate_version = ProgramVersion(
        id=seed_uuid("program-version:certificate-data-2024"),
        institution_id=institution.id,
        program_id=certificate_program.id,
        campus_id=main_campus.id,
        effective_term_id=fall_2024.id,
        catalog_year="2024",
        version_label="Mock Data Certificate 2024 Catalog",
        total_credits_required=Decimal("12.0"),
        **mock_source(),
    )
    management_version = ProgramVersion(
        id=seed_uuid("program-version:bs-management-2024"),
        institution_id=institution.id,
        program_id=management_program.id,
        campus_id=main_campus.id,
        effective_term_id=fall_2024.id,
        catalog_year="2024",
        version_label="Mock BS Management 2024 Catalog",
        total_credits_required=Decimal("120.0"),
        **mock_source(),
    )
    concentration_version = ProgramVersion(
        id=seed_uuid("program-version:finance-analytics-concentration-2024"),
        institution_id=institution.id,
        program_id=concentration_program.id,
        campus_id=main_campus.id,
        effective_term_id=fall_2024.id,
        catalog_year="2024",
        version_label="Mock Finance Analytics Concentration 2024 Catalog",
        total_credits_required=Decimal("9.0"),
        **mock_source(),
    )
    merge_all(
        session,
        [
            finance_version,
            accounting_minor_version,
            economics_minor_version,
            second_major_version,
            certificate_version,
            management_version,
            concentration_version,
        ],
    )
    session.flush()

    courses = [
        course("GEN", "101", "Mock General Education Seminar", level=100),
        course("BUS", "101", "Mock Business Foundations", level=100),
        course("ACC", "101", "Mock Accounting Foundations", level=100),
        course("FIN", "200", "Mock Finance Foundations", level=200),
        course("FIN", "201", "Mock Finance Transfer Equivalent", level=200),
        course("FIN", "300", "Mock Managerial Finance", level=300),
        course("FIN", "301", "Mock Corporate Finance", level=300),
        course("FIN", "400", "Mock Advanced Finance", level=400),
        course("FIN", "401", "Mock Investments", level=400),
        course("FIN", "401L", "Mock FIN 401 Lab", level=400),
        course("FIN", "402", "Mock Risk Management", level=400),
        course("FIN", "403", "Mock International Finance", level=400),
        course("ELEC", "100", "Mock Free Elective", level=100),
        course("ACCT", "300", "Mock Accounting Analytics", level=300),
        course("ACCT", "310", "Mock Advanced Accounting", level=300),
        course("ECON", "250", "Mock Managerial Economics", level=200),
        course("ECON", "260", "Mock Applied Microeconomics", level=200),
        course("DATA", "200", "Mock Data Literacy", level=200),
        course("MGMT", "200", "Mock Management Foundations", level=200),
        course("ACTL", "300", "Mock Actuarial Modeling", level=300),
    ]
    merge_all(session, courses)
    session.flush()

    sections = [
        section(
            "2024-fall-fin-300-001",
            "FIN-300",
            "2024-fall",
            "001",
            status=SectionStatus.OPEN,
            modality=SectionModality.IN_PERSON,
        ),
        section(
            "2024-fall-fin-300-web",
            "FIN-300",
            "2024-fall",
            "WEB",
            status=SectionStatus.OPEN,
            modality=SectionModality.ONLINE_ASYNCHRONOUS,
            capacity=None,
            available_seats=None,
            waitlist_capacity=None,
            waitlist_available=None,
            instructor_display="Mock Online Instructor",
        ),
        section(
            "2025-spring-fin-400-hyb",
            "FIN-400",
            "2025-spring",
            "HYB",
            status=SectionStatus.WAITLIST,
            modality=SectionModality.HYBRID,
            available_seats=0,
            waitlist_available=4,
        ),
        section(
            "2025-spring-fin-401l-lab",
            "FIN-401L",
            "2025-spring",
            "LAB",
            status=SectionStatus.OPEN,
            modality=SectionModality.IN_PERSON,
            title_override="Mock Finance Lab",
        ),
    ]
    merge_all(session, sections)
    session.flush()

    meetings = [
        section_meeting(
            "2024-fall-fin-300-001-lecture",
            "2024-fall-fin-300-001",
            MeetingType.LECTURE,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(10, 15),
            start_date=fall_2024.starts_on,
            end_date=fall_2024.ends_on,
            building="Mock Academic Building",
            room="101",
            display_order=10,
        ),
        section_meeting(
            "2024-fall-fin-300-001-lab",
            "2024-fall-fin-300-001",
            MeetingType.LAB,
            day_of_week=DayOfWeek.WEDNESDAY,
            start_time=time(14, 0),
            end_time=time(15, 50),
            start_date=fall_2024.starts_on,
            end_date=fall_2024.ends_on,
            building="Mock Finance Lab",
            room="201",
            display_order=20,
        ),
        section_meeting(
            "2024-fall-fin-300-web-async",
            "2024-fall-fin-300-web",
            MeetingType.OTHER,
            is_online=True,
            display_order=10,
        ),
        section_meeting(
            "2025-spring-fin-400-hyb-seminar",
            "2025-spring-fin-400-hyb",
            MeetingType.SEMINAR,
            day_of_week=DayOfWeek.THURSDAY,
            start_time=time(18, 0),
            end_time=time(20, 30),
            start_date=spring_2025.starts_on,
            end_date=spring_2025.ends_on,
            building="Mock Evening Center",
            room="310",
            display_order=10,
        ),
        section_meeting(
            "2025-spring-fin-401l-lab",
            "2025-spring-fin-401l-lab",
            MeetingType.LAB,
            day_of_week=DayOfWeek.FRIDAY,
            start_time=time(10, 0),
            end_time=time(11, 50),
            start_date=spring_2025.starts_on,
            end_date=spring_2025.ends_on,
            building="Mock Finance Lab",
            room="202",
            display_order=10,
        ),
    ]
    merge_all(session, meetings)
    session.flush()

    offering_patterns = [
        offering_pattern(
            "FIN-300",
            TermType.FALL,
            FrequencyType.ANNUAL,
            effective_term_key="2024-fall",
            expiration_term_key="2025-spring",
            confidence_level="0.70",
            notes="Mock historical pattern only; not a school commitment.",
        ),
        offering_pattern(
            "FIN-400",
            TermType.SPRING,
            FrequencyType.ANNUAL,
            effective_term_key="2024-fall",
            expiration_term_key="2025-spring",
            confidence_level="0.65",
            notes="Mock expected pattern only; students must confirm official offerings.",
        ),
        offering_pattern(
            "FIN-401L",
            TermType.SPRING,
            FrequencyType.IRREGULAR,
            effective_term_key="2024-fall",
            expiration_term_key="2025-spring",
            confidence_level="0.50",
            notes="Mock lab pattern for storage tests only.",
        ),
    ]
    merge_all(session, offering_patterns)
    session.flush()

    course_rules = [
        course_rule(
            "fin-300-prerequisite",
            "FIN-300",
            CourseRuleType.PREREQUISITE,
            "Mock FIN 300 prerequisite",
            description="Mock rule: complete Mock FIN 200 with a minimum grade of C.",
        ),
        course_rule(
            "fin-400-corequisite",
            "FIN-400",
            CourseRuleType.COREQUISITE,
            "Mock FIN 400 corequisite",
            description="Mock rule: take Mock FIN 401 Lab as a corequisite.",
        ),
        course_rule(
            "fin-400-major-restriction",
            "FIN-400",
            CourseRuleType.REGISTRATION_RESTRICTION,
            "Mock finance major restriction",
            description="Mock rule: finance major restriction for storage only.",
            requires_manual_confirmation=True,
        ),
        course_rule(
            "fin-400-section-permission",
            "FIN-400",
            CourseRuleType.PERMISSION,
            "Mock hybrid section permission",
            section_seed_name="2025-spring-fin-400-hyb",
            description="Mock section-level permission requirement.",
            requires_manual_confirmation=True,
        ),
    ]
    merge_all(session, course_rules)
    session.flush()

    expressions = [
        expression_node(
            "fin-300-prerequisite-root",
            "fin-300-prerequisite",
            CourseRuleExpressionNodeType.AND,
            display_order=0,
            text_value="Mock FIN 300 requires Mock FIN 200 with minimum grade C.",
        ),
        expression_node(
            "fin-300-prerequisite-completed-fin-200",
            "fin-300-prerequisite",
            CourseRuleExpressionNodeType.COMPLETED_COURSE,
            parent_seed_name="fin-300-prerequisite-root",
            display_order=10,
            referenced_course_key="FIN-200",
            text_value="Completed Mock FIN 200.",
        ),
        expression_node(
            "fin-300-prerequisite-min-grade-c",
            "fin-300-prerequisite",
            CourseRuleExpressionNodeType.MINIMUM_GRADE,
            parent_seed_name="fin-300-prerequisite-root",
            display_order=20,
            referenced_course_key="FIN-200",
            minimum_grade="C",
            text_value="Minimum grade C in Mock FIN 200.",
        ),
        expression_node(
            "fin-400-corequisite-root",
            "fin-400-corequisite",
            CourseRuleExpressionNodeType.COMPLETED_COURSE,
            display_order=0,
            referenced_course_key="FIN-401L",
            text_value="Mock FIN 401 Lab corequisite placeholder.",
        ),
        expression_node(
            "fin-400-major-restriction-root",
            "fin-400-major-restriction",
            CourseRuleExpressionNodeType.MAJOR_RESTRICTION,
            display_order=0,
            referenced_program_key="bs-finance",
            text_value="Mock finance major restriction.",
        ),
        expression_node(
            "fin-400-section-permission-root",
            "fin-400-section-permission",
            CourseRuleExpressionNodeType.PERMISSION_REQUIRED,
            display_order=0,
            permission_type="DEPARTMENT_APPROVAL",
            text_value="Mock department approval required.",
        ),
    ]
    merge_all(session, expressions)
    session.flush()

    equivalency = CourseEquivalency(
        id=seed_uuid("course-equivalency:fin-201-fin-301"),
        institution_id=institution.id,
        source_course_id=seed_uuid("course:FIN-201"),
        equivalent_course_id=seed_uuid("course:FIN-301"),
        note="Mock-only equivalency used to exercise Phase 2A storage.",
        **mock_source(),
    )
    merge_all(session, [equivalency])
    session.flush()

    root = requirement_node(
        "ROOT",
        "Mock BS Finance",
        RequirementType.GROUP,
        display_order=0,
    )
    merge_all(session, [root])
    session.flush()

    first_level_nodes = [
        requirement_node(
            "TOTAL-CREDITS",
            "Total Credits",
            RequirementType.TOTAL_CREDITS,
            parent_code="ROOT",
            display_order=10,
            minimum_credits=Decimal("120.0"),
        ),
        requirement_node(
            "GENERAL-ED",
            "General Education",
            RequirementType.GROUP,
            parent_code="ROOT",
            display_order=20,
        ),
        requirement_node(
            "BUSINESS-CORE",
            "Business Core",
            RequirementType.ALL_OF,
            parent_code="ROOT",
            display_order=30,
        ),
        requirement_node(
            "FINANCE-MAJOR",
            "Finance Major",
            RequirementType.ALL_OF,
            parent_code="ROOT",
            display_order=40,
        ),
        requirement_node(
            "FREE-ELECTIVES",
            "Free Electives",
            RequirementType.MINIMUM_CREDITS,
            parent_code="ROOT",
            display_order=50,
            minimum_credits=Decimal("9.0"),
            is_required=False,
        ),
    ]
    merge_all(session, first_level_nodes)
    session.flush()

    child_nodes = [
        requirement_node(
            "GEN-REQ",
            "Transferred General Education Course",
            RequirementType.REQUIRED_COURSE,
            parent_code="GENERAL-ED",
            display_order=10,
        ),
        requirement_node(
            "WAIVER-DEMO",
            "Approved Waiver Demonstration",
            RequirementType.REQUIRED_COURSE,
            parent_code="GENERAL-ED",
            display_order=20,
        ),
        requirement_node(
            "BUS-REQ-A",
            "Required Course A",
            RequirementType.REQUIRED_COURSE,
            parent_code="BUSINESS-CORE",
            display_order=10,
            minimum_grade="C",
        ),
        requirement_node(
            "BUS-REQ-B",
            "Required Course B",
            RequirementType.REQUIRED_COURSE,
            parent_code="BUSINESS-CORE",
            display_order=20,
            minimum_grade="C",
            allows_overlap=True,
        ),
        requirement_node(
            "FIN-REQ",
            "Required Finance Course",
            RequirementType.REQUIRED_COURSE,
            parent_code="FINANCE-MAJOR",
            display_order=10,
            minimum_grade="C",
            minimum_course_level=300,
        ),
        requirement_node(
            "CAPSTONE-DEMO",
            "Mock Finance Capstone",
            RequirementType.CAPSTONE,
            parent_code="FINANCE-MAJOR",
            display_order=15,
            minimum_grade="C",
            minimum_course_level=400,
        ),
        requirement_node(
            "FIN-ELECTIVES",
            "Choose 2 from 3 Finance Electives",
            RequirementType.CHOOSE_N,
            parent_code="FINANCE-MAJOR",
            display_order=20,
            choose_n=2,
            minimum_courses=2,
            minimum_grade="C",
            minimum_course_level=400,
        ),
        requirement_node(
            "SUBSTITUTION-DEMO",
            "Approved Substitution Demonstration",
            RequirementType.REQUIRED_COURSE,
            parent_code="FINANCE-MAJOR",
            display_order=30,
            minimum_grade="C",
        ),
        requirement_node(
            "UPPER-LEVEL",
            "Upper-Level Finance Credits",
            RequirementType.COURSE_LEVEL,
            parent_code="FINANCE-MAJOR",
            display_order=40,
            minimum_credits=Decimal("9.0"),
            minimum_course_level=300,
        ),
        requirement_node(
            "FIN-DISTINCT",
            "Minimum Distinct Finance Courses",
            RequirementType.MINIMUM_COURSES,
            parent_code="FINANCE-MAJOR",
            display_order=50,
            minimum_courses=3,
            minimum_grade="C",
        ),
        requirement_node(
            "RESIDENCY",
            "Mock Residency Credits",
            RequirementType.RESIDENCY,
            parent_code="ROOT",
            display_order=60,
            minimum_residency_credits=Decimal("9.0"),
        ),
        requirement_node(
            "MANUAL-REVIEW",
            "Manual Review Configuration Example",
            RequirementType.MINIMUM_GRADE,
            parent_code="ROOT",
            display_order=70,
            minimum_grade="C",
        ),
    ]
    merge_all(session, child_nodes)
    session.flush()

    requirement_options = [
        requirement_option("GEN-REQ", "GEN", "101", display_order=10),
        requirement_option("BUS-REQ-A", "BUS", "101", display_order=10, minimum_grade="C"),
        requirement_option("BUS-REQ-B", "ACC", "101", display_order=10, minimum_grade="C"),
        requirement_option("FIN-REQ", "FIN", "301", display_order=10, minimum_grade="C"),
        requirement_option("CAPSTONE-DEMO", "FIN", "400", display_order=10, minimum_grade="C"),
        requirement_option("FIN-ELECTIVES", "FIN", "401", display_order=10, minimum_grade="C"),
        requirement_option("FIN-ELECTIVES", "FIN", "402", display_order=20, minimum_grade="C"),
        requirement_option("FIN-ELECTIVES", "FIN", "403", display_order=30, minimum_grade="C"),
        requirement_option("SUBSTITUTION-DEMO", "FIN", "403", display_order=10, minimum_grade="C"),
    ]
    merge_all(session, requirement_options)
    session.flush()

    secondary_requirement_nodes = [
        requirement_node(
            "ROOT",
            "Mock Accounting Minor",
            RequirementType.ALL_OF,
            display_order=0,
            program_version_key="accounting-minor-2024",
        ),
        requirement_node(
            "ACCT-MINOR-TOTAL",
            "Accounting Minor Total Credits",
            RequirementType.TOTAL_CREDITS,
            parent_code="ROOT",
            display_order=10,
            minimum_credits=Decimal("18.0"),
            program_version_key="accounting-minor-2024",
        ),
        requirement_node(
            "ACCT-MINOR-SHARED",
            "Accounting Foundations",
            RequirementType.REQUIRED_COURSE,
            parent_code="ROOT",
            display_order=20,
            minimum_grade="C",
            allows_overlap=True,
            program_version_key="accounting-minor-2024",
        ),
        requirement_node(
            "ACCT-MINOR-UNIQUE",
            "Accounting Analytics",
            RequirementType.REQUIRED_COURSE,
            parent_code="ROOT",
            display_order=30,
            minimum_grade="C",
            program_version_key="accounting-minor-2024",
        ),
        requirement_node(
            "ACCT-MINOR-ADV",
            "Advanced Accounting",
            RequirementType.REQUIRED_COURSE,
            parent_code="ROOT",
            display_order=40,
            minimum_grade="C",
            program_version_key="accounting-minor-2024",
        ),
        requirement_node(
            "ROOT",
            "Mock Economics Minor",
            RequirementType.ALL_OF,
            display_order=0,
            program_version_key="economics-minor-2024",
        ),
        requirement_node(
            "ECON-MINOR-TOTAL",
            "Economics Minor Total Credits",
            RequirementType.TOTAL_CREDITS,
            parent_code="ROOT",
            display_order=10,
            minimum_credits=Decimal("18.0"),
            program_version_key="economics-minor-2024",
        ),
        requirement_node(
            "ECON-MINOR-CORE",
            "Managerial Economics",
            RequirementType.REQUIRED_COURSE,
            parent_code="ROOT",
            display_order=20,
            minimum_grade="C",
            program_version_key="economics-minor-2024",
        ),
        requirement_node(
            "ECON-MINOR-APPLIED",
            "Applied Microeconomics",
            RequirementType.REQUIRED_COURSE,
            parent_code="ROOT",
            display_order=30,
            minimum_grade="C",
            program_version_key="economics-minor-2024",
        ),
        requirement_node(
            "ROOT",
            "Mock BS Actuarial Analytics",
            RequirementType.ALL_OF,
            display_order=0,
            program_version_key="second-major-2024",
        ),
        requirement_node(
            "ACTL-TOTAL",
            "Actuarial Analytics Total Credits",
            RequirementType.TOTAL_CREDITS,
            parent_code="ROOT",
            display_order=10,
            minimum_credits=Decimal("120.0"),
            program_version_key="second-major-2024",
        ),
        requirement_node(
            "ACTL-FIN-FOUNDATION",
            "Finance Foundation Reuse Candidate",
            RequirementType.REQUIRED_COURSE,
            parent_code="ROOT",
            display_order=20,
            minimum_grade="C",
            allows_overlap=True,
            program_version_key="second-major-2024",
        ),
        requirement_node(
            "ACTL-MODELING",
            "Actuarial Modeling",
            RequirementType.REQUIRED_COURSE,
            parent_code="ROOT",
            display_order=30,
            minimum_grade="C",
            program_version_key="second-major-2024",
        ),
        requirement_node(
            "ROOT",
            "Mock Data Literacy Certificate",
            RequirementType.ALL_OF,
            display_order=0,
            program_version_key="certificate-data-2024",
        ),
        requirement_node(
            "DATA-CERT-CORE",
            "Data Literacy Core",
            RequirementType.REQUIRED_COURSE,
            parent_code="ROOT",
            display_order=10,
            minimum_grade="C",
            program_version_key="certificate-data-2024",
        ),
        requirement_node(
            "ROOT",
            "Mock BS Management",
            RequirementType.ALL_OF,
            display_order=0,
            program_version_key="bs-management-2024",
        ),
        requirement_node(
            "MGMT-TOTAL",
            "Management Total Credits",
            RequirementType.TOTAL_CREDITS,
            parent_code="ROOT",
            display_order=10,
            minimum_credits=Decimal("120.0"),
            program_version_key="bs-management-2024",
        ),
        requirement_node(
            "MGMT-BUS-FOUNDATION",
            "Reusable Business Foundation",
            RequirementType.REQUIRED_COURSE,
            parent_code="ROOT",
            display_order=20,
            minimum_grade="C",
            program_version_key="bs-management-2024",
        ),
        requirement_node(
            "MGMT-CORE",
            "Management Foundations",
            RequirementType.REQUIRED_COURSE,
            parent_code="ROOT",
            display_order=30,
            minimum_grade="C",
            program_version_key="bs-management-2024",
        ),
        requirement_node(
            "MGMT-FREE",
            "Management Free Elective Space",
            RequirementType.MINIMUM_CREDITS,
            parent_code="ROOT",
            display_order=40,
            minimum_credits=Decimal("12.0"),
            is_required=False,
            program_version_key="bs-management-2024",
        ),
        requirement_node(
            "ROOT",
            "Mock Finance Analytics Concentration",
            RequirementType.ALL_OF,
            display_order=0,
            program_version_key="finance-analytics-concentration-2024",
        ),
        requirement_node(
            "CONC-FIN-ANALYTICS",
            "Finance Analytics Course",
            RequirementType.REQUIRED_COURSE,
            parent_code="ROOT",
            display_order=10,
            minimum_grade="C",
            allows_overlap=True,
            program_version_key="finance-analytics-concentration-2024",
        ),
    ]
    merge_all(session, secondary_requirement_nodes)
    session.flush()

    secondary_requirement_options = [
        requirement_option(
            "ACCT-MINOR-SHARED",
            "ACC",
            "101",
            display_order=10,
            minimum_grade="C",
            program_version_key="accounting-minor-2024",
        ),
        requirement_option(
            "ACCT-MINOR-UNIQUE",
            "ACCT",
            "300",
            display_order=10,
            minimum_grade="C",
            program_version_key="accounting-minor-2024",
        ),
        requirement_option(
            "ACCT-MINOR-ADV",
            "ACCT",
            "310",
            display_order=10,
            minimum_grade="C",
            program_version_key="accounting-minor-2024",
        ),
        requirement_option(
            "ECON-MINOR-CORE",
            "ECON",
            "250",
            display_order=10,
            minimum_grade="C",
            program_version_key="economics-minor-2024",
        ),
        requirement_option(
            "ECON-MINOR-APPLIED",
            "ECON",
            "260",
            display_order=10,
            minimum_grade="C",
            program_version_key="economics-minor-2024",
        ),
        requirement_option(
            "ACTL-FIN-FOUNDATION",
            "FIN",
            "301",
            display_order=10,
            minimum_grade="C",
            program_version_key="second-major-2024",
        ),
        requirement_option(
            "ACTL-MODELING",
            "ACTL",
            "300",
            display_order=10,
            minimum_grade="C",
            program_version_key="second-major-2024",
        ),
        requirement_option(
            "DATA-CERT-CORE",
            "DATA",
            "200",
            display_order=10,
            minimum_grade="C",
            program_version_key="certificate-data-2024",
        ),
        requirement_option(
            "MGMT-BUS-FOUNDATION",
            "BUS",
            "101",
            display_order=10,
            minimum_grade="C",
            program_version_key="bs-management-2024",
        ),
        requirement_option(
            "MGMT-CORE",
            "MGMT",
            "200",
            display_order=10,
            minimum_grade="C",
            program_version_key="bs-management-2024",
        ),
        requirement_option(
            "CONC-FIN-ANALYTICS",
            "FIN",
            "401",
            display_order=10,
            minimum_grade="C",
            program_version_key="finance-analytics-concentration-2024",
        ),
    ]
    merge_all(session, secondary_requirement_options)
    session.flush()

    student = StudentProfile(
        id=seed_uuid("student-profile:mock-student"),
        home_institution_id=institution.id,
        home_campus_id=main_campus.id,
        expected_graduation_term_id=spring_2025.id,
        external_ref="MOCK-STUDENT-001",
        display_name="Mock Student",
        class_standing="SOPHOMORE",
        **mock_source(),
    )
    merge_all(session, [student])
    session.flush()

    student_program = StudentAcademicProgram(
        id=seed_uuid("student-academic-program:mock-student-bs-finance"),
        student_profile_id=student.id,
        program_version_id=finance_version.id,
        program_type=StudentProgramType.PRIMARY_MAJOR,
        status=StudentAcademicProgramStatus.ACTIVE,
        declared_on=date(2024, 9, 1),
        **mock_source(),
    )
    merge_all(session, [student_program])
    session.flush()

    attempts = [
        StudentCourseAttempt(
            id=seed_uuid("attempt:mock-student-bus-101-1"),
            student_profile_id=student.id,
            course_id=seed_uuid("course:BUS-101"),
            term_id=fall_2024.id,
            attempt_number=1,
            status=StudentCourseAttemptStatus.COMPLETED,
            grade="B",
            credits_attempted=Decimal("3.0"),
            credits_earned=Decimal("3.0"),
            is_repeat=False,
            **mock_source(),
        ),
        StudentCourseAttempt(
            id=seed_uuid("attempt:mock-student-acc-101-1"),
            student_profile_id=student.id,
            course_id=seed_uuid("course:ACC-101"),
            term_id=fall_2024.id,
            attempt_number=1,
            status=StudentCourseAttemptStatus.COMPLETED,
            grade="D",
            credits_attempted=Decimal("3.0"),
            credits_earned=Decimal("3.0"),
            is_repeat=False,
            **mock_source(),
        ),
        StudentCourseAttempt(
            id=seed_uuid("attempt:mock-student-acc-101-2"),
            student_profile_id=student.id,
            course_id=seed_uuid("course:ACC-101"),
            term_id=spring_2025.id,
            attempt_number=2,
            status=StudentCourseAttemptStatus.COMPLETED,
            grade="B",
            credits_attempted=Decimal("3.0"),
            credits_earned=Decimal("3.0"),
            is_repeat=True,
            **mock_source(),
        ),
        StudentCourseAttempt(
            id=seed_uuid("attempt:mock-student-fin-301-1"),
            student_profile_id=student.id,
            course_id=seed_uuid("course:FIN-301"),
            term_id=fall_2024.id,
            attempt_number=1,
            status=StudentCourseAttemptStatus.COMPLETED,
            grade="B",
            credits_attempted=Decimal("3.0"),
            credits_earned=Decimal("3.0"),
            is_repeat=False,
            **mock_source(),
        ),
        StudentCourseAttempt(
            id=seed_uuid("attempt:mock-student-fin-401-1"),
            student_profile_id=student.id,
            course_id=seed_uuid("course:FIN-401"),
            term_id=fall_2024.id,
            attempt_number=1,
            status=StudentCourseAttemptStatus.COMPLETED,
            grade="B+",
            credits_attempted=Decimal("3.0"),
            credits_earned=Decimal("3.0"),
            is_repeat=False,
            **mock_source(),
        ),
        StudentCourseAttempt(
            id=seed_uuid("attempt:mock-student-fin-402-1"),
            student_profile_id=student.id,
            course_id=seed_uuid("course:FIN-402"),
            term_id=spring_2025.id,
            attempt_number=1,
            status=StudentCourseAttemptStatus.IN_PROGRESS,
            grade=None,
            credits_attempted=Decimal("3.0"),
            credits_earned=Decimal("0.0"),
            is_repeat=False,
            **mock_source(),
        ),
        StudentCourseAttempt(
            id=seed_uuid("attempt:mock-student-fin-400-1"),
            student_profile_id=student.id,
            course_id=seed_uuid("course:FIN-400"),
            term_id=spring_2025.id,
            attempt_number=1,
            status=StudentCourseAttemptStatus.PLANNED,
            grade=None,
            credits_attempted=Decimal("3.0"),
            credits_earned=Decimal("0.0"),
            is_repeat=False,
            **mock_source(),
        ),
        StudentCourseAttempt(
            id=seed_uuid("attempt:mock-student-fin-200-incomplete"),
            student_profile_id=student.id,
            course_id=seed_uuid("course:FIN-200"),
            term_id=spring_2025.id,
            attempt_number=1,
            status=StudentCourseAttemptStatus.INCOMPLETE,
            grade="I",
            credits_attempted=Decimal("3.0"),
            credits_earned=Decimal("0.0"),
            is_repeat=False,
            **mock_source(),
        ),
        StudentCourseAttempt(
            id=seed_uuid("attempt:mock-student-elec-100-1"),
            student_profile_id=student.id,
            course_id=seed_uuid("course:ELEC-100"),
            term_id=fall_2024.id,
            attempt_number=1,
            status=StudentCourseAttemptStatus.COMPLETED,
            grade="A",
            credits_attempted=Decimal("3.0"),
            credits_earned=Decimal("3.0"),
            is_repeat=False,
            **mock_source(),
        ),
        StudentCourseAttempt(
            id=seed_uuid("attempt:mock-student-acct-300-1"),
            student_profile_id=student.id,
            course_id=seed_uuid("course:ACCT-300"),
            term_id=fall_2024.id,
            attempt_number=1,
            status=StudentCourseAttemptStatus.COMPLETED,
            grade="B",
            credits_attempted=Decimal("3.0"),
            credits_earned=Decimal("3.0"),
            is_repeat=False,
            **mock_source(),
        ),
        StudentCourseAttempt(
            id=seed_uuid("attempt:mock-student-econ-250-1"),
            student_profile_id=student.id,
            course_id=seed_uuid("course:ECON-250"),
            term_id=fall_2024.id,
            attempt_number=1,
            status=StudentCourseAttemptStatus.COMPLETED,
            grade="A-",
            credits_attempted=Decimal("3.0"),
            credits_earned=Decimal("3.0"),
            is_repeat=False,
            **mock_source(),
        ),
        StudentCourseAttempt(
            id=seed_uuid("attempt:mock-student-data-200-planned"),
            student_profile_id=student.id,
            course_id=seed_uuid("course:DATA-200"),
            term_id=spring_2025.id,
            attempt_number=1,
            status=StudentCourseAttemptStatus.PLANNED,
            grade=None,
            credits_attempted=Decimal("3.0"),
            credits_earned=Decimal("0.0"),
            is_repeat=False,
            **mock_source(),
        ),
    ]
    merge_all(session, attempts)
    session.flush()

    transfer_credits = [
        TransferCredit(
            id=seed_uuid("transfer-credit:mock-student-gen-101"),
            student_profile_id=student.id,
            equivalent_course_id=seed_uuid("course:GEN-101"),
            source_institution_name="Mock Transfer College",
            source_course_code="MTC 100",
            credits_earned=Decimal("3.0"),
            grade="TA",
            status=ApprovalStatus.APPROVED,
            **mock_source(),
        ),
        TransferCredit(
            id=seed_uuid("transfer-credit:mock-student-fin-200-pending"),
            student_profile_id=student.id,
            equivalent_course_id=seed_uuid("course:FIN-200"),
            source_institution_name="Mock Pending College",
            source_course_code="MPC 200",
            credits_earned=Decimal("3.0"),
            grade=None,
            status=ApprovalStatus.PENDING,
            **mock_source(),
        ),
    ]
    course_waivers = [
        CourseWaiver(
            id=seed_uuid("course-waiver:mock-student-general-ed-pending"),
            institution_id=institution.id,
            student_profile_id=student.id,
            program_version_id=finance_version.id,
            requirement_node_id=seed_uuid("requirement-node:GENERAL-ED"),
            status=ApprovalStatus.PENDING,
            reason="Mock pending waiver. It must not be applied by Phase 3A.",
            **mock_source(),
        ),
        CourseWaiver(
            id=seed_uuid("course-waiver:mock-student-waiver-demo-approved"),
            institution_id=institution.id,
            student_profile_id=student.id,
            program_version_id=finance_version.id,
            requirement_node_id=seed_uuid("requirement-node:WAIVER-DEMO"),
            status=ApprovalStatus.APPROVED,
            reason="Mock approved waiver that satisfies a requirement but adds no credits.",
            **mock_source(),
        ),
    ]
    substitutions = [
        CourseSubstitution(
            id=seed_uuid("course-substitution:mock-student-fin-elective-rejected"),
            institution_id=institution.id,
            student_profile_id=student.id,
            program_version_id=finance_version.id,
            requirement_node_id=seed_uuid("requirement-node:FIN-ELECTIVES"),
            original_course_id=seed_uuid("course:FIN-401"),
            substitute_course_id=seed_uuid("course:FIN-402"),
            status=ApprovalStatus.REJECTED,
            reason="Mock rejected substitution. It must not be applied by Phase 3A.",
            **mock_source(),
        ),
        CourseSubstitution(
            id=seed_uuid("course-substitution:mock-student-substitution-demo-approved"),
            institution_id=institution.id,
            student_profile_id=student.id,
            program_version_id=finance_version.id,
            requirement_node_id=seed_uuid("requirement-node:SUBSTITUTION-DEMO"),
            original_course_id=seed_uuid("course:FIN-403"),
            substitute_course_id=seed_uuid("course:ELEC-100"),
            status=ApprovalStatus.APPROVED,
            reason="Mock approved substitution using a completed substitute course.",
            **mock_source(),
        ),
    ]
    merge_all(session, [*transfer_credits, *course_waivers, *substitutions])
    session.flush()

    combination_rules = [
        ProgramCombinationRule(
            id=seed_uuid("program-combination-rule:finance-accounting-minor-2024"),
            primary_program_version_id=finance_version.id,
            secondary_program_version_id=accounting_minor_version.id,
            combination_type=ScenarioRelationshipType.MINOR,
            maximum_shared_credits=Decimal("3.0"),
            minimum_unique_secondary_credits=Decimal("6.0"),
            minimum_unique_courses=2,
            allows_double_counting=True,
            requires_manual_confirmation=False,
            notes=(
                "Mock rule: finance major and accounting minor may share one "
                "3-credit requirement, with at least 6 unique minor credits."
            ),
            effective_term_id=fall_2024.id,
            **mock_source(),
        ),
        ProgramCombinationRule(
            id=seed_uuid("program-combination-rule:finance-economics-minor-2024"),
            primary_program_version_id=finance_version.id,
            secondary_program_version_id=economics_minor_version.id,
            combination_type=ScenarioRelationshipType.MINOR,
            maximum_shared_credits=Decimal("0.0"),
            minimum_unique_secondary_credits=Decimal("9.0"),
            minimum_unique_courses=3,
            allows_double_counting=False,
            requires_manual_confirmation=True,
            notes="Mock rule: economics minor credits are modeled as unique-only.",
            effective_term_id=fall_2024.id,
            **mock_source(),
        ),
        ProgramCombinationRule(
            id=seed_uuid("program-combination-rule:finance-data-certificate-2024"),
            primary_program_version_id=finance_version.id,
            secondary_program_version_id=certificate_version.id,
            combination_type=ScenarioRelationshipType.CERTIFICATE,
            maximum_shared_credits=Decimal("0.0"),
            minimum_unique_secondary_credits=Decimal("12.0"),
            minimum_unique_courses=4,
            allows_double_counting=False,
            requires_manual_confirmation=True,
            notes="Mock rule: certificate requirements need advisor confirmation.",
            effective_term_id=fall_2024.id,
            **mock_source(),
        ),
        ProgramCombinationRule(
            id=seed_uuid("program-combination-rule:finance-concentration-2024"),
            primary_program_version_id=finance_version.id,
            secondary_program_version_id=concentration_version.id,
            combination_type=ScenarioRelationshipType.CONCENTRATION,
            maximum_shared_credits=Decimal("6.0"),
            minimum_unique_secondary_credits=Decimal("0.0"),
            minimum_unique_courses=0,
            allows_double_counting=True,
            requires_manual_confirmation=False,
            notes="Mock rule: concentration may overlap with finance major electives.",
            effective_term_id=fall_2024.id,
            **mock_source(),
        ),
        ProgramCombinationRule(
            id=seed_uuid("program-combination-rule:management-accounting-minor-2024"),
            primary_program_version_id=management_version.id,
            secondary_program_version_id=accounting_minor_version.id,
            combination_type=ScenarioRelationshipType.MINOR,
            maximum_shared_credits=Decimal("0.0"),
            minimum_unique_secondary_credits=Decimal("9.0"),
            minimum_unique_courses=3,
            allows_double_counting=False,
            requires_manual_confirmation=True,
            notes="Mock directional rule differs from finance-to-accounting.",
            effective_term_id=fall_2024.id,
            **mock_source(),
        ),
    ]
    merge_all(session, combination_rules)
    session.flush()

    merge_all(
        session,
        [
            DevSeedRecord(
                id=seed_uuid("dev-seed-record:mock-institution"),
                seed_key="mock-institution",
                label="Mock institution seed marker",
                payload={
                    "source_type": SourceType.MOCK.value,
                    "is_official": False,
                    "advisor_confirmation_required": True,
                },
            ),
            DevSeedRecord(
                id=seed_uuid("dev-seed-record:mock-academic-domain"),
                seed_key="mock-academic-domain",
                label="Phase 2A mock academic domain seed marker",
                payload={
                    "source_type": SourceType.MOCK.value,
                    "is_official": False,
                    "program": "Mock BS Finance",
                    "student": "Mock Student",
                },
            ),
            DevSeedRecord(
                id=seed_uuid("dev-seed-record:mock-course-rules-sections"),
                seed_key="mock-course-rules-sections",
                label="Phase 2B mock course rules and sections seed marker",
                payload={
                    "source_type": SourceType.MOCK.value,
                    "is_official": False,
                    "sections": ["Mock Fall Term Sections", "Mock Spring Term Sections"],
                    "rules": [
                        "Mock Prerequisite Rule",
                        "Mock Corequisite Rule",
                        "Mock Major Restriction",
                        "Mock Permission Required Rule",
                    ],
                },
            ),
            DevSeedRecord(
                id=seed_uuid("dev-seed-record:mock-degree-audit-core"),
                seed_key="mock-degree-audit-core",
                label="Phase 3A mock degree audit source-data seed marker",
                payload={
                    "source_type": SourceType.MOCK.value,
                    "is_official": False,
                    "audit_edge_cases": [
                        "retake",
                        "in_progress",
                        "planned",
                        "approved_transfer",
                        "pending_transfer",
                        "approved_waiver",
                        "approved_substitution",
                        "manual_review",
                    ],
                },
            ),
            DevSeedRecord(
                id=seed_uuid("dev-seed-record:mock-academic-scenarios"),
                seed_key="mock-academic-scenarios",
                label="Phase 3B mock what-if scenarios source-data seed marker",
                payload={
                    "source_type": SourceType.MOCK.value,
                    "is_official": False,
                    "programs": [
                        "Mock Accounting Minor",
                        "Mock Economics Minor",
                        "Mock BS Actuarial Analytics",
                        "Mock Data Literacy Certificate",
                        "Mock BS Management",
                        "Mock Finance Analytics Concentration",
                    ],
                    "combination_rules": [
                        "directional",
                        "maximum_shared_credits",
                        "minimum_unique_secondary_credits",
                        "missing_second_major_rule",
                    ],
                },
            ),
        ],
    )
    session.commit()


def main() -> None:
    with SessionLocal() as session:
        seed_mock_data(session)


if __name__ == "__main__":
    main()
