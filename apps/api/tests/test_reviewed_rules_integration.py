from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1.academic import eligibility_check_response
from app.db.base import Base
from app.models.academic import (
    AcademicProgram,
    AcademicTerm,
    AuditMode,
    Course,
    DegreeAuditWarning,
    EligibilityMode,
    EligibilityOverallResult,
    Institution,
    ProgramVersion,
    RequirementCourseOption,
    RequirementEvaluation,
    RequirementNode,
    SourceType,
    StudentAcademicProgram,
    StudentAcademicProgramStatus,
    StudentProfile,
    StudentProgramType,
)
from app.models.reviewed_rules import ReviewedRuleSetRecord
from app.seed_dev import seed_mock_data
from app.services.course_eligibility.engine import CourseEligibilityApplicationService
from app.services.degree_audit.persistence import DegreeAuditApplicationService
from app.services.reviewed_rules.contracts import (
    CatalogRuleSet,
    CourseDefinition,
    RequirementRule,
    RuleLifecycle,
    RuleSource,
)
from app.services.reviewed_rules.resolution import resolve_for_student


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
        seed_mock_data(db)
        yield db


def _rule_set(
    institution: Institution,
    program: AcademicProgram,
    version: ProgramVersion,
    *,
    courses: list[CourseDefinition],
    requirements: list[RequirementRule],
) -> tuple[ReviewedRuleSetRecord, CatalogRuleSet]:
    rule_set_id = uuid4()
    source = RuleSource(
        institution_id=institution.code,
        program_id=program.code,
        program_name=program.name,
        degree=program.degree_level.value,
        major=program.code,
        catalog_year=version.catalog_year,
        effective_term="2024FA",
        source_type="SYNTHETIC_FIXTURE",
        source_title="Synthetic reviewed rule integration fixture",
        source_url_or_document_id="fixture://stage-10b/reviewed-rules",
        source_location="tests/test_reviewed_rules_integration.py",
        source_evidence="Synthetic fixture only; not official school policy.",
        imported_at=datetime.now(UTC),
    )
    payload = CatalogRuleSet(
        rule_set_id=rule_set_id,
        version=1,
        lifecycle=RuleLifecycle.ACTIVE,
        source=source,
        courses=courses,
        requirements=requirements,
        reviewer_confirmed=True,
        reviewed_at=datetime.now(UTC),
    )
    record = ReviewedRuleSetRecord(
        id=rule_set_id,
        institution_identifier=institution.code,
        program_identifier=program.code,
        catalog_year=version.catalog_year,
        version=1,
        lifecycle=RuleLifecycle.ACTIVE,
        source_title=source.source_title,
        source_location=source.source_location,
        source_evidence=source.source_evidence,
        payload=payload.model_dump(mode="json"),
        validation_state="VALID",
        validation_errors=[],
        validation_warnings=[],
        reviewer_confirmed=True,
        reviewed_at=payload.reviewed_at,
        activated_at=datetime.now(UTC),
    )
    return record, payload


def _catalog_context(session: Session) -> tuple[Institution, AcademicProgram, ProgramVersion]:
    institution = session.scalar(select(Institution).where(Institution.code == "MOCKU"))
    program = session.scalar(select(AcademicProgram).where(AcademicProgram.code == "BSFIN"))
    assert institution is not None
    assert program is not None
    version = session.scalar(
        select(ProgramVersion).where(
            ProgramVersion.program_id == program.id,
            ProgramVersion.catalog_year == "2024",
        )
    )
    assert version is not None
    return institution, program, version


def test_degree_audit_consumes_exact_active_reviewed_rules(session: Session) -> None:
    institution, program, version = _catalog_context(session)
    node = session.scalar(
        select(RequirementNode).where(RequirementNode.program_version_id == version.id)
    )
    course = session.scalar(select(Course).where(Course.subject_code == "FIN"))
    student = session.scalar(select(StudentProfile))
    assert node is not None
    assert course is not None
    assert student is not None

    record, _ = _rule_set(
        institution,
        program,
        version,
        courses=[
            CourseDefinition(
                course_id=str(course.id),
                code=f"{course.subject_code} {course.course_number}",
                title=course.title,
                credits_min=course.credits_min,
                credits_max=course.credits_max,
            )
        ],
        requirements=[
            RequirementRule(
                rule_id=node.code,
                name=node.name,
                operator="REQUIRED_COURSE",
                course_ids=[str(course.id)],
            )
        ],
    )
    session.add(record)
    session.commit()

    run = DegreeAuditApplicationService(session).create_audit(
        student.id,
        version.id,
        AuditMode.CURRENT,
    )

    assert run.reviewed_rule_set_id == record.id
    assert run.rule_resolution_state == "ACTIVE"
    assert run.rule_source_reference == "fixture://stage-10b/reviewed-rules"
    assert "active reviewed" in run.rule_resolution_explanation.lower()


