"""Synthetic regression evidence; no real student or school rules are included."""

from copy import deepcopy
from decimal import Decimal
from typing import Never
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import (
    AcademicTerm,
    AuditMode,
    Course,
    CourseEquivalency,
    ImportedRecordReview,
    ImportedRecordReviewDecision,
    ProgramVersion,
    RequirementCourseOption,
    RequirementEvaluationStatus,
    RequirementNode,
    SourceType,
    StudentAcademicProgram,
    StudentProfile,
)
from app.seed_dev import seed_uuid
from app.services.academic_workflow import academic_workflow
from app.services.data_review.engine import DataReviewApplicationService
from app.services.degree_audit.allocator import AuditAllocator
from app.services.degree_audit.engine import (
    DegreeAuditEngine,
)
from app.services.reviewed_rules.contracts import CourseDefinition, RequirementRule
from app.services.reviewed_rules.resolution import (
    resolve_for_program_version,
    reviewed_requirement_view,
)
from tests.test_data_reviews import create_catalog_import, create_section_import
from tests.test_data_reviews import session as seeded_session
from tests.test_reviewed_rules_integration import _catalog_context, _rule_set

# Reuse the existing synthetic fixture without redefining its setup.
session = seeded_session


def real_student(session: Session) -> StudentProfile:
    student = session.get(StudentProfile, seed_uuid("student-profile:mock-student"))
    assert student is not None
    student.source_type = SourceType.STUDENT_PROVIDED
    session.commit()
    return student


def apply_import(session: Session, run_id: UUID) -> UUID:
    service = DataReviewApplicationService(session)
    review = service.create_review_session(
        data_import_run_id=run_id, reviewer_label="Synthetic review"
    )
    for record in session.scalars(
        select(ImportedRecordReview).where(ImportedRecordReview.review_session_id == review.id)
    ).all():
        service.update_record_review(
            review_session_id=review.id,
            record_review_id=record.id,
            decision=ImportedRecordReviewDecision.CONFIRMED,
        )
    service.apply_review_session(review.id, dry_run=False)
    return review.id


def test_candidates_require_apply_and_remain_student_scoped(session: Session) -> None:
    student = real_student(session)
    run = create_catalog_import(session, "MATH*1044", title="Synthetic Mathematics")
    assert academic_workflow(session, student).courses == []
    review_id = apply_import(session, run)
    result = academic_workflow(session, student)
    assert [course.code for course in result.courses] == ["MATH 1044"]
    assert result.courses[0].source.source_type == "BROWSER_EXTENSION"
    assert result.courses[0].source.is_official is False
    assert result.programs == [] and result.terms == []
    DataReviewApplicationService(session).apply_review_session(review_id, dry_run=False)
    assert academic_workflow(session, student) == result
    other = StudentProfile(
        id=uuid4(),
        home_institution_id=student.home_institution_id,
        home_campus_id=student.home_campus_id,
        external_ref="synthetic-other",
        display_name="Synthetic other",
        source_type=SourceType.STUDENT_PROVIDED,
        is_official=False,
    )
    session.add(other)
    session.commit()
    assert academic_workflow(session, other).courses == []
    # Reopening a DB session uses persisted evidence, not process memory.
    session.expire_all()
    assert academic_workflow(session, student).revision == result.revision


def test_mock_profile_and_mock_program_never_become_real_candidates(session: Session) -> None:
    student = session.get(StudentProfile, seed_uuid("student-profile:mock-student"))
    assert student is not None
    assert academic_workflow(session, student).issues[0].reason_code == "DEMO_PROFILE"
    student = real_student(session)
    result = academic_workflow(session, student)
    assert not result.programs and not result.courses and not result.terms


def test_reviewed_sections_supply_real_terms_and_cancelled_sections_are_explained(
    session: Session,
) -> None:
    student = real_student(session)
    apply_import(session, create_catalog_import(session))
    term = session.get(AcademicTerm, seed_uuid("term:2024-fall"))
    assert term is not None
    term.source_type = SourceType.IMPORTED
    term.source_reference = "fixture://synthetic-reviewed-term"
    session.commit()
    apply_import(session, create_section_import(session, course_code="ACCT 2200"))
    result = academic_workflow(session, student)
    assert result.section_ids
    assert [item.id for item in result.terms] == [term.id]
    from app.models.academic import Section, SectionStatus

    section = session.get(Section, result.section_ids[0])
    assert section is not None
    section.status = SectionStatus.CANCELLED
    session.commit()
    updated = academic_workflow(session, student)
    assert updated.section_ids == []
    assert any("SECTION_CANCELLED" in item.message for item in updated.issues)


