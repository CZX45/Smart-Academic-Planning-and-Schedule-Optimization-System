from collections.abc import Generator, Sequence
from typing import Any, cast

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base, DevSeedRecord
from app.models.academic import (
    AcademicProgram,
    AcademicTerm,
    AuditCourseApplication,
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
    DegreeAuditRun,
    DegreeAuditWarning,
    Institution,
    ProgramCombinationRule,
    ProgramType,
    ProgramVersion,
    RequirementCourseOption,
    RequirementEvaluation,
    RequirementNode,
    Section,
    SectionMeeting,
    SectionModality,
    SectionStatus,
    SourceType,
    StudentAcademicProgram,
    StudentCourseAttempt,
    StudentProfile,
    TransferCredit,
)
from app.seed_dev import seed_mock_data

SEEDED_MODELS = [
    DevSeedRecord,
    Institution,
    Campus,
    AcademicTerm,
    AcademicProgram,
    ProgramVersion,
    Course,
    CourseEquivalency,
    CourseOfferingPattern,
    Section,
    SectionMeeting,
    CourseRule,
    CourseRuleExpression,
    RequirementNode,
    RequirementCourseOption,
    StudentProfile,
    StudentAcademicProgram,
    StudentCourseAttempt,
    TransferCredit,
    CourseWaiver,
    CourseSubstitution,
    ProgramCombinationRule,
]

AUDIT_SNAPSHOT_MODELS = [
    DegreeAuditRun,
    RequirementEvaluation,
    AuditCourseApplication,
    DegreeAuditWarning,
]


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