def test_eligibility_consumes_reviewed_prerequisite_and_persists_explanation(
    session: Session,
) -> None:
    institution, program, version = _catalog_context(session)
    student = session.scalar(select(StudentProfile))
    target = session.scalar(
        select(Course).where(
            Course.subject_code == "FIN",
            Course.course_number == "300",
        )
    )
    prerequisite = session.scalar(
        select(Course).where(
            Course.subject_code == "BUS",
            Course.course_number == "101",
        )
    )
    term_id = session.scalar(select(AcademicTerm).where(AcademicTerm.term_code == "2024FA"))
    assert student is not None
    assert target is not None
    assert prerequisite is not None
    assert term_id is not None
    target_definition = CourseDefinition(
        course_id=str(target.id),
        code=f"{target.subject_code} {target.course_number}",
        title=target.title,
        credits_min=target.credits_min,
        credits_max=target.credits_max,
        prerequisite_ids=[str(prerequisite.id)],
    )
    prerequisite_definition = CourseDefinition(
        course_id=str(prerequisite.id),
        code=f"{prerequisite.subject_code} {prerequisite.course_number}",
        title=prerequisite.title,
        credits_min=prerequisite.credits_min,
        credits_max=prerequisite.credits_max,
    )
    record, _ = _rule_set(
        institution,
        program,
        version,
        courses=[target_definition, prerequisite_definition],
        requirements=[],
    )
    session.add(record)
    session.commit()

    run = CourseEligibilityApplicationService(session).create_check(
        student_profile_id=student.id,
        course_id=target.id,
        section_id=None,
        target_term_id=term_id.id,
        mode=EligibilityMode.CURRENT,
    )

    assert run.overall_result is EligibilityOverallResult.ELIGIBLE
    assert run.reviewed_rule_set_id == record.id
    assert run.rule_resolution_state == "ACTIVE"
    assert run.reviewed_rule_reasons
    assert run.reviewed_rule_reasons[0]["reviewed_rule_set_id"] == str(record.id)
    response = eligibility_check_response(run, session)
    assert response.reviewed_rule_reasons[0].rule_source_reference == (
        "fixture://stage-10b/reviewed-rules"
    )


def test_missing_reviewed_rules_keep_eligibility_unknown_when_definition_is_absent(
    session: Session,
) -> None:
    institution, program, version = _catalog_context(session)
    student = session.scalar(select(StudentProfile))
    target = session.scalar(select(Course).where(Course.subject_code == "FIN"))
    term = session.scalar(select(AcademicTerm).where(AcademicTerm.term_code == "2024FA"))
    assert student is not None
    assert target is not None
    assert term is not None
    record, _ = _rule_set(
        institution,
        program,
        version,
        courses=[],
        requirements=[],
    )
    session.add(record)
    session.commit()

    run = CourseEligibilityApplicationService(session).create_check(
        student_profile_id=student.id,
        course_id=target.id,
        section_id=None,
        target_term_id=term.id,
        mode=EligibilityMode.CURRENT,
    )

    assert run.overall_result is EligibilityOverallResult.UNKNOWN
    assert run.reviewed_rule_reasons[0]["reason_code"] == "REVIEWED_COURSE_RULE_MISSING"


def test_unmapped_reviewed_requirement_does_not_reuse_legacy_options(session: Session) -> None:
    institution, program, version = _catalog_context(session)
    node = session.scalar(
        select(RequirementNode).where(RequirementNode.program_version_id == version.id)
    )
    student = session.scalar(select(StudentProfile))
    course = session.scalar(select(Course).where(Course.subject_code == "FIN"))
    assert node is not None and student is not None and course is not None
    legacy_option = session.scalar(
        select(RequirementCourseOption).where(
            RequirementCourseOption.requirement_node_id == node.id
        )
    )
    assert legacy_option is not None
    record, _ = _rule_set(
        institution,
        program,
        version,
        courses=[],
        requirements=[
            RequirementRule(
                rule_id=node.code,
                name=node.name,
                operator="REQUIRED_COURSE",
                course_ids=["SYNTHETIC-UNMAPPED-999"],
            )
        ],
    )
    session.add(record)
    session.commit()

    run = DegreeAuditApplicationService(session).create_audit(
        student.id, version.id, AuditMode.CURRENT
    )

    assert run.rule_resolution_state == "ACTIVE"
    evaluation = session.scalar(
        select(RequirementEvaluation).where(RequirementEvaluation.degree_audit_run_id == run.id)
    )
    assert evaluation is not None
    assert evaluation.status.value != "SATISFIED"
    warnings = session.scalars(
        select(DegreeAuditWarning).where(DegreeAuditWarning.degree_audit_run_id == run.id)
    ).all()
    assert any("SYNTHETIC-UNMAPPED-999" in warning.message for warning in warnings)


