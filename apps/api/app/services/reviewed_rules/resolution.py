from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import (
    AcademicProgram,
    Course,
    Institution,
    ProgramVersion,
    RequirementCourseOption,
    RequirementNode,
    RequirementType,
    StudentAcademicProgram,
    StudentAcademicProgramStatus,
    StudentProgramType,
)
from app.models.reviewed_rules import ReviewedRuleSetRecord
from app.services.reviewed_rules.contracts import CatalogRuleSet, RuleLifecycle


class RuleResolutionState(StrEnum):
    ACTIVE = "ACTIVE"
    MISSING = "MISSING"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class RuleResolution:
    state: RuleResolutionState
    record: ReviewedRuleSetRecord | None
    rule_set: CatalogRuleSet | None
    explanation: str


def reviewed_requirement_view(
    rule_set: CatalogRuleSet,
    nodes: list[RequirementNode],
    options: list[RequirementCourseOption],
    courses: list[Course],
) -> tuple[list[RequirementNode], list[RequirementCourseOption], list[str]]:
    """Overlay supported reviewed fields onto existing persisted audit nodes.

    RequirementEvaluation keeps its existing foreign keys, while the active
    reviewed payload controls the evaluated node set and course options.
    """

    nodes_by_code = {node.code: node for node in nodes}
    courses_by_identifier: dict[str, Course] = {str(course.id): course for course in courses}
    for course in courses:
        courses_by_identifier[f"{course.subject_code} {course.course_number}".upper()] = course
        courses_by_identifier[f"{course.subject_code}{course.course_number}".upper()] = course
    selected_nodes: list[RequirementNode] = []
    selected_options: list[RequirementCourseOption] = []
    warnings: list[str] = []
    options_by_node: dict[UUID, list[RequirementCourseOption]] = {}
    for option in options:
        options_by_node.setdefault(option.requirement_node_id, []).append(option)

    for rule in rule_set.requirements:
        node = nodes_by_code.get(rule.rule_id)
        if node is None:
            warnings.append(f"Reviewed rule {rule.rule_id} has no persisted requirement node.")
            continue
        try:
            requirement_type = RequirementType(rule.operator)
        except ValueError:
            warnings.append(
                f"Reviewed rule {rule.rule_id} uses unsupported operator {rule.operator}."
            )
            continue
        reviewed_node = copy(node)
        reviewed_node.name = rule.name
        reviewed_node.requirement_type = requirement_type
        reviewed_node.minimum_credits = rule.minimum_credits
        reviewed_node.minimum_grade = rule.minimum_grade
        reviewed_node.choose_n = rule.choose_n
        selected_nodes.append(reviewed_node)
        allowed_courses: set[UUID] = set()
        unresolved_identifiers: list[str] = []
        for course_identifier in rule.course_ids:
            matched_course = courses_by_identifier.get(course_identifier)
            if matched_course is None:
                matched_course = courses_by_identifier.get(course_identifier.upper())
            if matched_course is None:
                definition = next(
                    (
                        candidate
                        for candidate in rule_set.courses
                        if candidate.course_id == course_identifier
                    ),
                    None,
                )
                if definition is not None:
                    matched_course = courses_by_identifier.get(definition.code.upper())
                    if matched_course is None:
                        matched_course = courses_by_identifier.get(
                            definition.code.replace(" ", "").upper()
                        )
            if matched_course is None:
                unresolved_identifiers.append(course_identifier)
                continue
            allowed_courses.add(matched_course.id)
        if unresolved_identifiers:
            warnings.append(
                f"Reviewed rule {rule.rule_id} has unresolved course references "
                f"{', '.join(unresolved_identifiers)}; review is required and no persisted "
                "requirement options were reused."
            )
        for option in options_by_node.get(node.id, []):
            if not rule.course_ids or (
                not unresolved_identifiers and option.course_id in allowed_courses
            ):
                selected_options.append(copy(option))
    if not rule_set.requirements:
        warnings.append("The active reviewed rule set contains no supported requirements.")
    return selected_nodes, selected_options, warnings


def resolve_for_program_version(db: Session, program_version_id: UUID) -> RuleResolution:
    row = db.execute(
        select(ProgramVersion, AcademicProgram, Institution)
        .join(AcademicProgram, ProgramVersion.program_id == AcademicProgram.id)
        .join(Institution, ProgramVersion.institution_id == Institution.id)
        .where(ProgramVersion.id == program_version_id)
    ).one_or_none()
    if row is None:
        return RuleResolution(
            RuleResolutionState.MISSING,
            None,
            None,
            "The requested ProgramVersion does not exist.",
        )
    program_version, program, institution = row
    records = db.scalars(
        select(ReviewedRuleSetRecord).where(
            ReviewedRuleSetRecord.institution_identifier == institution.code,
            ReviewedRuleSetRecord.program_identifier == program.code,
            ReviewedRuleSetRecord.catalog_year == program_version.catalog_year,
            ReviewedRuleSetRecord.lifecycle == RuleLifecycle.ACTIVE,
        )
    ).all()
    if len(records) > 1:
        return RuleResolution(
            RuleResolutionState.CONFLICT,
            None,
            None,
            "Multiple active reviewed rule sets match the exact catalog identity.",
        )
    if not records:
        return RuleResolution(
            RuleResolutionState.MISSING,
            None,
            None,
            "No exact active reviewed rule set matches this institution, program, "
            "and catalog year.",
        )
    record = records[0]
    return RuleResolution(
        RuleResolutionState.ACTIVE,
        record,
        CatalogRuleSet.model_validate(record.payload),
        "Exact active reviewed rule set selected by institution, program, and catalog year.",
    )


PROGRAM_PRIORITY = {
    StudentProgramType.PRIMARY_MAJOR: 0,
    StudentProgramType.SECOND_MAJOR: 1,
    StudentProgramType.MINOR: 2,
    StudentProgramType.CERTIFICATE: 3,
}


def resolve_for_student(
    db: Session,
    student_id: UUID,
    program_version_id: UUID | None = None,
) -> RuleResolution:
    active_programs = db.scalars(
        select(StudentAcademicProgram).where(
            StudentAcademicProgram.student_profile_id == student_id,
            StudentAcademicProgram.status == StudentAcademicProgramStatus.ACTIVE,
        )
    ).all()
    if program_version_id is not None:
        selected = next(
            (
                program
                for program in active_programs
                if program.program_version_id == program_version_id
            ),
            None,
        )
        if selected is None:
            return RuleResolution(
                RuleResolutionState.MISSING,
                None,
                None,
                "The explicitly selected ProgramVersion is not an active Program for this student.",
            )
        return resolve_for_program_version(db, selected.program_version_id)
    if not active_programs:
        return RuleResolution(
            RuleResolutionState.MISSING,
            None,
            None,
            "The student has no active ProgramVersion for reviewed-rule resolution.",
        )
    active_programs = sorted(
        active_programs,
        key=lambda program: (
            PROGRAM_PRIORITY[program.program_type],
            str(program.program_version_id),
        ),
    )
    best_priority = PROGRAM_PRIORITY[active_programs[0].program_type]
    best_programs = [
        program
        for program in active_programs
        if PROGRAM_PRIORITY[program.program_type] == best_priority
    ]
    if len(best_programs) > 1:
        return RuleResolution(
            RuleResolutionState.CONFLICT,
            None,
            None,
            "Multiple active Programs share the highest semantic priority; "
            "explicit Program selection is required.",
        )
    return resolve_for_program_version(db, best_programs[0].program_version_id)