def test_program_requires_exact_active_reviewed_rules(session: Session) -> None:
    student = real_student(session)
    institution, program, version = _catalog_context(session)
    program.source_type = version.source_type = SourceType.IMPORTED
    assignment = session.scalar(
        select(StudentAcademicProgram).where(
            StudentAcademicProgram.student_profile_id == student.id,
            StudentAcademicProgram.program_version_id == version.id,
        )
    )
    assert assignment is not None
    assignment.source_type = SourceType.IMPORTED
    record, _ = _rule_set(institution, program, version, courses=[], requirements=[])
    session.add(record)
    session.commit()
    assert academic_workflow(session, student).programs == []
    payload = deepcopy(record.payload)
    payload["requirements"] = [
        RequirementRule(
            rule_id="synthetic",
            name="Synthetic credits",
            operator="MINIMUM_CREDITS",
            minimum_credits=Decimal("3"),
        ).model_dump(mode="json")
    ]
    record.payload = payload
    session.commit()
    assert [item.id for item in academic_workflow(session, student).programs] == [version.id]
    record.reviewer_confirmed = False
    session.commit()
    assert academic_workflow(session, student).programs == []
    assert resolve_for_program_version(session, version.id).state.value == "MISSING"


def test_rule_payload_catalog_tampering_is_not_active(session: Session) -> None:
    institution, program, version = _catalog_context(session)
    record, _ = _rule_set(institution, program, version, courses=[], requirements=[])
    payload = deepcopy(record.payload)
    payload["source"]["catalog_year"] = "different-year"
    record.payload = payload
    session.add(record)
    session.commit()
    assert resolve_for_program_version(session, version.id).state.value == "MISSING"


def test_real_audit_without_complete_history_or_reviewed_rules_requires_review(
    session: Session,
) -> None:
    student = real_student(session)
    version = session.get(ProgramVersion, seed_uuid("program-version:bs-finance-2024"))
    assert version is not None
    audit = DegreeAuditEngine(session).evaluate(student.id, version.id, AuditMode.CURRENT)
    assert audit.requirements
    assert all(
        item.status is RequirementEvaluationStatus.MANUAL_REVIEW_REQUIRED
        for item in audit.requirements
    )
    assert all(not item.applications for item in audit.requirements)
    assert audit.completed_credits == Decimal("0")
    assert audit.in_progress_credits == Decimal("0")
    assert audit.planned_credits == Decimal("0")


def test_reviewed_course_reference_normalizes_asterisk(session: Session) -> None:
    institution, program, version = _catalog_context(session)
    course = session.get(Course, seed_uuid("course:FIN-300"))
    assert course is not None
    node = session.scalar(
        select(RequirementNode).where(RequirementNode.program_version_id == version.id)
    )
    assert node is not None
    option = RequirementCourseOption(
        id=uuid4(), requirement_node_id=node.id, course_id=course.id, display_order=0
    )
    _, rules = _rule_set(
        institution,
        program,
        version,
        courses=[
            CourseDefinition(
                course_id="source-fin",
                code="FIN*300",
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
                course_ids=["source-fin"],
            )
        ],
    )
    _, options, warnings = reviewed_requirement_view(rules, [node], [option], [course])
    assert not warnings and options[0].course_id == course.id


def test_repeated_attempts_cannot_satisfy_two_exclusive_requirements(session: Session) -> None:
    context = DegreeAuditEngine(session)._load_context(
        seed_uuid("student-profile:mock-student"),
        seed_uuid("program-version:bs-finance-2024"),
        AuditMode.CURRENT,
    )
    course_id = seed_uuid("course:ACC-101")
    attempts = context.attempts_by_course[course_id]
    assert len(attempts) >= 2
    source_ids = {
        item.source_key
        for item in context.course_candidates(
            next(iter(context.nodes_by_id.values())), course_id, None
        )
    }
    assert len(source_ids) == 1
    allocator = AuditAllocator()
    key = next(iter(source_ids))
    allocator.reserve(key, allows_overlap=False)
    assert not any(
        allocator.is_available(item.source_key, allows_overlap=False)
        for item in context.course_candidates(
            next(iter(context.nodes_by_id.values())), course_id, None
        )
    )


