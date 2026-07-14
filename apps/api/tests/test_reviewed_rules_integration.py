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
    EligibilityMode,
    EligibilityOverallResult,
    Institution,
    ProgramVersion,
    RequirementNode,
    StudentProfile,
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