def test_missing_reviewed_corequisite_is_conditional_and_survives_get_round_trip(
    session: Session,
) -> None:
    institution, program, version = _catalog_context(session)
    student = session.scalar(select(StudentProfile))
    target = session.scalar(
        select(Course).where(Course.subject_code == "FIN", Course.course_number == "400")
    )
    corequisite = session.scalar(
        select(Course).where(Course.subject_code == "FIN", Course.course_number == "401L")
    )
    term = session.scalar(select(AcademicTerm).where(AcademicTerm.term_code == "2024FA"))
    assert (
        student is not None and target is not None and corequisite is not None and term is not None
    )
    record, _ = _rule_set(
        institution,
        program,
        version,
        courses=[
            CourseDefinition(
                course_id=str(target.id),
                code=f"{target.subject_code} {target.course_number}",
                title=target.title,
                credits_min=target.credits_min,
                credits_max=target.credits_max,
                corequisite_ids=[str(corequisite.id)],
            ),
            CourseDefinition(
                course_id=str(corequisite.id),
                code=f"{corequisite.subject_code} {corequisite.course_number}",
                title=corequisite.title,
                credits_min=corequisite.credits_min,
                credits_max=corequisite.credits_max,
            ),
        ],
        requirements=[],
    )
    session.add(record)
    session.commit()

    run = CourseEligibilityApplicationService(session).create_check(
        student_profile_id=student.id,
        course_id=target.id,
        section_id=None,
        target_term_id=term.id,
        mode=EligibilityMode.CURRENT,
    )
    immediate = eligibility_check_response(run, session)
    assert run.overall_result is EligibilityOverallResult.CONDITIONALLY_ELIGIBLE
    assert immediate.corequisite_summary is not None
    assert immediate.corequisite_summary.must_enroll_concurrently == [corequisite.id]
    assert any(
        reason.reason_code == "REVIEWED_COREQUISITE_REQUIRED"
        and f"{corequisite.subject_code} {corequisite.course_number}" in reason.explanation
        for reason in immediate.reviewed_rule_reasons
    )

    session.expire_all()
    stored = session.get(type(run), run.id)
    assert stored is not None
    round_trip = eligibility_check_response(stored, session)
    assert round_trip.corequisite_summary == immediate.corequisite_summary
    assert round_trip.rule_source_reference == immediate.rule_source_reference


def test_program_resolution_prefers_primary_major_semantically(session: Session) -> None:
    institution, program, version = _catalog_context(session)
    minor_program = session.scalar(select(AcademicProgram).where(AcademicProgram.code == "MINACCT"))
    minor_version = (
        session.scalar(select(ProgramVersion).where(ProgramVersion.program_id == minor_program.id))
        if minor_program is not None
        else None
    )
    student = session.scalar(select(StudentProfile))
    assert (
        institution is not None
        and program is not None
        and version is not None
        and minor_program is not None
        and minor_version is not None
        and student is not None
    )
    session.add(
        StudentAcademicProgram(
            id=uuid4(),
            student_profile_id=student.id,
            program_version_id=minor_version.id,
            program_type=StudentProgramType.MINOR,
            status=StudentAcademicProgramStatus.ACTIVE,
            source_type=SourceType.MOCK,
            is_official=False,
        )
    )
    primary_record, _ = _rule_set(institution, program, version, courses=[], requirements=[])
    minor_record, _ = _rule_set(
        institution, minor_program, minor_version, courses=[], requirements=[]
    )
    session.add_all([primary_record, minor_record])
    session.commit()

    resolution = resolve_for_student(session, student.id)

    assert resolution.state.value == "ACTIVE"
    assert resolution.record is not None
    assert resolution.record.program_identifier == "BSFIN"