def test_equivalent_courses_share_one_credit_identity(session: Session) -> None:
    context = DegreeAuditEngine(session)._load_context(
        seed_uuid("student-profile:mock-student"),
        seed_uuid("program-version:bs-finance-2024"),
        AuditMode.PROJECTED,
    )
    first, second = seed_uuid("course:ACC-101"), seed_uuid("course:FIN-300")
    context.equivalencies_by_equivalent[second] = [
        CourseEquivalency(id=uuid4(), source_course_id=first, equivalent_course_id=second)
    ]
    assert context.credit_identity(first) == context.credit_identity(second)
    before = context.credit_summary()
    assert before[0] >= Decimal("0")
    # The same source represented under two requirement alternatives is counted once.
    candidates = context.course_candidates(next(iter(context.nodes_by_id.values())), first, None)
    from app.services.degree_audit.engine import select_distinct_candidates

    assert (
        len(
            select_distinct_candidates(
                candidates + candidates, AuditAllocator(), allows_overlap=True
            )
        )
        == 1
    )


def test_credit_group_cannot_count_a_course_reserved_by_another_requirement(
    session: Session,
) -> None:
    from copy import copy

    from app.models.academic import RequirementType
    from app.services.degree_audit.engine import MinimumCreditsEvaluator

    context = DegreeAuditEngine(session)._load_context(
        seed_uuid("student-profile:mock-student"),
        seed_uuid("program-version:bs-finance-2024"),
        AuditMode.CURRENT,
    )
    course_id = seed_uuid("course:ACC-101")
    context.attempts_by_course = {course_id: context.attempts_by_course[course_id]}
    context.transfers_by_course = {}
    node = copy(next(iter(context.nodes_by_id.values())))
    node.requirement_type = RequirementType.MINIMUM_CREDITS
    node.minimum_credits = Decimal("3")
    node.minimum_grade = None
    node.allows_overlap = False
    allocator = AuditAllocator()
    allocator.reserve(context.credit_identity(course_id), allows_overlap=False)

    def unexpected_child(_: object) -> Never:
        raise AssertionError("Minimum credit nodes have no children")

    result = MinimumCreditsEvaluator().evaluate(node, context, unexpected_child, allocator)
    assert result.satisfied_credits == Decimal("0")
    assert result.applications == []
    assert result.status is not RequirementEvaluationStatus.SATISFIED


def test_invalid_rule_payload_requires_review_instead_of_crashing(session: Session) -> None:
    institution, program, version = _catalog_context(session)
    record, _ = _rule_set(institution, program, version, courses=[], requirements=[])
    record.payload = {"source": "invalid synthetic payload"}
    session.add(record)
    session.commit()
    assert resolve_for_program_version(session, version.id).state.value == "MISSING"


def test_real_planner_does_not_treat_mock_sections_as_offering_evidence(session: Session) -> None:
    from app.services.academic_planner.engine import AcademicPlannerApplicationService

    course = session.get(Course, seed_uuid("course:FIN-300"))
    term = session.get(AcademicTerm, seed_uuid("term:2024-fall"))
    assert course is not None and term is not None
    course.source_type = SourceType.IMPORTED
    session.commit()
    warnings = AcademicPlannerApplicationService(session)._availability_warnings(
        course, term, uuid4()
    )
    assert [warning.warning_code for warning in warnings] == ["COURSE_OFFERING_PATTERN_UNKNOWN"]