def table_counts(session: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    for model in SEEDED_MODELS:
        counts[model.__tablename__] = session.scalar(select(func.count()).select_from(model)) or 0
    for model in AUDIT_SNAPSHOT_MODELS:
        counts[model.__tablename__] = session.scalar(select(func.count()).select_from(model)) or 0
    return counts


def test_mock_seed_is_idempotent(session: Session) -> None:
    seed_mock_data(session)
    first_counts = table_counts(session)

    seed_mock_data(session)
    second_counts = table_counts(session)

    assert first_counts == second_counts
    assert first_counts["institutions"] == 1
    assert first_counts["student_course_attempts"] >= 2
    assert first_counts["sections"] >= 3
    assert first_counts["course_rules"] >= 4
    assert first_counts["degree_audit_runs"] == 0


def test_seeded_academic_data_is_mock_and_not_official(session: Session) -> None:
    seed_mock_data(session)

    for model in SEEDED_MODELS:
        if model is DevSeedRecord:
            continue
        records = cast(Sequence[Any], session.scalars(select(model)).all())
        assert records, f"{model.__tablename__} should be seeded"
        assert all(record.source_type is SourceType.MOCK for record in records)
        assert all(record.is_official is False for record in records)


def test_mock_finance_requirement_tree_shape(session: Session) -> None:
    seed_mock_data(session)

    version = session.scalar(select(ProgramVersion).where(ProgramVersion.catalog_year == "2024"))
    assert version is not None

    nodes = session.scalars(
        select(RequirementNode)
        .where(RequirementNode.program_version_id == version.id)
        .order_by(RequirementNode.display_order)
    ).all()
    names = {node.name for node in nodes}
    assert {
        "Mock BS Finance",
        "Total Credits",
        "General Education",
        "Transferred General Education Course",
        "Approved Waiver Demonstration",
        "Business Core",
        "Required Course A",
        "Required Course B",
        "Finance Major",
        "Required Finance Course",
        "Choose 2 from 3 Finance Electives",
        "Approved Substitution Demonstration",
        "Upper-Level Finance Credits",
        "Mock Residency Credits",
        "Manual Review Configuration Example",
        "Free Electives",
    }.issubset(names)

    finance_electives = next(
        node for node in nodes if node.name == "Choose 2 from 3 Finance Electives"
    )
    assert finance_electives.choose_n == 2
    option_count = session.scalar(
        select(func.count())
        .select_from(RequirementCourseOption)
        .where(RequirementCourseOption.requirement_node_id == finance_electives.id)
    )
    assert option_count == 3


def test_mock_phase_3a_audit_seed_covers_student_record_edge_cases(session: Session) -> None:
    seed_mock_data(session)

    attempts = session.scalars(select(StudentCourseAttempt)).all()
    assert {attempt.status.value for attempt in attempts}.issuperset(
        {"COMPLETED", "IN_PROGRESS", "PLANNED"}
    )
    assert any(attempt.is_repeat for attempt in attempts)
    assert any(attempt.grade == "D" for attempt in attempts)

    transfers = session.scalars(select(TransferCredit)).all()
    assert {transfer.status.value for transfer in transfers}.issuperset({"APPROVED", "PENDING"})

    waivers = session.scalars(select(CourseWaiver)).all()
    assert {waiver.status.value for waiver in waivers}.issuperset({"APPROVED", "PENDING"})

    substitutions = session.scalars(select(CourseSubstitution)).all()
    assert {substitution.status.value for substitution in substitutions}.issuperset(
        {"APPROVED", "REJECTED"}
    )


def test_mock_phase_3b_programs_and_combination_rules_are_seeded(session: Session) -> None:
    seed_mock_data(session)

    program_rows = session.execute(
        select(AcademicProgram, ProgramVersion).join(ProgramVersion)
    ).all()
    programs_by_code = {program.code: (program, version) for program, version in program_rows}
    assert {
        "BSFIN",
        "MINACCT",
        "MINECON",
        "BSZACT",
        "CERTDATA",
        "BSMGMT",
    }.issubset(programs_by_code)
    assert programs_by_code["MINACCT"][0].program_type is ProgramType.MINOR
    assert programs_by_code["CERTDATA"][0].program_type is ProgramType.CERTIFICATE

    rules = session.scalars(select(ProgramCombinationRule)).all()
    assert rules
    assert all(rule.source_type is SourceType.MOCK for rule in rules)
    assert all(rule.is_official is False for rule in rules)
    assert any(
        rule.primary_program_version_id == programs_by_code["BSFIN"][1].id
        and rule.secondary_program_version_id == programs_by_code["MINACCT"][1].id
        and rule.maximum_shared_credits == 3
        and rule.minimum_unique_secondary_credits == 6
        and rule.allows_double_counting
        for rule in rules
    )
    assert not any(
        rule.primary_program_version_id == programs_by_code["BSFIN"][1].id
        and rule.secondary_program_version_id == programs_by_code["BSZACT"][1].id
        for rule in rules
    )


def test_mock_phase_2b_sections_rules_and_offering_patterns(session: Session) -> None:
    seed_mock_data(session)

    sections = session.scalars(select(Section)).all()
    assert sections
    assert all(section.source_type is SourceType.MOCK for section in sections)
    assert all(section.is_official is False for section in sections)
    assert {section.modality.value for section in sections}.issuperset(
        {"IN_PERSON", "ONLINE_ASYNCHRONOUS", "HYBRID"}
    )

    meetings = session.scalars(select(SectionMeeting)).all()
    assert {meeting.meeting_type.value for meeting in meetings}.issuperset({"LECTURE", "LAB"})

    patterns = session.scalars(select(CourseOfferingPattern)).all()
    assert patterns
    assert all(pattern.source_type is SourceType.MOCK for pattern in patterns)
    assert all(pattern.is_official is False for pattern in patterns)

    fin_300 = session.scalar(
        select(Course).where(Course.subject_code == "FIN", Course.course_number == "300")
    )
    assert fin_300 is not None
    prerequisite = session.scalar(
        select(CourseRule).where(
            CourseRule.course_id == fin_300.id,
            CourseRule.rule_type == CourseRuleType.PREREQUISITE,
        )
    )
    assert prerequisite is not None
    prereq_nodes = session.scalars(
        select(CourseRuleExpression).where(CourseRuleExpression.course_rule_id == prerequisite.id)
    ).all()
    assert {node.node_type for node in prereq_nodes} == {
        CourseRuleExpressionNodeType.AND,
        CourseRuleExpressionNodeType.COMPLETED_COURSE,
        CourseRuleExpressionNodeType.MINIMUM_GRADE,
    }

    fin_400 = session.scalar(
        select(Course).where(Course.subject_code == "FIN", Course.course_number == "400")
    )
    assert fin_400 is not None
    corequisite = session.scalar(
        select(CourseRule).where(
            CourseRule.course_id == fin_400.id,
            CourseRule.rule_type == CourseRuleType.COREQUISITE,
        )
    )
    assert corequisite is not None


def test_mock_phase_6b_schedule_seed_cases_are_available(session: Session) -> None:
    seed_mock_data(session)

    seed_marker = session.scalar(
        select(DevSeedRecord).where(DevSeedRecord.seed_key == "mock-semester-schedule")
    )
    assert seed_marker is not None
    assert seed_marker.payload["source_type"] == "MOCK"
    assert seed_marker.payload["is_official"] is False
    assert "near-duplicate sections for diversity ranking" in seed_marker.payload["schedule_cases"]

    fin_300 = session.scalar(
        select(Course).where(Course.subject_code == "FIN", Course.course_number == "300")
    )
    fin_403 = session.scalar(
        select(Course).where(Course.subject_code == "FIN", Course.course_number == "403")
    )
    assert fin_300 is not None
    assert fin_403 is not None

    fin_300_sections = session.scalars(
        select(Section).where(Section.course_id == fin_300.id).order_by(Section.section_code)
    ).all()
    assert {section.section_code for section in fin_300_sections}.issuperset(
        {"001", "002", "AFT", "WEB"}
    )
    assert all(section.source_type is SourceType.MOCK for section in fin_300_sections)
    assert all(section.is_official is False for section in fin_300_sections)

    online_fin_403 = session.scalar(
        select(Section).where(
            Section.course_id == fin_403.id,
            Section.modality == SectionModality.ONLINE_SYNCHRONOUS,
        )
    )
    assert online_fin_403 is not None

    afternoon_meetings = session.scalars(
        select(SectionMeeting)
        .join(Section, SectionMeeting.section_id == Section.id)
        .where(
            Section.course_id == fin_300.id,
            Section.section_code == "AFT",
        )
    ).all()
    assert {meeting.day_of_week for meeting in afternoon_meetings} == {
        DayOfWeek.TUESDAY,
        DayOfWeek.THURSDAY,
    }
    assert all(
        meeting.start_time is not None and meeting.start_time.hour >= 13
        for meeting in afternoon_meetings
    )


def test_mock_phase_5a_planner_seed_cases_are_available(session: Session) -> None:
    seed_mock_data(session)

    seed_marker = session.scalar(
        select(DevSeedRecord).where(DevSeedRecord.seed_key == "mock-academic-planner")
    )
    assert seed_marker is not None
    assert seed_marker.payload["source_type"] == "MOCK"
    assert seed_marker.payload["is_official"] is False

    fin_400 = session.scalar(
        select(Course).where(Course.subject_code == "FIN", Course.course_number == "400")
    )
    fin_403 = session.scalar(
        select(Course).where(Course.subject_code == "FIN", Course.course_number == "403")
    )
    fin_450 = session.scalar(
        select(Course).where(Course.subject_code == "FIN", Course.course_number == "450")
    )
    assert fin_400 is not None
    assert fin_403 is not None
    assert fin_450 is not None

    assert session.scalar(
        select(CourseOfferingPattern).where(CourseOfferingPattern.course_id == fin_400.id)
    )
    assert (
        session.scalar(
            select(CourseOfferingPattern).where(CourseOfferingPattern.course_id == fin_403.id)
        )
        is None
    )

    closed_section = session.scalar(
        select(Section).where(
            Section.course_id
            == session.scalar(
                select(Course.id).where(
                    Course.subject_code == "FREE",
                    Course.course_number == "100",
                )
            ),
            Section.status == SectionStatus.CLOSED,
        )
    )
    assert closed_section is not None

    blocked_rule = session.scalar(
        select(CourseRule).where(
            CourseRule.course_id == fin_450.id,
            CourseRule.rule_type == CourseRuleType.PREREQUISITE,
        )
    )
    assert blocked_rule is not None
    blocked_expression = session.scalar(
        select(CourseRuleExpression).where(CourseRuleExpression.course_rule_id == blocked_rule.id)
    )
    assert blocked_expression is not None

    accounting_minor = session.scalar(
        select(AcademicProgram).where(AcademicProgram.code == "MINACCT")
    )
    assert accounting_minor is not None
    assert accounting_minor.program_type is ProgramType.MINOR
