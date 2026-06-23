from collections.abc import Generator
from datetime import date
from decimal import Decimal
from typing import Any, cast
from uuid import NAMESPACE_URL, UUID, uuid5

import pytest
from sqlalchemy import Table, UniqueConstraint, create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.academic import (
    AcademicProgram,
    AcademicTerm,
    ApprovalStatus,
    Campus,
    Course,
    CourseEquivalency,
    CourseSubstitution,
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