def test_real_review_apply_candidates_and_audit_round_trip(session: Session) -> None:
    from app.services.course_state.engine import active_course_state_snapshot
    from app.services.degree_audit.persistence import DegreeAuditApplicationService
    from tests.test_data_reviews import (
        create_myprogress_import,
        mark_finance_program_identity_as_reviewed,
        myprogress_course_row,
    )

    student = real_student(session)
    mark_finance_program_identity_as_reviewed(session)
    institution, program, version = _catalog_context(session)
    course = session.get(Course, seed_uuid("course:FIN-300"))
    term = session.get(AcademicTerm, seed_uuid("term:2024-fall"))
    node = session.scalar(
        select(RequirementNode).where(
            RequirementNode.program_version_id == version.id,
            RequirementNode.parent_id.is_(None),
        )
    )
    assert course is not None and term is not None and node is not None
    course.source_type = term.source_type = SourceType.IMPORTED
    course.source_reference = term.source_reference = "fixture://synthetic-reviewed"
    record, _ = _rule_set(
        institution,
        program,
        version,
        courses=[],
        requirements=[
            RequirementRule(
                rule_id=node.code,
                name="Synthetic credit requirement",
                operator="TOTAL_CREDITS",
                minimum_credits=Decimal("3"),
            )
        ],
    )
    session.add(record)
    session.commit()
    apply_import(
        session,
        create_myprogress_import(
            session,
            [
                myprogress_course_row(
                    1, course_code="FIN 300", title=course.title, status="COMPLETED", term="2024FA"
                )
            ],
        ),
    )
    snapshot = active_course_state_snapshot(session, student.id)
    assert snapshot is not None and snapshot.program_mapping_state == "EXACT"
    candidates = academic_workflow(session, student)
    assert [item.id for item in candidates.programs] == [version.id]
    assert [item.id for item in candidates.courses] == [course.id]
    assert [item.id for item in candidates.terms] == [term.id]
    run = DegreeAuditApplicationService(session).create_audit(
        student.id, version.id, AuditMode.CURRENT
    )
    assert run.completed_credits == Decimal("3")
    assert run.planned_credits == Decimal("0")
    assert run.reviewed_rule_set_id == record.id
    session.expire_all()
    from app.models.academic import DegreeAuditRun, RequirementEvaluation

    stored = session.get(DegreeAuditRun, run.id)
    assert stored is not None and stored.completed_credits == Decimal("3")
    evaluations = session.scalars(
        select(RequirementEvaluation).where(RequirementEvaluation.degree_audit_run_id == run.id)
    ).all()
    assert evaluations and all(
        item.status is RequirementEvaluationStatus.SATISFIED for item in evaluations
    )
    snapshot.program_mapping_state = "PROGRAM_IDENTITY_CONFLICT"
    session.commit()
    blocked = DegreeAuditEngine(session).evaluate(student.id, version.id, AuditMode.CURRENT)
    assert all(
        item.status is RequirementEvaluationStatus.MANUAL_REVIEW_REQUIRED
        for item in blocked.requirements
    )


def test_planner_consumes_reviewed_options_and_preserves_zero_credit_override(
    session: Session,
) -> None:
    from app.models.academic import AcademicPlanningMode
    from app.services.academic_planner.engine import AcademicPlannerApplicationService

    institution, program, version = _catalog_context(session)
    node = session.scalar(
        select(RequirementNode).where(
            RequirementNode.program_version_id == version.id,
            RequirementNode.parent_id.is_(None),
        )
    )
    assert node is not None
    wanted, excluded = seed_uuid("course:FIN-450"), seed_uuid("course:FIN-400")
    for index, course_id in enumerate([wanted, excluded]):
        session.add(
            RequirementCourseOption(
                id=uuid4(),
                institution_id=institution.id,
                program_version_id=version.id,
                requirement_node_id=node.id,
                course_id=course_id,
                display_order=index,
                credits_override=None,
                source_type=SourceType.MOCK,
                is_official=False,
                source_reference="fixture://synthetic-reviewed-options",
            )
        )
    record, _ = _rule_set(
        institution,
        program,
        version,
        courses=[],
        requirements=[
            RequirementRule(
                rule_id=node.code,
                name="Reviewed one-course choice",
                operator="CHOOSE_N",
                choose_n=1,
                course_ids=[str(wanted)],
            )
        ],
    )
    session.add(record)
    session.commit()
    audit = DegreeAuditEngine(session).evaluate(
        seed_uuid("student-profile:mock-student"), version.id, AuditMode.CURRENT
    )
    candidates, _ = AcademicPlannerApplicationService(session)._planner_candidates(
        audit, version, AcademicPlanningMode.CURRENT_PROGRAM
    )
    assert [item.course.id for item in candidates] == [wanted]
    assert candidates[0].requirement_node.choose_n == 1
    # Zero is a valid advisory value even though persisted options currently require > 0.
    from dataclasses import replace

    advisory = replace(
        candidates[0], course_option=RequirementCourseOption(credits_override=Decimal("0"))
    )
    assert advisory.credits == Decimal("0")
