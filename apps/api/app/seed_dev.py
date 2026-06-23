from __future__ import annotations

from collections.abc import Iterable
from datetime import date
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
    CourseSubstitution,
    CourseWaiver,
    DegreeLevel,
    Institution,
    ProgramType,
    ProgramVersion,
    RequirementCourseOption,
    RequirementNode,
    RequirementType,
    SourceType,
    StudentAcademicProgram,
    StudentAcademicProgramStatus,
    StudentCourseAttempt,
    StudentCourseAttemptStatus,
    StudentProfile,
    StudentProgramType,
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
) -> RequirementNode:
    return RequirementNode(
        id=seed_uuid(f"requirement-node:{code}"),
        institution_id=seed_uuid("institution:mock-university"),
        program_version_id=seed_uuid("program-version:bs-finance-2024"),
        parent_id=seed_uuid(f"requirement-node:{parent_code}") if parent_code else None,
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
) -> RequirementCourseOption:
    return RequirementCourseOption(
        id=seed_uuid(f"requirement-option:{node_code}:{subject_code}-{course_number}"),
        institution_id=seed_uuid("institution:mock-university"),
        program_version_id=seed_uuid("program-version:bs-finance-2024"),
        requirement_node_id=seed_uuid(f"requirement-node:{node_code}"),
        course_id=seed_uuid(f"course:{subject_code}-{course_number}"),
        display_order=display_order,
        minimum_grade=minimum_grade,
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
    merge_all(session, [finance_program])
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
    merge_all(session, [finance_version])
    session.flush()

    courses = [
        course("GEN", "101", "Mock General Education Seminar", level=100),
        course("BUS", "101", "Mock Business Foundations", level=100),
        course("ACC", "101", "Mock Accounting Foundations", level=100),
        course("FIN", "201", "Mock Finance Transfer Equivalent", level=200),
        course("FIN", "301", "Mock Corporate Finance", level=300),
        course("FIN", "401", "Mock Investments", level=400),
        course("FIN", "402", "Mock Risk Management", level=400),
        course("FIN", "403", "Mock International Finance", level=400),
        course("ELEC", "100", "Mock Free Elective", level=100),
    ]
    merge_all(session, courses)
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
    ]
    merge_all(session, child_nodes)
    session.flush()

    requirement_options = [
        requirement_option("BUS-REQ-A", "BUS", "101", display_order=10, minimum_grade="C"),
        requirement_option("BUS-REQ-B", "ACC", "101", display_order=10, minimum_grade="C"),
        requirement_option("FIN-REQ", "FIN", "301", display_order=10, minimum_grade="C"),
        requirement_option("FIN-ELECTIVES", "FIN", "401", display_order=10, minimum_grade="C"),
        requirement_option("FIN-ELECTIVES", "FIN", "402", display_order=20, minimum_grade="C"),
        requirement_option("FIN-ELECTIVES", "FIN", "403", display_order=30, minimum_grade="C"),
    ]
    merge_all(session, requirement_options)
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
    ]
    merge_all(session, attempts)
    session.flush()

    transfer_credit = TransferCredit(
        id=seed_uuid("transfer-credit:mock-student-gen-101"),
        student_profile_id=student.id,
        equivalent_course_id=seed_uuid("course:GEN-101"),
        source_institution_name="Mock Transfer College",
        source_course_code="MTC 100",
        credits_earned=Decimal("3.0"),
        grade="TA",
        status=ApprovalStatus.APPROVED,
        **mock_source(),
    )
    course_waiver = CourseWaiver(
        id=seed_uuid("course-waiver:mock-student-general-ed"),
        institution_id=institution.id,
        student_profile_id=student.id,
        program_version_id=finance_version.id,
        requirement_node_id=seed_uuid("requirement-node:GENERAL-ED"),
        status=ApprovalStatus.PENDING,
        reason="Mock pending waiver. It must not be applied by Phase 2A.",
        **mock_source(),
    )
    substitution = CourseSubstitution(
        id=seed_uuid("course-substitution:mock-student-fin-elective"),
        institution_id=institution.id,
        student_profile_id=student.id,
        program_version_id=finance_version.id,
        requirement_node_id=seed_uuid("requirement-node:FIN-ELECTIVES"),
        original_course_id=seed_uuid("course:FIN-401"),
        substitute_course_id=seed_uuid("course:FIN-402"),
        status=ApprovalStatus.REJECTED,
        reason="Mock rejected substitution. It must not be applied by Phase 2A.",
        **mock_source(),
    )
    merge_all(session, [transfer_credit, course_waiver, substitution])
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
        ],
    )
    session.commit()


def main() -> None:
    with SessionLocal() as session:
        seed_mock_data(session)


if __name__ == "__main__":
    main()
